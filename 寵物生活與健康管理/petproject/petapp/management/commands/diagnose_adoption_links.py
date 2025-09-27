from django.core.management.base import BaseCommand
from petapp.models import AdoptionPet, Pet
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = '診斷 AdoptionPet 和 Pet 之間的關聯問題'

    def handle(self, *args, **options):
        # 找出沒有設置 original_pet 的領養記錄
        adoptions_without_link = AdoptionPet.objects.filter(original_pet__isnull=True)

        self.stdout.write(f"=== 診斷報告 ===")
        self.stdout.write(f"找到 {adoptions_without_link.count()} 筆沒有關聯的領養記錄\n")

        for adoption in adoptions_without_link:
            self.stdout.write(f"🔍 診斷領養記錄: {adoption.name}")
            self.stdout.write(f"   ID: {adoption.id}")
            self.stdout.write(f"   飼主: {adoption.owner.username} ({adoption.owner.email})")
            self.stdout.write(f"   種類: {adoption.species}")
            self.stdout.write(f"   品種: {adoption.breed}")
            self.stdout.write(f"   晶片: {adoption.chip or '無'}")
            self.stdout.write(f"   創建時間: {adoption.created_at}")

            # 檢查該飼主的所有寵物
            owner_pets = Pet.objects.filter(owner=adoption.owner)
            self.stdout.write(f"   該飼主共有 {owner_pets.count()} 隻寵物:")

            if owner_pets.exists():
                for pet in owner_pets:
                    self.stdout.write(f"     - {pet.name} ({pet.species}, {pet.breed}) 晶片:{pet.chip or '無'}")

                    # 檢查匹配度
                    match_score = 0
                    match_reasons = []

                    if pet.name == adoption.name:
                        match_score += 3
                        match_reasons.append("名字匹配")
                    elif pet.name.lower() == adoption.name.lower():
                        match_score += 2
                        match_reasons.append("名字匹配(忽略大小寫)")

                    if pet.species == adoption.species:
                        match_score += 2
                        match_reasons.append("種類匹配")

                    if pet.breed == adoption.breed:
                        match_score += 2
                        match_reasons.append("品種匹配")

                    if pet.chip and adoption.chip and pet.chip == adoption.chip:
                        match_score += 5
                        match_reasons.append("晶片匹配")

                    if match_score > 0:
                        self.stdout.write(f"       🎯 匹配分數: {match_score} ({', '.join(match_reasons)})")

                    # 檢查是否已被其他領養記錄關聯
                    existing_adoption = AdoptionPet.objects.filter(original_pet=pet).first()
                    if existing_adoption:
                        self.stdout.write(f"       ⚠️  已被其他領養記錄關聯: {existing_adoption.name} (ID: {existing_adoption.id})")
            else:
                self.stdout.write(f"     (該飼主沒有任何寵物記錄)")

            # 檢查是否有同名寵物（跨飼主）
            same_name_pets = Pet.objects.filter(name=adoption.name).exclude(owner=adoption.owner)
            if same_name_pets.exists():
                self.stdout.write(f"   🔄 其他飼主的同名寵物:")
                for pet in same_name_pets[:3]:  # 只顯示前3筆
                    self.stdout.write(f"     - {pet.name} (飼主: {pet.owner.username})")

            self.stdout.write("-" * 50)

        # 統計資訊
        total_adoptions = AdoptionPet.objects.count()
        linked_adoptions = AdoptionPet.objects.filter(original_pet__isnull=False).count()

        self.stdout.write(f"\n📊 統計資訊:")
        self.stdout.write(f"   總領養記錄: {total_adoptions}")
        self.stdout.write(f"   已關聯記錄: {linked_adoptions}")
        self.stdout.write(f"   未關聯記錄: {adoptions_without_link.count()}")
        self.stdout.write(f"   關聯率: {(linked_adoptions/total_adoptions*100):.1f}%" if total_adoptions > 0 else "   關聯率: 0%")

        # 建議
        self.stdout.write(f"\n💡 修復建議:")
        if adoptions_without_link.count() > 0:
            self.stdout.write(f"   1. 檢查是否是測試數據 (如 'hahaha')")
            self.stdout.write(f"   2. 檢查寵物記錄是否存在於系統中")
            self.stdout.write(f"   3. 考慮手動建立寵物記錄")
            self.stdout.write(f"   4. 使用彈性匹配規則 (忽略大小寫、部分匹配)")
        else:
            self.stdout.write(f"   所有記錄都已正確關聯!")