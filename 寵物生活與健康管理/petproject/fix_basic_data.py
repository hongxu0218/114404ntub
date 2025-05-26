# fix_basic_data.py - 修復基礎資料的 ID
import os
import django
import json

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

from petapp.models import ServiceType, PetType

def fix_basic_data():
    print("修復基礎資料 ID...")
    
    # 1. 修復 ServiceType
    print("載入 service_types.json...")
    with open('normalized_tables/service_types.json', 'r', encoding='utf-8') as f:
        service_types_data = json.load(f)
    
    print("清除現有 ServiceType 資料...")
    ServiceType.objects.all().delete()
    
    print("重新建立 ServiceType 資料...")
    for item in service_types_data:
        ServiceType.objects.create(
            id=item['id'],
            name=item['name'],
            code=item['code'],
            is_active=item['is_active']
        )
    
    print(f"✅ ServiceType 建立完成: {len(service_types_data)} 筆")
    
    # 2. 修復 PetType
    print("載入 pet_types.json...")
    with open('normalized_tables/pet_types.json', 'r', encoding='utf-8') as f:
        pet_types_data = json.load(f)
    
    print("清除現有 PetType 資料...")
    PetType.objects.all().delete()
    
    print("重新建立 PetType 資料...")
    for item in pet_types_data:
        PetType.objects.create(
            id=item['id'],
            name=item['name'],
            code=item['code'],
            is_active=item['is_active']
        )
    
    print(f"✅ PetType 建立完成: {len(pet_types_data)} 筆")
    
    # 3. 檢查結果
    print("\n=== 檢查結果 ===")
    print("ServiceType:")
    for st in ServiceType.objects.all().order_by('id'):
        print(f"  ID: {st.id}, Code: {st.code}, Name: {st.name}")
    
    print("\nPetType:")
    for pt in PetType.objects.all().order_by('id'):
        print(f"  ID: {pt.id}, Code: {pt.code}, Name: {pt.name}")

if __name__ == "__main__":
    fix_basic_data()