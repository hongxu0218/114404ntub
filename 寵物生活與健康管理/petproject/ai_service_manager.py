#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 客服統一管理工具
整合所有 AI 客服相關功能：環境檢查、資料匯入、向量資料庫管理
"""

import os
import sys
import shutil
import json
import argparse
from pathlib import Path
import pandas as pd

def print_status(message, status="INFO"):
    """打印狀態訊息"""
    symbols = {
        "INFO": "[INFO] ",
        "SUCCESS": "[OK] ",
        "ERROR": "[ERROR] ",
        "WARNING": "[WARN] ",
        "WORKING": "[WORK] "
    }
    print(f"{symbols.get(status, '[INFO] ')}{message}")

def check_dependencies():
    """檢查所需依賴"""
    print_status("檢查 Python 依賴套件...", "WORKING")

    required_packages = {
        'sentence-transformers': '嵌入模型',
        'chromadb': '向量資料庫',
        'pandas': '資料處理',
        'numpy': '數值計算',
        'requests': 'HTTP 請求',
        'openpyxl': 'Excel 讀取'
    }

    missing = []
    for package, desc in required_packages.items():
        try:
            __import__(package.replace('-', '_'))
            print_status(f"{desc} ({package}) - 已安裝", "SUCCESS")
        except ImportError:
            print_status(f"{desc} ({package}) - 未安裝", "ERROR")
            missing.append(package)

    if missing:
        print_status(f"請安裝缺失套件: pip install {' '.join(missing)}", "WARNING")
        return False
    return True

def load_excel_data():
    """載入 Excel 資料"""
    print_status("載入 Excel 資料...", "WORKING")

    data_dir = Path("rag/data")
    if not data_dir.exists():
        print_status("rag/data 目錄不存在", "ERROR")
        return []

    faq_data = []
    excel_files = list(data_dir.glob("*.xlsx"))

    if not excel_files:
        print_status("未找到 Excel 檔案", "WARNING")
        return get_default_faq_data()

    for excel_file in excel_files:
        try:
            print_status(f"讀取 {excel_file.name}...", "INFO")
            df = pd.read_excel(excel_file)

            # 檢查欄位名稱
            print_status(f"欄位: {list(df.columns)}", "INFO")

            # 尋找問題和回答欄位
            question_col = None
            answer_col = None

            for col in df.columns:
                col_lower = str(col).lower()
                if any(word in col_lower for word in ['問題', 'question', '題目']):
                    question_col = col
                elif any(word in col_lower for word in ['回答', 'answer', '答案', '內容']):
                    answer_col = col

            if question_col and answer_col:
                for idx, row in df.iterrows():
                    if pd.notna(row[question_col]) and pd.notna(row[answer_col]):
                        faq_data.append({
                            'id': f'Q{len(faq_data)+1}',
                            'question': str(row[question_col]).strip(),
                            'answer': str(row[answer_col]).strip(),
                            'source': excel_file.stem
                        })

                print_status(f"從 {excel_file.name} 載入 {len([r for r in df.iterrows()])} 筆資料", "SUCCESS")
            else:
                print_status(f"{excel_file.name} 缺少問題或回答欄位", "WARNING")

        except Exception as e:
            print_status(f"讀取 {excel_file.name} 失敗: {e}", "ERROR")

    if not faq_data:
        print_status("Excel 檔案無有效資料，使用預設資料", "WARNING")
        return get_default_faq_data()

    print_status(f"總共載入 {len(faq_data)} 筆 FAQ 資料", "SUCCESS")
    return faq_data

def get_default_faq_data():
    """預設 FAQ 資料"""
    return [
        {
            'id': 'Q1',
            'question': '寵物健康紀錄怎麼填寫？',
            'answer': '''寵物健康紀錄填寫的內容包括：

1. 基本生理數值檢查
2. 觀察食慾和活動力狀況
3. 定期測量體溫
4. 記錄每日排便和小便情況
5. 疫苗接種和定期健康檢查
6. 注意特殊症狀紀錄
7. 體重變化和成長記錄
8. 行為異常和情緒變化
9. 運動時間和強度記錄

注意事項：
• 出現多個症狀應立即就醫
• 幼齡和高齡寵物需特別注意
• 症狀持續超過24小時建議就醫''',
            'source': 'default'
        },
        {
            'id': 'Q2',
            'question': '如何幫寵物洗澡？',
            'answer': '''正確幫寵物洗澡的步驟：

準備工作：
1. 準備適溫的洗澡水（38-40度C）
2. 準備寵物專用洗毛精
3. 毛巾和吹風機

洗澡步驟：
1. 先用溫水沖洗寵物全身
2. 避免水進入耳朵和眼睛
3. 輕輕按摩並清潔毛髮
4. 徹底沖洗乾淨
5. 用毛巾輕拍吸水
6. 徹底吹乾避免感冒

注意事項：
• 狗狗每1-2個月一次
• 貓咪通常不需要經常洗澡
• 幼齡、生病寵物應避免洗澡''',
            'source': 'default'
        },
        {
            'id': 'Q3',
            'question': '寵物疫苗接種時程？',
            'answer': '''寵物疫苗接種的完整時程：

幼犬疫苗時程：
• 6-8週：第一劑疫苗
• 10-12週：第二劑疫苗
• 14-16週：第三劑疫苗
• 16週以後：狂犬病疫苗

幼貓疫苗時程：
• 8-10週：第一劑疫苗
• 12-14週：第二劑疫苗
• 16週以後：狂犬病疫苗

注意事項：
• 疫苗前確保寵物身體健康
• 避免在疫苗期間洗澡
• 建立完整的疫苗紀錄''',
            'source': 'default'
        },
        {
            'id': 'Q4',
            'question': '如何在社群中按讚和留言？',
            'answer': '''在毛日好社群中進行互動的步驟：

按讚功能：
1. 在社群動態頁面瀏覽貼文
2. 點擊貼文下方的愛心圖示即可按讚
3. 再次點擊可以取消按讚
4. 按讚數會即時更新顯示

留言功能：
1. 點擊貼文下方的留言圖示
2. 在留言輸入框中寫下你的想法
3. 點擊「發送」按鈕提交留言
4. 也可以使用 Ctrl+Enter 快速發送留言
5. 可以對其他人的留言按讚

注意事項：
• 需要登入會員才能按讚和留言
• 請保持友善的互動環境
• 可以隨時刪除自己的留言''',
            'source': 'default'
        },
        {
            'id': 'Q5',
            'question': '社群功能有哪些？',
            'answer': '''毛日好社群提供以下功能：

發文功能：
1. 分享寵物照片和生活動態
2. 撰寫寵物照護心得
3. 發布寵物相關問題求助

互動功能：
1. 按讚：對喜歡的貼文按讚支持
2. 留言：與其他寵物家長交流討論
3. 分享：將實用內容分享給朋友

瀏覽功能：
1. 瀏覽其他用戶的寵物動態
2. 搜尋特定主題的貼文
3. 查看熱門貼文排行

個人檔案：
1. 編輯個人資料和寵物資訊
2. 查看自己的發文記錄
3. 管理追蹤和粉絲''',
            'source': 'default'
        },
        {
            'id': 'Q6',
            'question': '如何發布寵物動態貼文？',
            'answer': '''發布寵物動態貼文的步驟：

發文步驟：
1. 進入「毛日好社群」頁面
2. 在發文區域點擊「分享你的想法...」
3. 輸入想要分享的內容
4. 可以上傳寵物照片或影片
5. 選擇適當的標籤分類
6. 點擊「發布」按鈕完成

內容建議：
• 分享寵物可愛瞬間
• 記錄寵物成長過程
• 分享照護心得和經驗
• 提問寵物相關疑問
• 推薦好用的寵物用品

注意事項：
• 確保照片清晰且適當
• 內容積極正面
• 尊重其他用戶隱私''',
            'source': 'default'
        }
    ]

def detect_embedding_model():
    """自動偵測適合的嵌入模型"""
    print_status("偵測最佳嵌入模型...", "WORKING")

    models_to_try = [
        {
            'name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
            'expected_dim': 384,
            'description': '多語言模型 (384維)'
        },
        {
            'name': 'BAAI/bge-small-zh-v1.5',
            'expected_dim': 768,
            'description': '中文優化模型 (768維)'
        },
        {
            'name': 'BAAI/bge-base-zh-v1.5',
            'expected_dim': 768,
            'description': '中文基礎模型 (768維)'
        }
    ]

    for model_info in models_to_try:
        try:
            from sentence_transformers import SentenceTransformer
            print_status(f"測試 {model_info['description']}...", "INFO")
            model = SentenceTransformer(model_info['name'])
            actual_dim = model.get_sentence_embedding_dimension()

            if actual_dim == model_info['expected_dim']:
                print_status(f"使用模型: {model_info['description']}", "SUCCESS")
                return model_info['name'], actual_dim
            else:
                print_status(f"維度不符: 期望 {model_info['expected_dim']}, 實際 {actual_dim}", "WARNING")

        except Exception as e:
            print_status(f"載入失敗: {e}", "ERROR")
            continue

    print_status("無法找到適合的模型", "ERROR")
    return None, None

def build_vector_database(faq_data, model_name, force_rebuild=False):
    """建立向量資料庫"""
    print_status("建立向量資料庫...", "WORKING")

    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        from chromadb.config import Settings

        DB_DIR = 'rag/chroma_db'
        COLLECTION_NAME = 'faq_with_training'

        # 檢查是否需要重建
        if os.path.exists(DB_DIR) and not force_rebuild:
            try:
                client = chromadb.PersistentClient(
                    path=DB_DIR,
                    settings=Settings(anonymized_telemetry=False)
                )
                collection = client.get_or_create_collection(COLLECTION_NAME)
                existing_count = collection.count()

                if existing_count > 0:
                    print_status(f"發現現有資料庫 ({existing_count} 筆文檔)", "INFO")
                    response = input("是否重建資料庫？ (y/N): ").lower().strip()
                    if response != 'y':
                        print_status("使用現有資料庫", "SUCCESS")
                        return True
            except:
                pass

        # 載入模型
        print_status(f"載入嵌入模型: {model_name}", "INFO")
        embedder = SentenceTransformer(model_name)
        model_dim = embedder.get_sentence_embedding_dimension()
        print_status(f"模型維度: {model_dim}", "INFO")

        # 刪除舊資料庫
        if os.path.exists(DB_DIR):
            shutil.rmtree(DB_DIR)
            print_status("已刪除舊的向量資料庫", "INFO")

        # 建立新資料庫
        client = chromadb.PersistentClient(
            path=DB_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        collection = client.get_or_create_collection(COLLECTION_NAME)

        # 準備文檔
        documents = []
        metadatas = []
        ids = []

        for faq in faq_data:
            doc_text = f"問題：{faq['question']}\n\n回答：{faq['answer']}"
            documents.append(doc_text)
            metadatas.append({
                'id': faq['id'],
                'title': faq['question'],
                'source': faq.get('source', 'unknown')
            })
            ids.append(f"faq_{faq['id']}")

        # 建立向量
        print_status(f"處理 {len(documents)} 筆文檔...", "WORKING")
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        final_count = collection.count()
        print_status(f"向量資料庫建立完成！總文檔數: {final_count}", "SUCCESS")

        # 測試查詢
        test_queries = ['如何按讚', '寵物健康', '疫苗接種']
        print_status("測試向量檢索...", "WORKING")

        for query in test_queries:
            results = collection.query(
                query_texts=[query],
                n_results=1,
                include=['metadatas', 'distances']
            )

            if results and results['metadatas']:
                similarity = 1 - results['distances'][0][0]
                title = results['metadatas'][0][0]['title']
                print_status(f"查詢「{query}」→ {title} (相似度: {similarity:.3f})", "SUCCESS")
            else:
                print_status(f"查詢「{query}」→ 無結果", "WARNING")

        return True

    except Exception as e:
        print_status(f"建立向量資料庫失敗: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def update_chat_service_config(model_name):
    """更新 chat_service.py 的模型配置"""
    print_status("更新 chat_service.py 配置...", "WORKING")

    chat_service_path = Path("petapp/chat_service.py")
    if not chat_service_path.exists():
        print_status("chat_service.py 不存在", "ERROR")
        return False

    try:
        # 讀取原始檔案
        with open(chat_service_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 更新模型配置
        old_pattern = 'SentenceTransformer("'
        new_model_line = f'SentenceTransformer("{model_name}")  # 自動配置'

        # 尋找並替換第一個 SentenceTransformer 調用
        import re
        pattern = r'_embedder = SentenceTransformer\([^)]+\)'
        replacement = f'_embedder = {new_model_line}'

        new_content = re.sub(pattern, replacement, content, count=1)

        if new_content != content:
            with open(chat_service_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print_status(f"已更新模型配置為: {model_name}", "SUCCESS")
            return True
        else:
            print_status("未找到需要更新的配置", "WARNING")
            return False

    except Exception as e:
        print_status(f"更新配置失敗: {e}", "ERROR")
        return False

def test_ai_service():
    """測試 AI 客服服務"""
    print_status("測試 AI 客服服務...", "WORKING")

    try:
        import requests

        # 測試知識庫狀態
        kb_url = 'http://127.0.0.1:8000/api/chat/kb_status'
        response = requests.get(kb_url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print_status(f"知識庫狀態: {data.get('count', 0)} 筆文檔", "SUCCESS")
            if data.get('error'):
                print_status(f"知識庫錯誤: {data['error']}", "ERROR")
                return False
        else:
            print_status("無法連接到 Django 服務", "ERROR")
            return False

        # 測試 AI 聊天
        test_queries = [
            '如何按讚和留言',
            '寵物健康紀錄怎麼填寫',
            '社群功能有哪些'
        ]

        for query in test_queries:
            chat_url = 'http://127.0.0.1:8000/api/chat/'
            chat_data = {
                'message': query,
                'history': []
            }

            response = requests.post(chat_url, json=chat_data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                reply = result.get('reply', '')
                sources = len(result.get('sources', []))

                if '沒有找到相關資訊' in reply:
                    print_status(f"「{query}」→ 未找到資訊", "ERROR")
                else:
                    print_status(f"「{query}」→ 回答正常 (來源: {sources})", "SUCCESS")
            else:
                print_status(f"「{query}」→ API 錯誤", "ERROR")

        return True

    except Exception as e:
        print_status(f"測試失敗: {e}", "ERROR")
        return False

def main():
    """主程式"""
    parser = argparse.ArgumentParser(description='AI 客服統一管理工具')
    parser.add_argument('command', choices=[
        'check',      # 檢查環境
        'import',     # 匯入資料
        'build',      # 建立向量資料庫
        'rebuild',    # 強制重建向量資料庫
        'test',       # 測試服務
        'setup',      # 完整安裝設定
        'status'      # 檢查狀態
    ], help='執行的命令')

    parser.add_argument('--model', help='指定嵌入模型')
    parser.add_argument('--force', action='store_true', help='強制執行')

    args = parser.parse_args()

    print("=" * 60)
    print("AI 客服統一管理工具")
    print("=" * 60)

    if args.command == 'check':
        print_status("檢查環境依賴...", "INFO")
        success = check_dependencies()
        if success:
            print_status("環境檢查完成，所有依賴已安裝", "SUCCESS")
        else:
            print_status("環境檢查失敗，請安裝缺失的套件", "ERROR")

    elif args.command == 'import':
        print_status("匯入 Excel 資料...", "INFO")
        faq_data = load_excel_data()
        print_status(f"資料匯入完成，共 {len(faq_data)} 筆 FAQ", "SUCCESS")

    elif args.command in ['build', 'rebuild']:
        force = args.command == 'rebuild' or args.force

        if not check_dependencies():
            return

        faq_data = load_excel_data()

        model_name = args.model
        if not model_name:
            model_name, model_dim = detect_embedding_model()
            if not model_name:
                return

        success = build_vector_database(faq_data, model_name, force_rebuild=force)
        if success:
            update_chat_service_config(model_name)
            print_status("向量資料庫建立完成", "SUCCESS")
        else:
            print_status("向量資料庫建立失敗", "ERROR")

    elif args.command == 'test':
        success = test_ai_service()
        if success:
            print_status("AI 客服服務測試完成", "SUCCESS")
        else:
            print_status("AI 客服服務測試失敗", "ERROR")

    elif args.command == 'setup':
        print_status("執行完整安裝設定...", "INFO")

        # 1. 檢查依賴
        if not check_dependencies():
            print_status("請先安裝所有必要套件", "ERROR")
            return

        # 2. 載入資料
        faq_data = load_excel_data()

        # 3. 偵測模型
        model_name, model_dim = detect_embedding_model()
        if not model_name:
            return

        # 4. 建立資料庫
        if build_vector_database(faq_data, model_name, force_rebuild=True):
            update_chat_service_config(model_name)
            print_status("完整設定完成！", "SUCCESS")
            print_status("請重新啟動 Django 服務以套用設定", "INFO")
        else:
            print_status("設定失敗", "ERROR")

    elif args.command == 'status':
        print_status("檢查 AI 客服狀態...", "INFO")
        check_dependencies()
        test_ai_service()

if __name__ == '__main__':
    main()