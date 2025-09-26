#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虛擬機 AI 客服設置檢查腳本
用於確保虛擬機上的 AI 客服環境配置正確
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def print_status(message, status="INFO"):
    """打印狀態訊息"""
    symbols = {"INFO": "[INFO]", "SUCCESS": "[✓]", "ERROR": "[✗]", "WARNING": "[!]"}
    print(f"{symbols.get(status, '[INFO]')} {message}")

def check_python_packages():
    """檢查必要的 Python 套件"""
    print_status("檢查 Python 套件...")

    required_packages = [
        'sentence-transformers',
        'chromadb',
        'pandas',
        'numpy',
        'torch'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_status(f"{package} - 已安裝", "SUCCESS")
        except ImportError:
            print_status(f"{package} - 未安裝", "ERROR")
            missing_packages.append(package)

    if missing_packages:
        print_status(f"需要安裝的套件: {', '.join(missing_packages)}", "WARNING")
        print_status("執行安裝指令:", "INFO")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    return True

def check_embedding_model():
    """檢查嵌入模型"""
    print_status("檢查 BAAI/bge-base-zh-v1.5 模型...")

    try:
        from sentence_transformers import SentenceTransformer

        print_status("正在載入模型...", "INFO")
        model = SentenceTransformer('BAAI/bge-base-zh-v1.5')

        # 檢查模型資訊
        dimension = model.get_sentence_embedding_dimension()
        max_length = model.max_seq_length

        print_status(f"模型維度: {dimension}", "SUCCESS")
        print_status(f"最大序列長度: {max_length}", "SUCCESS")

        # 測試編碼
        test_embedding = model.encode(["測試文本"])
        print_status(f"編碼測試成功，向量形狀: {test_embedding.shape}", "SUCCESS")

        if dimension != 768:
            print_status(f"警告：模型維度應該是 768，但實際是 {dimension}", "WARNING")
            return False

        return True

    except ImportError:
        print_status("sentence-transformers 未安裝", "ERROR")
        return False
    except Exception as e:
        print_status(f"模型載入失敗: {e}", "ERROR")
        return False

def check_vector_database():
    """檢查向量資料庫"""
    print_status("檢查向量資料庫...")

    db_dir = Path("rag/chroma_db")

    if not db_dir.exists():
        print_status("向量資料庫目錄不存在", "ERROR")
        print_status("請執行以下指令建立資料庫:", "INFO")
        print("python rebuild_vectordb.py")
        return False

    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=str(db_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_or_create_collection("faq_with_training")
        count = collection.count()

        print_status(f"向量資料庫文檔數: {count}", "SUCCESS")

        if count == 0:
            print_status("向量資料庫為空，需要重建", "WARNING")
            return False

        # 測試查詢
        results = collection.query(
            query_texts=["如何按讚"],
            n_results=1
        )

        if results and results['documents']:
            print_status("向量查詢測試成功", "SUCCESS")
            return True
        else:
            print_status("向量查詢測試失敗", "ERROR")
            return False

    except ImportError:
        print_status("chromadb 未安裝", "ERROR")
        return False
    except Exception as e:
        print_status(f"向量資料庫錯誤: {e}", "ERROR")
        return False

def check_ollama_service():
    """檢查 Ollama 服務"""
    print_status("檢查 Ollama 服務...")

    try:
        import requests

        # 檢查 Ollama 服務是否運行
        ollama_url = "http://127.0.0.1:11434/api/tags"
        response = requests.get(ollama_url, timeout=5)

        if response.status_code == 200:
            print_status("Ollama 服務運行中", "SUCCESS")

            # 檢查模型
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]

            required_model = "qwen2.5:3b-instruct"
            if required_model in models:
                print_status(f"模型 {required_model} 已安裝", "SUCCESS")
                return True
            else:
                print_status(f"模型 {required_model} 未安裝", "WARNING")
                print_status(f"執行安裝指令: ollama pull {required_model}", "INFO")
                return False
        else:
            print_status("Ollama 服務未響應", "ERROR")
            return False

    except requests.exceptions.ConnectionError:
        print_status("無法連接 Ollama 服務", "ERROR")
        print_status("請確認 Ollama 已安裝並執行: ollama serve", "INFO")
        return False
    except ImportError:
        print_status("requests 套件未安裝", "ERROR")
        return False
    except Exception as e:
        print_status(f"Ollama 檢查錯誤: {e}", "ERROR")
        return False

def check_django_settings():
    """檢查 Django 設定"""
    print_status("檢查 Django 設定...")

    # 檢查 .env 文件
    env_file = Path(".env")
    if not env_file.exists():
        print_status(".env 文件不存在", "ERROR")
        print_status("請確認已複製 .env 文件到專案根目錄", "INFO")
        return False

    try:
        # 讀取 .env 內容
        env_content = env_file.read_text(encoding='utf-8')

        # 檢查關鍵設定
        checks = [
            ("DEBUG=False", "生產環境設定"),
            ("pawday114404.duckdns.org", "域名設定"),
            ("https://pawday114404.duckdns.org", "HTTPS 設定")
        ]

        all_good = True
        for check, description in checks:
            if check in env_content:
                print_status(f"{description} - 正確", "SUCCESS")
            else:
                print_status(f"{description} - 需要檢查", "WARNING")
                all_good = False

        return all_good

    except UnicodeDecodeError:
        print_status(".env 文件編碼錯誤，請確保使用 UTF-8 編碼", "ERROR")
        return False
    except Exception as e:
        print_status(f"讀取 .env 文件時發生錯誤: {e}", "ERROR")
        return False

def test_ai_chat():
    """測試 AI 聊天功能"""
    print_status("測試 AI 聊天功能...")

    try:
        # 這裡可以添加實際的 AI 聊天測試
        # 暫時跳過，因為需要 Django 環境
        print_status("AI 聊天測試需要在 Django 環境中執行", "INFO")
        return True

    except Exception as e:
        print_status(f"AI 聊天測試失敗: {e}", "ERROR")
        return False

def create_rebuild_script():
    """創建向量資料庫重建腳本"""
    rebuild_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建向量資料庫腳本
"""
import pandas as pd
import os
import shutil
import sys

def rebuild_vector_db():
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        from chromadb.config import Settings

        print("載入嵌入模型...")
        embedder = SentenceTransformer('BAAI/bge-base-zh-v1.5')
        print(f'模型維度: {embedder.get_sentence_embedding_dimension()}')

        DB_DIR = 'rag/chroma_db'
        COLLECTION_NAME = 'faq_with_training'

        if os.path.exists(DB_DIR):
            shutil.rmtree(DB_DIR)
            print('已刪除舊的向量資料庫')

        print("建立新的向量資料庫...")
        client = chromadb.PersistentClient(
            path=DB_DIR,
            settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_or_create_collection(COLLECTION_NAME)

        # FAQ 資料
        faq_data = [
            {
                'id': 'Q1',
                'question': '寵物健康紀錄怎麼填寫？',
                'answer': '''寵物健康紀錄填寫的內容包括：基本生理數值檢查、觀察食慾和活動力狀況、定期測量體溫、記錄每日排便和小便情況、疫苗接種和定期健康檢查等。'''
            },
            {
                'id': 'Q2',
                'question': '如何在社群中按讚和留言？',
                'answer': '''在毛日好社群中進行互動：按讚功能 - 點擊貼文下方愛心圖示即可按讚；留言功能 - 點擊留言圖示，在輸入框寫下想法，點擊發送按鈕提交留言，也可使用Ctrl+Enter快速發送。需要登入會員才能按讚和留言。'''
            },
            {
                'id': 'Q3',
                'question': '社群功能有哪些？',
                'answer': '''毛日好社群提供：發文功能(分享寵物照片和生活動態)、互動功能(按讚、留言、分享)、瀏覽功能(瀏覽動態、搜尋貼文)、個人檔案管理等。所有功能都需要註冊登入。'''
            }
        ]

        documents = []
        metadatas = []
        ids = []

        for faq in faq_data:
            doc_text = f"問題：{faq['question']}\\n\\n回答：{faq['answer']}"
            documents.append(doc_text)
            metadatas.append({
                'id': faq['id'],
                'title': faq['question'],
                'source': 'FAQ'
            })
            ids.append(f"faq_{faq['id']}")

        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f'向量資料庫重建完成！總文檔數: {collection.count()}')
        return True

    except Exception as e:
        print(f'錯誤: {e}')
        return False

if __name__ == '__main__':
    rebuild_vector_db()
'''

    with open("rebuild_vectordb.py", "w", encoding="utf-8") as f:
        f.write(rebuild_script)

    print_status("已創建 rebuild_vectordb.py 腳本", "SUCCESS")

def main():
    """主要檢查流程"""
    print("=" * 50)
    print("虛擬機 AI 客服環境檢查")
    print("=" * 50)

    checks = [
        ("Python 套件", check_python_packages),
        ("嵌入模型", check_embedding_model),
        ("向量資料庫", check_vector_database),
        ("Ollama 服務", check_ollama_service),
        ("Django 設定", check_django_settings),
    ]

    results = {}

    for name, check_func in checks:
        print(f"\n--- {name} ---")
        try:
            results[name] = check_func()
        except Exception as e:
            print_status(f"{name} 檢查時發生錯誤: {e}", "ERROR")
            results[name] = False

    # 總結
    print("\n" + "=" * 50)
    print("檢查結果總結")
    print("=" * 50)

    all_passed = True
    for name, passed in results.items():
        status = "SUCCESS" if passed else "ERROR"
        print_status(f"{name}: {'通過' if passed else '失敗'}", status)
        if not passed:
            all_passed = False

    if all_passed:
        print_status("所有檢查通過！AI 客服環境配置正確", "SUCCESS")
    else:
        print_status("部分檢查失敗，請根據上述提示進行修正", "WARNING")

        # 創建修復腳本
        create_rebuild_script()

        print("\n修復建議:")
        print("1. 安裝缺失的 Python 套件")
        print("2. 執行 python rebuild_vectordb.py 重建向量資料庫")
        print("3. 確保 Ollama 服務運行並安裝模型")
        print("4. 檢查 .env 設定文件")

    return all_passed

if __name__ == "__main__":
    main()