#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import django

# 設定Django環境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

# 現在可以導入Django的chat_service
from petapp import chat_service

def test_django_kb():
    print("=== 測試Django AI客服知識庫 ===\n")

    # 測試嵌入模型
    print(f"嵌入模型狀態: {chat_service._embedder is not None}")
    if chat_service._embedder:
        print(f"嵌入模型: {chat_service._embedder}")

    # 測試ChromaDB連接
    try:
        client, collection = chat_service._get_cached_client()
        print(f"ChromaDB客戶端: {client is not None}")
        print(f"集合: {collection is not None}")

        if collection:
            count = collection.count()
            print(f"集合文檔數量: {count}")

            # 測試檢索
            print("\n測試檢索:")
            queries = ["忘記密碼怎麼辦？", "註冊", "password"]
            for query in queries:
                print(f"\n查詢: {query}")
                try:
                    context, sources = chat_service.safe_retrieve(query, top_k=3)
                    print(f"檢索到內容: {len(context) > 0}")
                    print(f"來源數量: {len(sources)}")
                    if context:
                        print(f"內容預覽: {context[:200]}...")
                    else:
                        print("❌ 沒有檢索到相關內容")
                except Exception as e:
                    print(f"檢索錯誤: {e}")

    except Exception as e:
        print(f"ChromaDB錯誤: {e}")

if __name__ == "__main__":
    test_django_kb()