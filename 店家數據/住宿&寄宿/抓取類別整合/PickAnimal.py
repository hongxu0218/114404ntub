import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urlparse
import os
import csv
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# 定義寵物類型關鍵字
GENERAL_PET_KEYWORDS = ['寵物', '毛小孩', '寵物旅館', '寵物住宿']

DOG_GENERAL_KEYWORDS = ['狗', '犬', '汪', '狗狗', '犬隻', '汪星人', '犬舍']
DOG_SIZE_KEYWORDS = {
    '小型犬': ['小型犬', '小型狗', '小狗', '小型', '迷你犬', '柴犬', '吉娃娃', '貴賓', '約克夏', '臘腸', '馬爾濟斯', '博美', '比熊', '西施'],
    '中型犬': ['中型犬', '中型狗', '中型', '邊境牧羊犬', '柯基', '米格魯', '秋田', '鬥牛犬', '牧羊犬'],
    '大型犬': ['大型犬', '大型狗', '大型', '拉布拉多', '黃金獵犬', '德國牧羊犬', '哈士奇', '薩摩耶', '大丹', '聖伯納', '杜賓', '阿拉斯加'],
}

CAT_KEYWORDS = ['貓', '貓咪', '喵星人', '貓奴', '貓砂', '貓爪', '貓籠', '貓屋', '貓食', '喵']

OTHER_PET_KEYWORDS = {
    '兔子': ['兔子', '兔兔', '長耳兔', '兔舍', '兔籠'],
    '倉鼠': ['倉鼠', '鼠', '倉鼠籠', '鼠窩'],
    '鳥類': ['鳥', '鸚鵡', '鳥類', '鳥籠', '鳥舍', '鳥窩'],
    '爬蟲類': ['爬蟲', '蜥蜴', '蛇', '烏龜', '守宮', '爬蟲箱', '蛇籠'],
    '其他小動物': ['刺蝟', '松鼠', '天竺鼠', '雪貂', '水豚', '蜜袋鼯']
}

def clean_url(url):
    """清理並驗證URL"""
    if not url or pd.isna(url):
        return None
    
    # 確保URL以http或https開頭
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    # 驗證URL格式
    try:
        result = urlparse(url)
        return url if all([result.scheme, result.netloc]) else None
    except:
        return None

def fetch_website_content(url, timeout=10):
    """抓取網站內容"""
    if not url:
        return None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            # 嘗試檢測並設置正確的編碼
            if response.encoding == 'ISO-8859-1':
                encodings = ['utf-8', 'big5', 'gbk']
                for enc in encodings:
                    try:
                        response.encoding = enc
                        response.text.encode(enc)
                        break
                    except UnicodeEncodeError:
                        continue
            
            return response.text
        return None
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return None

def check_keywords_in_text(text, keyword_dict):
    """檢查文本中是否包含指定的關鍵字"""
    if not text:
        return {}
    
    result = {}
    for category, keywords in keyword_dict.items():
        for keyword in keywords:
            if keyword in text:
                result[category] = True
                break
    
    return result

def analyze_store_webpage(row):
    """分析店家網頁，檢查支援的寵物類型"""
    store_name = row['店名'] if not pd.isna(row['店名']) else "未命名店家"
    website = clean_url(row['網站'])
    
    # 初始化結果
    result = {
        '店名': store_name,
        '網站': website,
        '地址': row['地址'] if not pd.isna(row['地址']) else "",
        '電話': row['電話'] if not pd.isna(row['電話']) else "",
        '營業時間': row['營業時間'] if not pd.isna(row['營業時間']) else "",
        '評分': row['評分'] if not pd.isna(row['評分']) else "",
        '評分數量': row['評分數量'] if not pd.isna(row['評分數量']) else "",
        '城市': row['城市'] if not pd.isna(row['城市']) else "",
        '區域': row['區域'] if not pd.isna(row['區域']) else "",
        '接受狗': False,
        '接受貓': False
    }
    
    # 如果沒有網站，檢查店名和營業時間中的關鍵字
    store_text = str(store_name) + " " + str(row.get('營業時間', ''))
    
    # 檢查是否明確提及狗或貓
    dog_mentioned = False
    cat_mentioned = False
    
    # 檢查是否支援狗
    for keyword in DOG_GENERAL_KEYWORDS:
        if keyword in store_text:
            dog_mentioned = True
            result['接受狗'] = True
            break
            
    # 檢查是否支援貓
    for keyword in CAT_KEYWORDS:
        if keyword in store_text:
            cat_mentioned = True
            result['接受貓'] = True
            break
    
    # 檢查店名和營業時間中的關鍵字
    dog_size_results = check_keywords_in_text(store_text, DOG_SIZE_KEYWORDS)
    other_pet_results = check_keywords_in_text(store_text, OTHER_PET_KEYWORDS)
    
    # 如果有網站且不是特殊名單中的網站，爬取網站內容
    special_sites = ["thepaw.com.tw", "facebook.com/profile.php?id=100087392181167", "facebook.com/Ponpon.Pet.hotel"]
    skip_crawling = False
    
    if website:
        # 檢查是否在特殊名單中
        for site in special_sites:
            if site in website:
                skip_crawling = True
                break
        
        if not skip_crawling:
            print(f"正在爬取 {store_name} 的網站: {website}")
            html_content = fetch_website_content(website)
            
            if html_content:
                # 解析HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 取得純文字內容
                website_text = soup.get_text(separator=" ", strip=True)
                
                # 檢查網站是否明確提及狗或貓
                if not dog_mentioned:
                    for keyword in DOG_GENERAL_KEYWORDS:
                        if keyword in website_text:
                            dog_mentioned = True
                            result['接受狗'] = True
                            break
                            
                if not cat_mentioned:
                    for keyword in CAT_KEYWORDS:
                        if keyword in website_text:
                            cat_mentioned = True
                            result['接受貓'] = True
                            break
                
                # 檢查網站內容中的通用寵物關鍵字
                general_pet_mentioned = False
                for keyword in GENERAL_PET_KEYWORDS:
                    if keyword in website_text:
                        general_pet_mentioned = True
                        break
                
                # 只有在沒有明確提及狗或貓的情況下，才考慮通用寵物關鍵字
                # 如果已經提到貓，通用寵物關鍵字不應該暗示也接受狗
                # 如果已經提到狗，通用寵物關鍵字不應該暗示也接受貓
                if general_pet_mentioned:
                    if not dog_mentioned and not cat_mentioned:
                        # 如果只有通用寵物關鍵字，但沒有明確提及狗或貓，
                        # 我們需要進一步判斷
                        # 檢查店名中是否暗示只接受某種寵物
                        is_dog_exclusive = False
                        is_cat_exclusive = False
                        
                        # 如果店名中包含"狗"相關詞但不包含"貓"相關詞，可能是狗專門店
                        for keyword in DOG_GENERAL_KEYWORDS:
                            if keyword in store_name:
                                is_dog_exclusive = True
                                break
                        
                        # 如果店名中包含"貓"相關詞但不包含"狗"相關詞，可能是貓專門店
                        for keyword in CAT_KEYWORDS:
                            if keyword in store_name:
                                is_cat_exclusive = True
                                break
                        
                        # 根據店名判斷處理通用寵物關鍵字
                        if is_dog_exclusive and not is_cat_exclusive:
                            # 如果店名暗示只接受狗
                            result['接受狗'] = True
                        elif is_cat_exclusive and not is_dog_exclusive:
                            # 如果店名暗示只接受貓
                            result['接受貓'] = True
                        else:
                            # 如果店名沒有特殊暗示，預設同時接受狗和貓
                            result['接受狗'] = True
                            result['接受貓'] = True
                
                # 檢查網站內容中的關鍵字
                web_dog_size_results = check_keywords_in_text(website_text, DOG_SIZE_KEYWORDS)
                web_other_pet_results = check_keywords_in_text(website_text, OTHER_PET_KEYWORDS)
                
                # 合併結果
                for key, value in web_dog_size_results.items():
                    dog_size_results[key] = True
                
                for key, value in web_other_pet_results.items():
                    other_pet_results[key] = True
    
    # 將犬隻大小結果添加到返回值 (如果找到特定大小類型，也標記為接受狗)
    has_specific_dog_size = False
    for dog_size, _ in DOG_SIZE_KEYWORDS.items():
        is_supported = dog_size in dog_size_results
        result[f'接受{dog_size}'] = is_supported
        if is_supported:
            has_specific_dog_size = True
            result['接受狗'] = True
    
    # 如果明確支援狗但沒有特定大小信息，將所有大小標記為"可能支援"
    if result['接受狗'] and not has_specific_dog_size:
        result['接受小型犬'] = True
        result['接受中型犬'] = True
        result['接受大型犬'] = True
    
    # 添加其他寵物類型結果
    for pet_type, _ in OTHER_PET_KEYWORDS.items():
        result[f'接受{pet_type}'] = pet_type in other_pet_results
    
    # 添加一個綜合評估欄位
    accepted_types = []
    
    # 先檢查是否支援狗和貓
    if result['接受狗']:
        # 檢查是否有特定大小
        dog_sizes = []
        if result['接受小型犬']: dog_sizes.append('小型犬')
        if result['接受中型犬']: dog_sizes.append('中型犬')
        if result['接受大型犬']: dog_sizes.append('大型犬')
        
        if dog_sizes:
            accepted_types.extend(dog_sizes)
        else:
            accepted_types.append('狗')
    
    if result['接受貓']:
        accepted_types.append('貓')
    
    # 添加其他寵物類型
    for key, value in result.items():
        if key.startswith('接受') and value and key not in ['接受狗', '接受貓', '接受小型犬', '接受中型犬', '接受大型犬']:
            accepted_types.append(key[2:])  # 去掉「接受」兩個字
    
    result['支援寵物類型'] = '、'.join(accepted_types) if accepted_types else '未明確說明'
    
    return result

def process_csv(input_file, output_file, unclear_output_file, max_workers=5, sample_size=None):
    """處理CSV檔案並分析店家網站
    
    Args:
        input_file (str): 輸入CSV檔案路徑
        output_file (str): 輸出CSV檔案路徑
        unclear_output_file (str): 未明確說明店家的輸出CSV檔案路徑
        max_workers (int, optional): 最大同時處理的線程數. Defaults to 5.
        sample_size (int, optional): 處理的樣本數量. Defaults to None (全部處理).
    """
    # 讀取CSV
    try:
        df = pd.read_csv(input_file, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(input_file, encoding='big5')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(input_file, encoding='gbk')
            except:
                raise Exception("無法讀取CSV檔案，請確認編碼格式。")
    
    print(f"成功載入CSV檔案，共 {len(df)} 筆資料")
    
    # 如果指定了取樣大小，隨機選擇一部分資料
    if sample_size and sample_size < len(df):
        df = df.sample(n=sample_size, random_state=42)
        print(f"隨機選取 {sample_size} 筆資料進行分析")
    
    results = []
    
    # 使用多線程處理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_row = {executor.submit(analyze_store_webpage, row): idx for idx, row in df.iterrows()}
        
        # 處理完成的任務
        for i, future in enumerate(as_completed(future_to_row)):
            try:
                result = future.result()
                results.append(result)
                
                # 每處理10筆資料顯示進度
                if (i + 1) % 10 == 0 or i + 1 == len(future_to_row):
                    print(f"已處理 {i + 1}/{len(future_to_row)} 筆資料 ({(i + 1) / len(future_to_row) * 100:.1f}%)")
                
                # 防止請求過於頻繁
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                idx = future_to_row[future]
                print(f"處理第 {idx} 筆資料時發生錯誤: {str(e)}")
    
    # 將結果轉換為DataFrame
    result_df = pd.DataFrame(results)
    
    # 分離未明確說明的店家
    unclear_df = result_df[result_df['支援寵物類型'] == '未明確說明'].copy()
    
    # 保存結果
    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"分析完成！結果已保存至 {output_file}")
    
    # 保存未明確說明的店家資料
    if not unclear_df.empty:
        # 確保 unclear_output_file 是字串
        if not isinstance(unclear_output_file, str):
            unclear_output_file = str(unclear_output_file)
        
        unclear_df.to_csv(unclear_output_file, index=False, encoding='utf-8-sig')
        print(f"已將 {len(unclear_df)} 筆未明確說明的店家資料保存至 {unclear_output_file}")
    else:
        print("沒有發現未明確說明的店家資料")
    
    # 顯示統計資訊
    print("\n=== 分析統計 ===")
    
    # 狗貓接受統計
    dog_count = sum(result_df['接受狗'])
    cat_count = sum(result_df['接受貓'])
    print(f"接受狗的店家數量: {dog_count} ({dog_count/len(result_df)*100:.1f}%)")
    print(f"接受貓的店家數量: {cat_count} ({cat_count/len(result_df)*100:.1f}%)")
    
    # 犬隻大小統計
    print("\n=== 犬隻大小統計 ===")
    for dog_size in DOG_SIZE_KEYWORDS.keys():
        count = sum(result_df[f'接受{dog_size}'])
        print(f"接受{dog_size}的店家數量: {count} ({count/len(result_df)*100:.1f}%)")
    
    # 其他寵物統計
    print("\n=== 其他寵物統計 ===")
    for pet_type in OTHER_PET_KEYWORDS.keys():
        count = sum(result_df[f'接受{pet_type}'])
        print(f"接受{pet_type}的店家數量: {count} ({count/len(result_df)*100:.1f}%)")
    
    # 顯示接受多種寵物的店家比例
    print("\n=== 多樣性統計 ===")
    # 計算每家店接受的寵物種類數
    pet_type_counts = []
    for _, row in result_df.iterrows():
        count = 0
        if row['接受狗']: count += 1
        if row['接受貓']: count += 1
        for pet_type in OTHER_PET_KEYWORDS.keys():
            if row[f'接受{pet_type}']: count += 1
        pet_type_counts.append(count)
    
    # 統計接受0,1,2,3+種寵物的店家數量
    zero_count = sum(1 for c in pet_type_counts if c == 0)
    one_count = sum(1 for c in pet_type_counts if c == 1)
    two_count = sum(1 for c in pet_type_counts if c == 2)
    three_plus_count = sum(1 for c in pet_type_counts if c >= 3)
    
    print(f"未明確說明接受任何寵物的店家: {zero_count} ({zero_count/len(result_df)*100:.1f}%)")
    print(f"僅接受一種寵物的店家: {one_count} ({one_count/len(result_df)*100:.1f}%)")
    print(f"接受兩種寵物的店家: {two_count} ({two_count/len(result_df)*100:.1f}%)")
    print(f"接受三種或以上寵物的店家: {three_plus_count} ({three_plus_count/len(result_df)*100:.1f}%)")

if __name__ == "__main__":
    # 設定檔案路徑
    input_file = "全台寵物寄宿店家.csv"  # 輸入檔案名稱
    output_file = "寵物寄宿店家分析結果.csv"  # 輸出檔案名稱
    unclear_output_file = "未明確說明寵物寄宿店家.csv"  # 未明確說明店家的輸出檔案
    
    # 使用者可自訂參數
    max_workers = 5  # 最大同時處理的線程數
    sample_size = None  # 設置為整數值可以只處理部分資料，None表示處理全部資料
    
    # 執行分析
    process_csv(input_file, output_file, unclear_output_file, max_workers, sample_size)
    
    # 程式執行完畢
    print("程式執行完畢。")