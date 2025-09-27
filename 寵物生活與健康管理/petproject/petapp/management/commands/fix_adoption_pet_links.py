from django.core.management.base import BaseCommand
from petapp.models import AdoptionPet, Pet


class Command(BaseCommand):
    help = '修復 AdoptionPet 和 Pet 之間的關聯'

    def handle(self, *args, **options):
        # 找出沒有設置 original_pet 的領養記錄
        adoptions_without_link = AdoptionPet.objects.filter(original_pet__isnull=True)

        self.stdout.write(f"找到 {adoptions_without_link.count()} 筆沒有關聯的領養記錄")

        fixed_count = 0
        for adoption in adoptions_without_link:
            matching_pet = None

            # 方法1：使用晶片號碼匹配
            if adoption.chip:
                matching_pet = Pet.objects.filter(
                    chip=adoption.chip,
                    owner=adoption.owner
                ).first()
                if matching_pet:
                    self.stdout.write(f"通過晶片號碼匹配: {adoption.name} -> {matching_pet.name}")

            # 方法2：精確匹配
            if not matching_pet:
                matching_pet = Pet.objects.filter(
                    name=adoption.name,
                    species=adoption.species,
                    breed=adoption.breed,
                    owner=adoption.owner
                ).first()
                if matching_pet:
                    self.stdout.write(f"通過精確匹配: {adoption.name} -> {matching_pet.name}")

            # 方法3：只用名字匹配（如果只有一個結果）
            if not matching_pet:
                potential_pets = Pet.objects.filter(
                    name=adoption.name,
                    owner=adoption.owner
                )
                if potential_pets.count() == 1:
                    matching_pet = potential_pets.first()
                    self.stdout.write(f"通過名字匹配: {adoption.name} -> {matching_pet.name}")

            if matching_pet:
                adoption.original_pet = matching_pet
                adoption.save()
                fixed_count += 1
            else:
                self.stdout.write(f"無法匹配: {adoption.name} (飼主: {adoption.owner.username})")

        self.stdout.write(
            self.style.SUCCESS(f'成功修復 {fixed_count} 筆記錄')
        )