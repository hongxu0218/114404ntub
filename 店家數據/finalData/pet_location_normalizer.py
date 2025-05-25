import json
import re
from datetime import datetime
from collections import defaultdict

# 讀取JSON檔案
def load_json_data(file_path):
    """從JSON檔案載入資料"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"找不到檔案: {file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON格式錯誤: {e}")
        return []

class PetLocationNormalizer:
    def __init__(self):
        # 服務類型對照表
        self.service_type_mapping = {
            'is_cosmetic': {'code': 'cosmetic', 'name': '美容'},
            'is_funeral': {'code': 'funeral', 'name': '殯葬'},
            'is_hospital': {'code': 'hospital', 'name': '醫療'},
            'is_live': {'code': 'live', 'name': '住宿'},
            'is_boarding': {'code': 'boarding', 'name': '寄宿'},
            'is_park': {'code': 'park', 'name': '公園'},
            'is_product': {'code': 'product', 'name': '用品'},
            'is_shelter': {'code': 'shelter', 'name': '收容所'}
        }
        
        # 寵物類型對照表
        self.pet_type_mapping = {
            'support_small_dog': {'code': 'small_dog', 'name': '小型犬'},
            'support_medium_dog': {'code': 'medium_dog', 'name': '中型犬'},
            'support_large_dog': {'code': 'large_dog', 'name': '大型犬'},
            'support_cat': {'code': 'cat', 'name': '貓'},
            'support_bird': {'code': 'bird', 'name': '鳥類'},
            'support_rodent': {'code': 'rodent', 'name': '齧齒類'},
            'support_reptile': {'code': 'reptile', 'name': '爬蟲類'},
            'support_other': {'code': 'other', 'name': '其他'}
        }
        
        # 星期對照表
        self.weekday_mapping = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
    
    def normalize_data(self, json_data):
        """將JSON資料正規化為各個表格的資料"""
        
        # 初始化各表格資料
        service_types = {}
        pet_types = {}
        pet_locations = []
        location_service_relations = []
        location_pet_relations = []
        business_hours = []
        
        # 處理每筆地點資料
        for item in json_data:
            location_id = item['id']
            
            # 1. 處理 PetLocation 主表
            pet_location = {
                'id': location_id,
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
                'has_emergency': bool(item.get('has_emergency', 0)),
                'business_hours': item.get('business_hours'),  # 保留JSON格式（過渡期）
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at')
            }
            pet_locations.append(pet_location)
            
            # 2. 處理服務類型
            for field, service_info in self.service_type_mapping.items():
                if item.get(field, 0) == 1:  # 如果該服務類型為True
                    code = service_info['code']
                    name = service_info['name']
                    
                    # 添加到 ServiceType 表（避免重複）
                    if code not in service_types:
                        service_types[code] = {
                            'id': len(service_types) + 1,
                            'name': name,
                            'code': code,
                            'is_active': True
                        }
                    
                    # 添加關聯記錄
                    location_service_relations.append({
                        'id': len(location_service_relations) + 1,
                        'location_id': location_id,
                        'servicetype_id': service_types[code]['id'],
                        'created_at': datetime.now().isoformat()
                    })
            
            # 3. 處理寵物類型
            for field, pet_info in self.pet_type_mapping.items():
                if item.get(field, 0) == 1:  # 如果支援該寵物類型
                    code = pet_info['code']
                    name = pet_info['name']
                    
                    # 添加到 PetType 表（避免重複）
                    if code not in pet_types:
                        pet_types[code] = {
                            'id': len(pet_types) + 1,
                            'name': name,
                            'code': code,
                            'is_active': True
                        }
                    
                    # 添加關聯記錄
                    location_pet_relations.append({
                        'id': len(location_pet_relations) + 1,
                        'location_id': location_id,
                        'pettype_id': pet_types[code]['id'],
                        'created_at': datetime.now().isoformat()
                    })
            
            # 4. 處理營業時間
            if item.get('business_hours'):
                try:
                    hours_data = json.loads(item['business_hours'])
                    for day_eng, time_str in hours_data.items():
                        if day_eng in self.weekday_mapping and time_str and time_str.strip() not in ['休息', '暫停營業', '不營業', 'Closed']:
                            day_of_week = self.weekday_mapping[day_eng]
                            
                            # 處理各種時間格式
                            parsed_hours = self._parse_business_hours(time_str)
                            
                            for idx, (open_time, close_time) in enumerate(parsed_hours):
                                if open_time and close_time:
                                    business_hours.append({
                                        'id': len(business_hours) + 1,
                                        'location_id': location_id,
                                        'day_of_week': day_of_week,
                                        'open_time': open_time,
                                        'close_time': close_time,
                                        'period_order': idx + 1,
                                        'period_name': f'時段{idx + 1}' if len(parsed_hours) > 1 else '全天'
                                    })
                except json.JSONDecodeError:
                    print(f"無法解析營業時間 JSON (Location ID: {location_id}): {item['business_hours']}")
                except Exception as e:
                    print(f"處理營業時間時發生錯誤 (Location ID: {location_id}): {e}")
                    print(f"時間資料: {item.get('business_hours', 'N/A')}")
        
        # 轉換字典為列表
        service_types_list = list(service_types.values())
        pet_types_list = list(pet_types.values())
        
        return {
            'service_types': service_types_list,
            'pet_types': pet_types_list,
            'pet_locations': pet_locations,
            'location_service_relations': location_service_relations,
            'location_pet_relations': location_pet_relations,
            'business_hours': business_hours
        }
    
    def _parse_business_hours(self, time_str):
        """解析營業時間字串，返回 [(開始時間, 結束時間)] 列表"""
        
        if not time_str or not time_str.strip():
            return []
        
        # 清理字串
        time_str = time_str.strip()
        
        # 常見的休息日標示
        closed_indicators = ['休息', '暫停營業', '不營業', 'Closed', 'closed', '公休', '休館']
        if any(indicator in time_str for indicator in closed_indicators):
            return []
        
        # 24小時營業
        if '24' in time_str and ('小時' in time_str or 'hours' in time_str.lower()):
            return [('00:00', '23:59')]
        
        # 處理多種分隔符號
        separators = ['–', '-', '~', '到', 'to', '至']
        
        # 處理多個時段（用逗號、分號或其他符號分隔）
        period_separators = [',', '；', ';', '、', ' and ', '&']
        periods = [time_str]
        
        for sep in period_separators:
            temp_periods = []
            for period in periods:
                temp_periods.extend(period.split(sep))
            periods = temp_periods
        
        results = []
        
        for period in periods:
            period = period.strip()
            if not period:
                continue
                
            # 尋找時間分隔符
            found_separator = None
            for sep in separators:
                if sep in period:
                    found_separator = sep
                    break
            
            if found_separator:
                try:
                    parts = period.split(found_separator)
                    if len(parts) >= 2:
                        open_time = self._normalize_time(parts[0].strip())
                        close_time = self._normalize_time(parts[1].strip())
                        
                        if open_time and close_time:
                            results.append((open_time, close_time))
                    else:
                        print(f"時間格式異常: {period}")
                except Exception as e:
                    print(f"解析時間段失敗: {period}, 錯誤: {e}")
            else:
                # 沒有分隔符，可能是單一時間或特殊格式
                normalized = self._normalize_time(period)
                if normalized:
                    # 假設是開始時間，結束時間設為同一天的23:59
                    results.append((normalized, '23:59'))
        
        return results
    
    def _normalize_time(self, time_str):
        """標準化時間格式為 HH:MM"""
        
        if not time_str:
            return None
        
        # 移除多餘的空格和符號
        time_str = time_str.strip().replace(' ', '').replace('：', ':')
        
        # 匹配 HH:MM 格式
        pattern1 = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
        if pattern1:
            hour, minute = pattern1.groups()
            return f"{int(hour):02d}:{minute}"
        
        # 匹配 HH.MM 格式
        pattern2 = re.match(r'^(\d{1,2})\.(\d{2})$', time_str)
        if pattern2:
            hour, minute = pattern2.groups()
            return f"{int(hour):02d}:{minute}"
        
        # 匹配 HHMM 格式（4位數字）
        pattern3 = re.match(r'^(\d{2})(\d{2})$', time_str)
        if pattern3:
            hour, minute = pattern3.groups()
            return f"{hour}:{minute}"
        
        # 匹配 H:MM 或 HH:M 格式
        pattern4 = re.match(r'^(\d{1,2}):(\d{1,2})$', time_str)
        if pattern4:
            hour, minute = pattern4.groups()
            return f"{int(hour):02d}:{int(minute):02d}"
        
        # 匹配只有小時的格式 (例如: "10", "18")
        pattern5 = re.match(r'^(\d{1,2})$', time_str)
        if pattern5:
            hour = pattern5.group(1)
            return f"{int(hour):02d}:00"
        
        # 處理上午/下午格式
        if 'AM' in time_str.upper() or 'PM' in time_str.upper():
            is_pm = 'PM' in time_str.upper()
            time_part = re.sub(r'[AaPpMm\s]', '', time_str)
            
            time_match = re.match(r'^(\d{1,2}):?(\d{0,2})$', time_part)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                
                if is_pm and hour != 12:
                    hour += 12
                elif not is_pm and hour == 12:
                    hour = 0
                
                return f"{hour:02d}:{minute:02d}"
        
        return None
    
    def print_results(self, normalized_data):
        """輸出正規化後的結果"""
        
        print("=" * 80)
        print("正規化資料處理結果")
        print("=" * 80)
        
        # 1. ServiceType 表
        print("\n📋 ServiceType【服務類型表】")
        print("-" * 50)
        for item in normalized_data['service_types']:
            print(f"ID: {item['id']}, Code: {item['code']}, Name: {item['name']}, Active: {item['is_active']}")
        
        # 2. PetType 表
        print("\n🐾 PetType【寵物類型表】")
        print("-" * 50)
        for item in normalized_data['pet_types']:
            print(f"ID: {item['id']}, Code: {item['code']}, Name: {item['name']}, Active: {item['is_active']}")
        
        # 3. PetLocation 表
        print("\n📍 PetLocation【寵物地點表】")
        print("-" * 50)
        for item in normalized_data['pet_locations'][:5]:  # 只顯示前5筆
            print(f"ID: {item['id']}, Name: {item['name']}, City: {item['city']}, District: {item['district']}")
            print(f"    Address: {item['address']}")
            print(f"    Phone: {item['phone']}, Rating: {item['rating']}, Emergency: {item['has_emergency']}")
            print(f"    Lat: {item['lat']}, Lon: {item['lon']}")
            print()
        
        if len(normalized_data['pet_locations']) > 5:
            print(f"... 還有 {len(normalized_data['pet_locations']) - 5} 筆地點資料")
        
        # 4. LocationServiceType 關聯表
        print(f"\n🔗 LocationServiceType【地點服務關聯表】- 共 {len(normalized_data['location_service_relations'])} 筆")
        print("-" * 50)
        for item in normalized_data['location_service_relations'][:10]:  # 只顯示前10筆
            print(f"ID: {item['id']}, Location ID: {item['location_id']}, Service Type ID: {item['servicetype_id']}")
        
        if len(normalized_data['location_service_relations']) > 10:
            print(f"... 還有 {len(normalized_data['location_service_relations']) - 10} 筆關聯記錄")
        
        # 5. LocationPetType 關聯表
        print(f"\n🔗 LocationPetType【地點寵物關聯表】- 共 {len(normalized_data['location_pet_relations'])} 筆")
        print("-" * 50)
        for item in normalized_data['location_pet_relations'][:10]:  # 只顯示前10筆
            print(f"ID: {item['id']}, Location ID: {item['location_id']}, Pet Type ID: {item['pettype_id']}")
        
        if len(normalized_data['location_pet_relations']) > 10:
            print(f"... 還有 {len(normalized_data['location_pet_relations']) - 10} 筆關聯記錄")
        
        # 6. BusinessHours 表
        print(f"\n🕒 BusinessHours【營業時間表】- 共 {len(normalized_data['business_hours'])} 筆")
        print("-" * 50)
        weekday_names = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
        for item in normalized_data['business_hours'][:15]:  # 只顯示前15筆
            day_name = weekday_names[item['day_of_week']]
            print(f"ID: {item['id']}, Location ID: {item['location_id']}, {day_name}: {item['open_time']}-{item['close_time']}")
        
        if len(normalized_data['business_hours']) > 15:
            print(f"... 還有 {len(normalized_data['business_hours']) - 15} 筆營業時間記錄")
    
    def export_to_sql_inserts(self, normalized_data):
        """生成SQL INSERT語句"""
        
        sql_statements = []
        
        # 1. ServiceType 插入語句
        sql_statements.append("-- ServiceType 表插入語句")
        for item in normalized_data['service_types']:
            sql = f"INSERT INTO ServiceType (id, name, code, is_active) VALUES ({item['id']}, '{item['name']}', '{item['code']}', {item['is_active']});"
            sql_statements.append(sql)
        
        # 2. PetType 插入語句
        sql_statements.append("\n-- PetType 表插入語句")
        for item in normalized_data['pet_types']:
            sql = f"INSERT INTO PetType (id, name, code, is_active) VALUES ({item['id']}, '{item['name']}', '{item['code']}', {item['is_active']});"
            sql_statements.append(sql)
        
        # 3. PetLocation 插入語句
        sql_statements.append("\n-- PetLocation 表插入語句")
        for item in normalized_data['pet_locations']:
            # 處理可能包含單引號的字串
            name = item['name'].replace("'", "''") if item['name'] else 'NULL'
            address = item['address'].replace("'", "''") if item['address'] else 'NULL'
            phone = item['phone'] if item['phone'] else 'NULL'
            website = item['website'].replace("'", "''") if item['website'] else 'NULL'
            city = item['city'] if item['city'] else 'NULL'
            district = item['district'] if item['district'] else 'NULL'
            
            lat = f"'{item['lat']}'" if item['lat'] is not None else 'NULL'
            lon = f"'{item['lon']}'" if item['lon'] is not None else 'NULL'
            rating = f"'{item['rating']}'" if item['rating'] is not None else 'NULL'
            rating_count = item['rating_count'] if item['rating_count'] is not None else 'NULL'
            
            business_hours = item['business_hours'].replace("'", "''") if item['business_hours'] else 'NULL'
            
            sql = f"""INSERT INTO PetLocation (id, name, address, phone, website, city, district, lat, lon, rating, rating_count, has_emergency, business_hours, created_at, updated_at) 
VALUES ({item['id']}, '{name}', '{address}', '{phone}', '{website}', '{city}', '{district}', {lat}, {lon}, {rating}, {rating_count}, {item['has_emergency']}, '{business_hours}', '{item['created_at']}', '{item['updated_at']}');"""
            sql_statements.append(sql)
        
        # 4. LocationServiceType 關聯表插入語句
        sql_statements.append("\n-- LocationServiceType 關聯表插入語句")
        for item in normalized_data['location_service_relations']:
            sql = f"INSERT INTO LocationServiceType (id, location_id, servicetype_id, created_at) VALUES ({item['id']}, {item['location_id']}, {item['servicetype_id']}, '{item['created_at']}');"
            sql_statements.append(sql)
        
        # 5. LocationPetType 關聯表插入語句
        sql_statements.append("\n-- LocationPetType 關聯表插入語句")
        for item in normalized_data['location_pet_relations']:
            sql = f"INSERT INTO LocationPetType (id, location_id, pettype_id, created_at) VALUES ({item['id']}, {item['location_id']}, {item['pettype_id']}, '{item['created_at']}');"
            sql_statements.append(sql)
        
        # 6. BusinessHours 插入語句
        sql_statements.append("\n-- BusinessHours 表插入語句")
        for item in normalized_data['business_hours']:
            sql = f"INSERT INTO BusinessHours (id, location_id, day_of_week, open_time, close_time, period_order, period_name) VALUES ({item['id']}, {item['location_id']}, {item['day_of_week']}, '{item['open_time']}', '{item['close_time']}', {item['period_order']}, '{item['period_name']}');"
            sql_statements.append(sql)
        
        return '\n'.join(sql_statements)

# 執行正規化處理
if __name__ == "__main__":
    # 從mapdata.json載入資料
    json_file_path = "mapdata.json"  # JSON檔案路徑
    map_data = load_json_data(json_file_path)
    
    if not map_data:
        print("無法載入資料，請確認mapdata.json檔案存在且格式正確")
        exit(1)
    
    print(f"成功載入 {len(map_data)} 筆地點資料")
    
    normalizer = PetLocationNormalizer()
    normalized_data = normalizer.normalize_data(map_data)
    
    # 輸出結果
    normalizer.print_results(normalized_data)
    
    # 生成SQL語句
    print("\n" + "=" * 80)
    print("生成 SQL INSERT 語句...")
    print("=" * 80)
    sql_inserts = normalizer.export_to_sql_inserts(normalized_data)
    
    # 將每個表格分別保存為獨立的JSON檔案
    print("正在生成各資料表的JSON檔案...")
    
    # 建立輸出目錄（可選）
    import os
    output_dir = "normalized_tables"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"建立輸出目錄: {output_dir}")
    
    # 分別保存各個資料表
    table_files = {
        'service_types': 'service_types.json',
        'pet_types': 'pet_types.json', 
        'pet_locations': 'pet_locations.json',
        'location_service_relations': 'location_service_relations.json',
        'location_pet_relations': 'location_pet_relations.json',
        'business_hours': 'business_hours.json'
    }
    
    for table_name, filename in table_files.items():
        file_path = os.path.join(output_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(normalized_data[table_name], f, ensure_ascii=False, indent=2)
        print(f"✅ {table_name} 已保存至: {file_path} ({len(normalized_data[table_name])} 筆資料)")
    
    # 將SQL語句保存到檔案
    sql_file_path = os.path.join(output_dir, "normalized_inserts.sql")
    with open(sql_file_path, "w", encoding="utf-8") as f:
        f.write(sql_inserts)
    print(f"✅ SQL語句已保存至: {sql_file_path}")
    
    # 也保存完整的合併檔案（可選）
    complete_file_path = os.path.join(output_dir, "complete_normalized_data.json")
    with open(complete_file_path, "w", encoding="utf-8") as f:
        json.dump(normalized_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 完整資料已保存至: {complete_file_path}")
    
    # 輸出統計資訊
    print(f"\n處理完成！統計資訊：")
    print(f"- 服務類型: {len(normalized_data['service_types'])} 種")
    print(f"- 寵物類型: {len(normalized_data['pet_types'])} 種") 
    print(f"- 地點資料: {len(normalized_data['pet_locations'])} 筆")
    print(f"- 地點服務關聯: {len(normalized_data['location_service_relations'])} 筆")
    print(f"- 地點寵物關聯: {len(normalized_data['location_pet_relations'])} 筆")
    print(f"- 營業時間記錄: {len(normalized_data['business_hours'])} 筆")