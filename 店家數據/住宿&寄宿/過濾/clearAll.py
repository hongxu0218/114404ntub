import json
import pandas as pd
import os

def merge_city_data():
    """合併所有城市的寵物住宿店家資料"""
    
    # 檔案路徑
    input_dir = "E:/ntub/專題/數據/v1/過濾"
    output_dir = "E:/ntub/專題/數據/v1"
    
    output_json_path = f"{output_dir}/全台寵物寄宿店家.json"
    output_csv_path = f"{output_dir}/全台寵物寄宿店家.csv"
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 要處理的城市列表
    cities = ["台北", "台中", "台南", "桃園", "高雄", "新北"]
    
    # 合併所有城市的資料
    all_pet_boarding_shops = []
    total_shops = 0
    
    for city in cities:
        input_path = f"{input_dir}/過濾{city}寵物住宿店家.json"
        
        # 檢查輸入檔案是否存在
        if not os.path.exists(input_path):
            print(f"警告: 找不到 {input_path} 檔案，跳過此城市")
            continue
        
        # 讀取JSON檔案
        print(f"讀取檔案: {input_path}")
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                city_data = json.load(f)
            
            # 為每筆資料增加城市標記
            for shop in city_data:
                if '城市' not in shop:  # 如果原資料沒有城市欄位，則添加
                    shop['城市'] = city
            
            # 加入合併清單
            all_pet_boarding_shops.extend(city_data)
            
            # 計數
            print(f"{city}寵物住宿店家數量: {len(city_data)} 筆")
            total_shops += len(city_data)
            
        except Exception as e:
            print(f"處理 {city} 資料時發生錯誤: {e}")
    
    print(f"\n全台寵物寄宿店家總數: {total_shops} 筆")
    
    # 顯示合併後的前10個店家
    print("\n合併後的前10個寵物寄宿店家:")
    for i, shop in enumerate(all_pet_boarding_shops[:10]):
        print(f"{i+1}. {shop.get('城市', '未知')} - {shop['店名']}")
    
    # 存儲為JSON檔案
    print(f"\n將全台結果保存為JSON檔案: {output_json_path}")
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(all_pet_boarding_shops, f, ensure_ascii=False, indent=4)
    
    # 轉換為DataFrame並存儲為CSV檔案
    print(f"將全台結果保存為CSV檔案: {output_csv_path}")
    df = pd.DataFrame(all_pet_boarding_shops)
    df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    
    return total_shops

def main():
    print(f"{'-'*50}")
    print(f"開始合併所有城市的寵物寄宿店家資料")
    print(f"{'-'*50}")
    
    total_shops = merge_city_data()
    
    print(f"{'-'*50}")
    print(f"合併完成! 總共收集了 {total_shops} 家寵物寄宿店家")
    print(f"全台資料已保存到 E:/ntub/專題/數據/v1 目錄下")
    print(f"{'-'*50}")

if __name__ == "__main__":
    main()