import json
import pandas as pd
import os

def filter_pet_boarding_shops(data, city_name):
    """過濾寵物住宿相關店家"""
    
    # 定義關鍵詞
    boarding_keywords = ["寄宿", "寄養", "住宿", "旅館", "旅宿", "旅行", "寄放", "過夜", "安親", "旅店", "hotel", "hostel", "寄居", "旅", "Inn"]
    pet_keywords = ["寵物", "毛孩", "狗", "貓", "汪", "犬", "喵", "毛", "寵", "兔", "動物", "兔子", "貓咪", "寵", "小愛", "pet", "dog", "cat", "兔", "Pet", "Dog", "Cat"]
    exclude_keywords = ["美容", "訓練", "spa", "洗澡", "剪", "用品", "商城", "商店", "食品", "獸醫", "醫院", "診所", "咖啡", "餐廳", "教學", "火化", "公園"]
    
    # 特殊需要包含的店家名稱列表
    special_include = ["花襪子的家寵物旅館", "好時光寵物旅館", "北歐寵物旅館", "宅貓旅館", 
                       "汪窩", "毛起來住", "狗窩", "巴克二世", "米菲寵物", "寵物之家", 
                       "Comfortable Pet", "汪汪旅店", "米可多", "愛寶貝", "寵物天地",
                       "愛犬之家", "狗狗家", "快樂狗", "喵星球"]
    
    # 過濾店家
    filtered_shops = []
    for shop in data:
        shop_name = shop['店名']
        
        # 特殊包含的店家
        if any(name in shop_name for name in special_include):
            filtered_shops.append(shop)
            continue
        
        # 檢查是否含有住宿關鍵詞
        has_boarding_keyword = any(keyword in shop_name.lower() for keyword in boarding_keywords)
        
        # 檢查是否含有寵物關鍵詞
        has_pet_keyword = any(keyword in shop_name.lower() for keyword in pet_keywords)
        
        # 檢查是否含有排除關鍵詞，但前提是沒有住宿關鍵詞
        has_exclude_keyword = not has_boarding_keyword and any(keyword in shop_name for keyword in exclude_keywords)
        
        # 如果有住宿關鍵詞和寵物關鍵詞，並且不是被排除的類型，則為住宿店家
        if (has_boarding_keyword and has_pet_keyword) and not has_exclude_keyword:
            filtered_shops.append(shop)
    
    print(f"{city_name}過濾後的寵物住宿店家數量: {len(filtered_shops)}")
    
    return filtered_shops

def process_city(city_name):
    """處理單一城市的資料"""
    
    # 檔案路徑
    input_dir = "E:/ntub/專題/數據/v1"
    output_dir = "E:/ntub/專題/數據/v1/過濾"
    
    input_path = f"{input_dir}/{city_name}寵物寄宿店家.json"
    output_json_path = f"{output_dir}/過濾{city_name}寵物住宿店家.json"
    output_csv_path = f"{output_dir}/過濾{city_name}寵物住宿店家.csv"
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 檢查輸入檔案是否存在
    if not os.path.exists(input_path):
        print(f"錯誤: 找不到 {input_path} 檔案")
        return False
    
    # 讀取JSON檔案
    print(f"讀取檔案: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"{city_name}原始資料共有 {len(data)} 筆")
    
    # 過濾店家
    filtered_shops = filter_pet_boarding_shops(data, city_name)
    
    # 顯示前10個過濾後的店家名稱
    print(f"\n{city_name}過濾後的前10個寵物住宿店家:")
    for i, shop in enumerate(filtered_shops[:10]):
        print(f"{i+1}. {shop['店名']}")
    
    # 存儲為JSON檔案
    print(f"\n將{city_name}結果保存為JSON檔案: {output_json_path}")
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_shops, f, ensure_ascii=False, indent=4)
    
    # 轉換為DataFrame並存儲為CSV檔案
    print(f"將{city_name}結果保存為CSV檔案: {output_csv_path}")
    df = pd.DataFrame(filtered_shops)
    df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    
    return True

def main():
    # 要處理的城市列表
    cities = ["台北", "台中", "台南", "桃園", "高雄", "新北"]
    
    successful_cities = 0
    for city in cities:
        print(f"\n{'-'*50}")
        print(f"開始處理 {city} 的寵物寄宿店家資料")
        print(f"{'-'*50}")
        
        if process_city(city):
            successful_cities += 1
        
        print(f"{'-'*50}")
    
    print(f"\n總共成功處理了 {successful_cities}/{len(cities)} 個城市的資料")
    print("\n處理完成!")
    print(f"過濾後的檔案已保存到 E:/ntub/專題/數據/v1/過濾 目錄下")

if __name__ == "__main__":
    main()