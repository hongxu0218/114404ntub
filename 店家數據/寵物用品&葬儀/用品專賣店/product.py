import requests
import json
import pandas as pd
import time
import os
from dotenv import load_dotenv

# 載入環境變數（如果你將API金鑰存在.env檔案中）
load_dotenv()

class GoogleMapsAPI:
    def __init__(self, api_key=None):
        # 優先使用參數提供的API金鑰，否則嘗試從環境變數取得
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError("必須提供Google Maps API金鑰")
        
        self.places_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        self.place_details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        self.results = []
        
        # 添加請求間隔時間（毫秒）
        self.delay_between_requests = 300  # 每次請求間隔300毫秒，避免超過API限制
    
    def search_places(self, query, location, language="zh-TW", limit=None):
        """
        搜尋特定地點的商家
        
        參數:
            query (str): 搜尋關鍵字
            location (str): 地點名稱
            language (str): 回傳結果的語言
            limit (int, optional): 限制結果數量
        """
        search_query = f"{query} in {location}"
        
        params = {
            "query": search_query,
            "key": self.api_key,
            "language": language
        }
        
        all_results = []
        next_page_token = None
        
        try:
            # 第一頁結果
            response = requests.get(self.places_url, params=params)
            result_data = response.json()
            
            if result_data["status"] != "OK":
                if result_data["status"] == "ZERO_RESULTS":
                    print(f"在「{location}」中未找到「{query}」的結果")
                    return []
                else:
                    print(f"API錯誤: {result_data['status']}")
                    if "error_message" in result_data:
                        print(f"錯誤訊息: {result_data['error_message']}")
                    return []
            
            all_results.extend(result_data["results"])
            
            # 如果有下一頁且沒有達到限制，繼續獲取
            while "next_page_token" in result_data and (limit is None or len(all_results) < limit):
                next_page_token = result_data["next_page_token"]
                
                # Google 要求在使用 next_page_token 前等待一小段時間
                time.sleep(2)
                
                # 使用 next_page_token 獲取下一頁結果
                next_params = {
                    "key": self.api_key,
                    "pagetoken": next_page_token,
                    "language": language
                }
                
                response = requests.get(self.places_url, params=next_params)
                result_data = response.json()
                
                if result_data["status"] == "OK":
                    all_results.extend(result_data["results"])
                else:
                    print(f"獲取下一頁時出錯: {result_data['status']}")
                    break
            
            # 限制結果數量
            if limit is not None and len(all_results) > limit:
                all_results = all_results[:limit]
            
            self.results = all_results
            print(f"找到 {len(all_results)} 個結果")
            return all_results
            
        except Exception as e:
            print(f"搜尋地點時發生錯誤: {e}")
            return []
    
    def get_place_details(self, place_id, language="zh-TW"):
        """
        獲取特定地點的詳細資訊
        
        參數:
            place_id (str): 地點的唯一ID
            language (str): 回傳結果的語言
        """
        params = {
            "place_id": place_id,
            "key": self.api_key,
            "language": language,
            "fields": "name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,opening_hours"
        }
        
        try:
            # 添加延遲避免超過API限制
            time.sleep(self.delay_between_requests / 1000.0)
            
            response = requests.get(self.place_details_url, params=params)
            result_data = response.json()
            
            if result_data["status"] == "OK":
                return result_data["result"]
            else:
                print(f"獲取地點詳情時出錯: {result_data['status']}")
                return None
                
        except Exception as e:
            print(f"獲取地點詳情時發生錯誤: {e}")
            return None
    
    def extract_place_data(self):
        """
        從搜尋結果中提取詳細資訊，改進篩選邏輯以處理多功能寵物店
        """
        extracted_data = []
        
        if not self.results:
            print("沒有結果可提取")
            return extracted_data
        
        # 寵物用品相關關鍵詞
        boarding_keywords = ["用品", "商品", "物品", "產品", "product", "goods"]
        
        # 寵物相關關鍵詞
        pet_keywords = ["寵物", "毛孩", "狗", "貓", "汪", "pet", "dog", "cat"]
        
        # 排除完全不相關的地點
        negative_keywords = ["老街", "瀑布", "公園", "景點", "觀光", "風景區", "步道", "登山", 
                          "國小", "國中", "高中", "學校", "大學", "廟", "餐廳", "小吃",
                          "咖啡", "早餐", "午餐", "晚餐", "夜市", "市場", "超市"]
        
        excluded_count = 0
        included_count = 0
        
        for i, place in enumerate(self.results):
            try:
                place_id = place["place_id"]
                place_name = place.get("name", "未知店名")
                print(f"正在提取 ({i+1}/{len(self.results)}): {place_name}")
                
                # 初步檢查名稱是否含有明顯不相關的關鍵詞
                if any(neg_kw in place_name for neg_kw in negative_keywords):
                    print(f"  排除: {place_name} (名稱明顯不相關)")
                    excluded_count += 1
                    continue
                
                # 檢查地點類型是否相關 (如果API返回了類型信息)
                place_types = place.get("types", [])
                tourist_related_types = ["tourist_attraction", "natural_feature", "park", 
                                      "museum", "church", "place_of_worship"]
                
                if any(pt in tourist_related_types for pt in place_types):
                    print(f"  排除: {place_name} (地點類型不相關)")
                    excluded_count += 1
                    continue
                
                # 取得詳細資訊
                details = self.get_place_details(place_id)
                
                if details:
                    place_name_lower = details.get("name", "").lower()
                    
                    # 規則1: 名稱中同時包含寵物和寄宿關鍵詞的店家直接保留
                    name_has_pet = any(kw in place_name_lower for kw in pet_keywords)
                    name_has_boarding = any(kw in place_name_lower for kw in boarding_keywords)
                    
                    # 規則2: 使用我們的搜尋關鍵詞找到的結果，如果包含任一寵物關鍵詞，也保留
                    # 因為我們是搜尋"寵物寄宿"等詞，API返回的結果可能已經過篩選
                    search_relevance = True
                    
                    # 規則3: 如果名稱中只有寵物關鍵詞，檢查經營內容是否包含寄宿服務
                    # 這裡我們能獲取的資訊有限，主要依賴於名稱和可能的營業時間
                    has_overnight_service = False
                    if "opening_hours" in details and "weekday_text" in details["opening_hours"]:
                        # 如果營業時間包含夜間服務，可能提供寄宿
                        opening_hours = " ".join(details["opening_hours"]["weekday_text"]).lower()
                        if "24小時" in opening_hours or "24 小時" in opening_hours or "24h" in opening_hours:
                            has_overnight_service = True
                    
                    # 決定是否保留此店家
                    if (name_has_pet and name_has_boarding) or \
                       (name_has_pet and search_relevance) or \
                       (name_has_boarding and search_relevance):
                        # 保留此店家
                        place_data = {
                            "店名": details.get("name", ""),
                            "地址": details.get("formatted_address", ""),
                            "電話": details.get("formatted_phone_number", ""),
                            "網站": details.get("website", ""),
                            "評分": details.get("rating", ""),
                            "評分數量": details.get("user_ratings_total", ""),
                        }
                        
                        # 營業時間（如果有）
                        if "opening_hours" in details and "weekday_text" in details["opening_hours"]:
                            place_data["營業時間"] = " | ".join(details["opening_hours"]["weekday_text"])
                        else:
                            place_data["營業時間"] = ""
                        
                        # 添加一個可能性評分欄位，表示該店提供寵物寄宿服務的可能性
                        confidence = 0
                        if name_has_pet and name_has_boarding:
                            confidence = 5  # 最高確信度
                        elif name_has_boarding:
                            confidence = 4
                        elif name_has_pet and has_overnight_service:
                            confidence = 3
                        elif name_has_pet:
                            confidence = 2
                        else:
                            confidence = 1
                        
                        place_data["寄宿可能性"] = confidence
                        
                        extracted_data.append(place_data)
                        included_count += 1
                        print(f"  包含: {place_name} (可能性評分: {confidence}/5)")
                    else:
                        # 排除此店家
                        print(f"  排除: {place_name} (未找到足夠的寵物寄宿相關證據)")
                        excluded_count += 1
                
            except Exception as e:
                print(f"提取地點資料時發生錯誤: {e}")
        
        # 排序結果，將最可能提供寵物寄宿服務的店家放在前面
        extracted_data.sort(key=lambda x: x["寄宿可能性"], reverse=True)
        
        print(f"成功提取 {len(extracted_data)} 個疑似寵物寄宿店家 (排除了 {excluded_count} 個不相關地點)")
        return extracted_data
    
    def save_to_csv(self, data, filename):
        """
        將資料保存為 CSV 檔案
        """
        # 確保目錄存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')  # 使用 utf-8-sig 以支援中文
        print(f"資料已保存至 {filename}")
    
    def save_to_json(self, data, filename):
        """
        將資料保存為 JSON 檔案
        """
        # 確保目錄存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"資料已保存至 {filename}")

def main():
    # 設定儲存路徑
    output_dir = r"C:\Users\susan\OneDrive - ntub.edu.tw\畢業專題\爬蟲\寵物用品&葬儀"
    
    # 直接提供你的 API 金鑰
    api_key = "AIzaSyD6bvzxlm0cOmyfR0md43t0qixgXEupMpY"  # 把這裡替換成你的實際 API 金鑰
    maps_api = GoogleMapsAPI(api_key)
    
    try:
        # 定義搜尋關鍵詞
        keywords = [
            "寵物用品",
            "寵物產品",
            "寵物商品",
            "狗狗用品",
            "貓咪用品",
            "寵物物品",
            "毛孩用品",
        ]
        
        # 定義城市及其行政區
        cities_districts = {
            "台北市": ["中正區", "大同區", "中山區", "松山區", "大安區", "萬華區", 
                    "信義區", "士林區", "北投區", "內湖區", "南港區", "文山區"],
            "臺北市": [],  # 使用台北市的區域，避免重複
            "新北市": ["板橋區", "三重區", "中和區", "永和區", "新莊區", "新店區", 
                    "樹林區", "鶯歌區", "三峽區", "淡水區", "汐止區", "瑞芳區", 
                    "土城區", "蘆洲區", "五股區", "泰山區", "林口區", "深坑區", 
                    "石碇區", "坪林區", "三芝區", "石門區", "八里區", "平溪區", 
                    "雙溪區", "貢寮區", "金山區", "萬里區", "烏來區"],
            "桃園市": ["桃園區", "中壢區", "大溪區", "楊梅區", "蘆竹區", "大園區", 
                    "龜山區", "八德區", "龍潭區", "平鎮區", "新屋區", "觀音區", "復興區"],
            "台中市": ["中區", "東區", "南區", "西區", "北區", "北屯區", "西屯區", "南屯區", 
                    "太平區", "大里區", "霧峰區", "烏日區", "豐原區", "后里區", "石岡區", 
                    "東勢區", "和平區", "新社區", "潭子區", "大雅區", "神岡區", "大肚區", 
                    "沙鹿區", "龍井區", "梧棲區", "清水區", "大甲區", "外埔區", "大安區"],
            "臺中市": [],  # 使用台中市的區域，避免重複
            "台南市": ["中西區", "東區", "南區", "北區", "安平區", "安南區", "永康區", 
                    "歸仁區", "新化區", "左鎮區", "玉井區", "楠西區", "南化區", "仁德區", 
                    "關廟區", "龍崎區", "官田區", "麻豆區", "佳里區", "西港區", "七股區", 
                    "將軍區", "學甲區", "北門區", "新營區", "後壁區", "白河區", "東山區", 
                    "六甲區", "下營區", "柳營區", "鹽水區", "善化區", "大內區", "山上區", 
                    "新市區", "安定區"],
            "臺南市": [],  # 使用台南市的區域，避免重複
            "高雄市": ["楠梓區", "左營區", "鼓山區", "三民區", "鹽埕區", "前金區", "新興區", 
                    "苓雅區", "前鎮區", "旗津區", "小港區", "鳳山區", "林園區", "大寮區", 
                    "大樹區", "大社區", "仁武區", "鳥松區", "岡山區", "橋頭區", "燕巢區", 
                    "田寮區", "阿蓮區", "路竹區", "湖內區", "茄萣區", "永安區", "彌陀區", 
                    "梓官區", "旗山區", "美濃區", "六龜區", "甲仙區", "杉林區", "內門區", 
                    "茂林區", "桃源區", "那瑪夏區"]
        }
        
        # 主要城市名稱（用於整合資料）
        main_city_names = {
            "台北市": "台北市", "臺北市": "台北市",
            "新北市": "新北市",
            "桃園市": "桃園市",
            "台中市": "台中市", "臺中市": "台中市",
            "台南市": "台南市", "臺南市": "台南市",
            "高雄市": "高雄市"
        }
        
        # 儲存所有城市的資料
        all_pet_boarding_data = []
        
        # 城市資料統計
        city_stats = {}
        
        # 處理每個城市
        for city_name, districts in cities_districts.items():
            # 跳過無區域的替代城市名稱（會在主要名稱中處理）
            if not districts:
                continue
                
            print(f"\n========== 開始搜尋：{city_name} ==========")
            city_data = []
            existing_identifiers = set()  # 用於去重
            
            # 如果有區域，按區域搜尋
            for district in districts:
                district_full_name = f"{city_name}{district}"
                print(f"\n----- 搜尋區域：{district_full_name} -----")
                
                # 對每個關鍵詞進行搜尋
                for keyword in keywords:
                    print(f"使用關鍵詞：{keyword}")
                    
                    # 搜尋並提取資料
                    maps_api.search_places(keyword, district_full_name)
                    keyword_data = maps_api.extract_place_data()
                    
                    # 添加不重複的資料到區域結果中
                    for place in keyword_data:
                        identifier = f"{place['店名']}_{place['地址']}"
                        if identifier not in existing_identifiers:
                            # 添加城市和區域標記
                            place["城市"] = main_city_names.get(city_name, city_name)
                            place["區域"] = district
                            
                            city_data.append(place)
                            existing_identifiers.add(identifier)
                    
                    print(f"使用關鍵詞「{keyword}」在「{district_full_name}」中找到 {len(keyword_data)} 筆資料，" 
                          f"累計不重複資料：{len(city_data)}")
            
            # 儲存該城市的資料
            normalized_city_name = main_city_names.get(city_name, city_name).replace("市", "")
            csv_file_path = os.path.join(output_dir, f"{normalized_city_name}寵物用品店家.csv")
            json_file_path = os.path.join(output_dir, f"{normalized_city_name}寵物用品店家.json")
            
            maps_api.save_to_csv(city_data, csv_file_path)
            maps_api.save_to_json(city_data, json_file_path)
            
            # 將該城市資料添加到總資料中
            all_pet_boarding_data.extend(city_data)
            
            # 記錄該城市的統計資訊
            city_stats[normalized_city_name] = len(city_data)
            
            print(f"\n完成 {city_name} 的資料搜集，共找到 {len(city_data)} 筆資料")
        
        # 儲存所有城市的合併資料
        all_csv_file_path = os.path.join(output_dir, "全台寵物用品店家.csv")
        all_json_file_path = os.path.join(output_dir, "全台寵物用品店家.json")
        
        maps_api.save_to_csv(all_pet_boarding_data, all_csv_file_path)
        maps_api.save_to_json(all_pet_boarding_data, all_json_file_path)
        
        # 輸出統計資訊
        print("\n========== 資料收集統計 ==========")
        for city, count in city_stats.items():
            print(f"{city}：{count} 筆資料")
        print(f"總計：{len(all_pet_boarding_data)} 筆資料")
        
    except Exception as e:
        import traceback
        print(f"執行過程中發生錯誤: {e}")
        traceback.print_exc()  # 打印詳細錯誤訊息

if __name__ == "__main__":
    main()