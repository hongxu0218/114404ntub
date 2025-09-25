#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import django
import pandas as pd

# 設定Django環境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

# 現在可以導入Django的chat_service
from petapp import chat_service
import chromadb
from chromadb.config import Settings

def rebuild_django_kb():
    print("=== 重建Django AI客服知識庫 ===\n")

    # 檢查必要組件
    if not chat_service._embedder:
        print("嵌入模型未載入")
        return

    print(f"嵌入模型: {chat_service._embedder}")
    print(f"DB路徑: {chat_service.DB_DIR}")
    print(f"集合名: {chat_service.COLLECTION_NAME}")

    # 讀取Excel資料
    try:
        df = pd.read_excel('data/platform_manual.xlsx')
        print(f"✅ 成功讀取Excel，共{len(df)}行資料")
    except Exception as e:
        print(f"❌ 讀取Excel失敗: {e}")
        return

    # 初始化ChromaDB客戶端
    try:
        client = chromadb.PersistentClient(
            path=chat_service.DB_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        print("✅ ChromaDB客戶端初始化成功")
    except Exception as e:
        print(f"❌ ChromaDB初始化失敗: {e}")
        return

    # 刪除舊集合並創建新集合
    try:
        client.delete_collection(chat_service.COLLECTION_NAME)
        print(f"✅ 已刪除舊集合: {chat_service.COLLECTION_NAME}")
    except Exception:
        print("⚠️  舊集合不存在，跳過刪除")

    try:
        collection = client.create_collection(chat_service.COLLECTION_NAME)
        print(f"✅ 已創建新集合: {chat_service.COLLECTION_NAME}")
    except Exception as e:
        print(f"❌ 創建集合失敗: {e}")
        return

    # 處理資料並加入集合
    documents = []
    metadatas = []
    ids = []

    for idx, row in df.iterrows():
        q = str(row.get('Question', '')).strip()
        a = str(row.get('Answer', '')).strip()

        if q and a:
            # 組合問答對
            combined_text = f"Q: {q}\nA: {a}"
            documents.append(combined_text)
            metadatas.append({
                'question': q,
                'answer': a,
                'source': 'platform_manual',
                'id': f"qa_{idx+1}"
            })
            ids.append(f"qa_{idx+1}")

    if not documents:
        print("❌ 沒有有效的問答資料")
        return

    print(f"✅ 準備加入 {len(documents)} 個文檔")

    # 批量加入文檔
    try:
        # 生成嵌入向量
        embeddings = chat_service._embedder.encode(documents, normalize_embeddings=True).tolist()
        print(f"✅ 生成 {len(embeddings)} 個嵌入向量，維度: {len(embeddings[0])}")

        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ 成功加入 {len(documents)} 個文檔到集合")

    except Exception as e:
        print(f"❌ 加入文檔失敗: {e}")
        return

    # 驗證重建結果
    try:
        count = collection.count()
        print(f"✅ 集合總文檔數: {count}")

        # 測試查詢
        test_queries = ["忘記密碼怎麼辦？", "註冊帳號", "如何登入"]
        print("\n=== 測試查詢 ===")

        for query in test_queries:
            try:
                context, sources = chat_service.safe_retrieve(query, top_k=3)
                print(f"\n查詢: {query}")
                print(f"檢索結果: {'✅ 成功' if context else '❌ 失敗'}")
                if context:
                    print(f"相關來源: {len(sources)} 個")
                    print(f"內容預覽: {context[:150]}...")
                else:
                    print("未找到相關內容")

            except Exception as e:
                print(f"查詢錯誤: {e}")

    except Exception as e:
        print(f"❌ 驗證失敗: {e}")

    print("\n=== 重建完成 ===")

if __name__ == "__main__":
    rebuild_django_kb()