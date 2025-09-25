# import_locations.py - 放在專案根目錄
import os
import django
import json
import sys
from datetime import datetime

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

from petapp.models import ServiceType, PetType, PetLocation, BusinessHours

def import_pet_locations():
    """匯入寵物地點資料"""
    
    # JSON 檔案路徑
    data_dir = 'normalized_tables'
    
    print("開始匯入地點資料...")
    
    try:
        # 1. 匯入 PetLocation
        print("正在匯入地點資料...")
        with open(f'{data_dir}/pet_locations.json', 'r', encoding='utf-8') as f:
            locations_data = json.load(f)
        
        location_count = 0
        for item in locations_data:
            try:
                # 處理時間
                created_at = parse_datetime(item.get('created_at'))
                updated_at = parse_datetime(item.get('updated_at'))
                
                # 創建或更新地點
                location, created = PetLocation.objects.get_or_create(
                    id=item['id'],
                    defaults={
                        'name': item.get('name'),
                        'address': item.get('address'),
                        'phone': item.get('phone'),
                        'website': item.get('website'),
                        'city': item.get('city'),
                        'district': item.get('district'),
                        'lat': item.get('lat'),
                        'lon': item.get('lon'),
                        'rating': item.get('rating'),
                        'rating_count': item.get('rating_count'),
                        'has_emergency': bool(item.get('has_emergency', False)),
                        'business_hours': item.get('business_hours'),
                        'created_at': created_at,
                        'updated_at': updated_at
                    }
                )
                if created:
                    location_count += 1
                    
            except Exception as e:
                print(f"處理地點 {item.get('id')} 時發生錯誤: {e}")
                continue
        
        print(f"✅ 地點資料匯入完成: {location_count} 筆新資料")
        
        # 2. 建立地點與服務類型的關聯
        print("正在建立地點與服務類型關聯...")
        
        # 首先建立 ID 映射表
        service_id_mapping = {}
        for service in ServiceType.objects.all():
            service_id_mapping[service.id] = service
        
        print(f"現有服務類型: {list(service_id_mapping.keys())}")
        
        with open(f'{data_dir}/location_service_relations.json', 'r', encoding='utf-8') as f:
            service_relations = json.load(f)
        
        service_relation_count = 0
        skipped_service_count = 0
        
        for item in service_relations:
            try:
                location = PetLocation.objects.get(id=item['location_id'])
                service_type_id = item['servicetype_id']
                
                # 檢查服務類型是否存在
                if service_type_id in service_id_mapping:
                    service_type = service_id_mapping[service_type_id]
                    location.service_types.add(service_type)
                    service_relation_count += 1
                else:
                    print(f"找不到服務類型 ID: {service_type_id}")
                    skipped_service_count += 1
                    
            except PetLocation.DoesNotExist:
                print(f"找不到地點 ID: {item['location_id']}")
                skipped_service_count += 1
            except Exception as e:
                print(f"建立服務關聯時發生錯誤: {e}")
                skipped_service_count += 1
                continue
        
        print(f"✅ 地點服務關聯建立完成: {service_relation_count} 筆成功，{skipped_service_count} 筆跳過")
        
        # 3. 建立地點與寵物類型的關聯
        print("正在建立地點與寵物類型關聯...")
        
        # 建立寵物類型 ID 映射表
        pet_id_mapping = {}
        for pet_type in PetType.objects.all():
            pet_id_mapping[pet_type.id] = pet_type
        
        print(f"現有寵物類型: {list(pet_id_mapping.keys())}")
        
        with open(f'{data_dir}/location_pet_relations.json', 'r', encoding='utf-8') as f:
            pet_relations = json.load(f)
        
        pet_relation_count = 0
        skipped_pet_count = 0
        
        for item in pet_relations:
            try:
                location = PetLocation.objects.get(id=item['location_id'])
                pet_type_id = item['pettype_id']
                
                # 檢查寵物類型是否存在
                if pet_type_id in pet_id_mapping:
                    pet_type = pet_id_mapping[pet_type_id]
                    location.pet_types.add(pet_type)
                    pet_relation_count += 1
                else:
                    print(f"找不到寵物類型 ID: {pet_type_id}")
                    skipped_pet_count += 1
                    
            except PetLocation.DoesNotExist:
                print(f"找不到地點 ID: {item['location_id']}")
                skipped_pet_count += 1
            except Exception as e:
                print(f"建立寵物關聯時發生錯誤: {e}")
                skipped_pet_count += 1
                continue
        
        print(f"✅ 地點寵物關聯建立完成: {pet_relation_count} 筆成功，{skipped_pet_count} 筆跳過")
        
        # 4. 匯入營業時間（可選，可以先跳過）
        print("正在匯入營業時間...")
        try:
            with open(f'{data_dir}/business_hours.json', 'r', encoding='utf-8') as f:
                hours_data = json.load(f)
            
            hours_count = 0
            skipped_count = 0
            
            for item in hours_data:
                try:
                    location = PetLocation.objects.get(id=item['location_id'])
                    
                    # 修正時間格式
                    open_time = normalize_time(item.get('open_time'))
                    close_time = normalize_time(item.get('close_time'))
                    
                    # 跳過無效的時間
                    if not open_time or not close_time:
                        skipped_count += 1
                        continue
                    
                    business_hour, created = BusinessHours.objects.get_or_create(
                        location=location,
                        day_of_week=item['day_of_week'],
                        period_order=item.get('period_order', 1),
                        defaults={
                            'open_time': open_time,
                            'close_time': close_time,
                            'period_name': item.get('period_name', '全天')
                        }
                    )
                    if created:
                        hours_count += 1
                        
                except Exception as e:
                    skipped_count += 1
                    # 註解掉詳細錯誤訊息，避免輸出太多
                    # print(f"處理營業時間時發生錯誤 (Location ID: {item.get('location_id')}): {e}")
                    continue
            
            print(f"✅ 營業時間匯入完成: {hours_count} 筆成功，{skipped_count} 筆跳過")
            
        except FileNotFoundError:
            print("⚠️ 營業時間檔案未找到，跳過此步驟")
        
        # 5. 顯示統計資訊
        print("\n=== 匯入完成統計 ===")
        print(f"總地點數: {PetLocation.objects.count()}")
        print(f"服務類型數: {ServiceType.objects.count()}")
        print(f"寵物類型數: {PetType.objects.count()}")
        print(f"營業時間記錄數: {BusinessHours.objects.count()}")
        
        # 測試一些關聯
        location_with_services = PetLocation.objects.filter(service_types__isnull=False).distinct().count()
        location_with_pets = PetLocation.objects.filter(pet_types__isnull=False).distinct().count()
        
        print(f"有服務類型的地點: {location_with_services}")
        print(f"有寵物類型的地點: {location_with_pets}")
        
        print("\n✅ 所有資料匯入完成！")
        
    except Exception as e:
        print(f"❌ 匯入過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

def normalize_time(time_str):
    """標準化時間格式，處理 24:00 等特殊情況"""
    if not time_str:
        return None
    
    time_str = time_str.strip()
    
    # 處理 24:00 的情況 - 轉換為 23:59
    if time_str == "24:00":
        return "23:59"
    
    # 處理其他可能的 24 小時格式
    if time_str.startswith("24:"):
        return "23:59"
    
    # 檢查時間格式是否有效
    try:
        from datetime import datetime
        datetime.strptime(time_str, '%H:%M')
        return time_str
    except ValueError:
        print(f"無效的時間格式: {time_str}")
        return None

def parse_datetime(datetime_str):
    """解析日期時間字串"""
    if not datetime_str:
        return datetime.now()
    
    try:
        if 'T' in datetime_str:
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        else:
            return datetime.fromisoformat(datetime_str)
    except (ValueError, TypeError):
        return datetime.now()

if __name__ == "__main__":
    import_pet_locations()