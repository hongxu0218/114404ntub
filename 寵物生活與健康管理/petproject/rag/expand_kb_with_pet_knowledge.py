#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import django
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

from petapp import chat_service
import chromadb
from chromadb.config import Settings

# 寵物專業知識庫
PET_KNOWLEDGE = [
    {
        "question": "狗狗適合的運動量是多少？",
        "answer": "狗狗的運動量依品種、年齡、健康狀況而定：\n1. 小型犬：每天30-60分鐘輕度運動\n2. 中型犬：每天60-90分鐘中等強度運動\n3. 大型犬：每天90-120分鐘運動\n4. 幼犬：短時間多次，避免過度運動\n5. 老犬：溫和運動，視身體狀況調整\n運動類型包括散步、玩球、游泳等。"
    },
    {
        "question": "貓咪適合的運動量是多少？",
        "answer": "貓咪每天需要10-15分鐘的活躍運動：\n1. 幼貓：短時間高頻率玩耍\n2. 成貓：每天2-3次，每次5-10分鐘\n3. 老貓：溫和的互動遊戲\n4. 室內貓：需要更多人工刺激運動\n使用逗貓棒、雷射筆、玩具老鼠等工具。"
    },
    {
        "question": "如何與狗狗建立良好關係？",
        "answer": "與狗狗建立關係的方法：\n1. 建立日常作息，讓狗狗有安全感\n2. 使用正向訓練，獎勵好行為\n3. 每天固定互動時間，如散步、遊戲\n4. 保持耐心，理解狗狗的身體語言\n5. 提供適當的社交機會\n6. 定期健康檢查，關注狗狗福利\n7. 避免體罰，建立信任關係"
    },
    {
        "question": "如何與貓咪建立良好關係？",
        "answer": "與貓咪相處的技巧：\n1. 尊重貓咪的獨立性，不強迫互動\n2. 讓貓咪主動接近你\n3. 輕聲說話，避免突然動作\n4. 提供舒適的休息空間\n5. 定時餵食，建立信任\n6. 透過遊戲增進感情\n7. 學習讀懂貓咪的肢體語言\n8. 保持環境清潔，特別是貓砂盆"
    },
    {
        "question": "寵物疫苗接種時程如何安排？",
        "answer": "寵物疫苗接種時程：\n狗狗：\n1. 6-8週：第一劑核心疫苗\n2. 10-12週：第二劑核心疫苗\n3. 14-16週：第三劑核心疫苗\n4. 成年後每年補強\n\n貓咪：\n1. 6-8週：第一劑核心疫苗\n2. 10-12週：第二劑核心疫苗\n3. 14-16週：第三劑核心疫苗\n4. 成年後每年補強\n\n請諮詢獸醫師制定個人化疫苗計劃。"
    },
    {
        "question": "寵物飲食注意事項有哪些？",
        "answer": "寵物飲食要點：\n1. 選擇適合年齡的優質飼料\n2. 定時定量餵食，避免暴飲暴食\n3. 提供新鮮乾淨的飲水\n4. 避免人類食物：巧克力、洋蔥、葡萄等\n5. 控制零食份量，不超過每日熱量10%\n6. 幼齡寵物需要更頻繁餵食\n7. 老齡寵物可能需要特殊飲食\n8. 有健康問題請諮詢獸醫師"
    },
    {
        "question": "寵物訓練的基本原則是什麼？",
        "answer": "寵物訓練基本原則：\n1. 正向強化：獎勵好行為而非懲罰壞行為\n2. 一致性：所有家人使用相同指令和規則\n3. 耐心：重複練習，不急於求成\n4. 及時反應：行為發生當下立即回應\n5. 短時間訓練：每次10-15分鐘避免疲勞\n6. 循序漸進：從簡單指令開始\n7. 社會化：讓寵物適應不同環境和人\n8. 尋求專業協助：遇到困難可諮詢訓練師"
    },
    {
        "question": "寵物常見疾病預防方法？",
        "answer": "寵物疾病預防：\n1. 定期健康檢查：每年至少一次\n2. 按時接種疫苗和驅蟲\n3. 保持口腔衛生，定期刷牙\n4. 控制體重，避免肥胖\n5. 提供適當運動\n6. 注意環境清潔\n7. 觀察行為變化，早期發現問題\n8. 避免接觸有毒物質\n9. 提供均衡營養\n10. 老齡寵物需要更頻繁檢查"
    }
]

def expand_knowledge_base():
    print("正在擴充寵物專業知識庫...")

    # 讀取現有Excel資料
    df_existing = pd.read_excel('data/platform_manual.xlsx')
    print(f"現有平台FAQ: {len(df_existing)}個")

    # 初始化ChromaDB
    client = chromadb.PersistentClient(
        path=chat_service.DB_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    # 獲取現有集合
    collection = client.get_collection(chat_service.COLLECTION_NAME)
    current_count = collection.count()
    print(f"當前知識庫文檔數: {current_count}")

    # 準備新的寵物知識文檔
    new_documents = []
    new_metadatas = []
    new_ids = []

    start_idx = current_count + 1
    for idx, knowledge in enumerate(PET_KNOWLEDGE):
        combined_text = f"Q: {knowledge['question']}\nA: {knowledge['answer']}"
        new_documents.append(combined_text)
        new_metadatas.append({
            'question': knowledge['question'],
            'answer': knowledge['answer'],
            'source': 'pet_knowledge',
            'id': f"pet_kb_{idx+1}"
        })
        new_ids.append(f"pet_kb_{idx+1}")

    print(f"準備加入 {len(new_documents)} 個寵物知識文檔")

    # 生成嵌入向量並加入集合
    embeddings = chat_service._embedder.encode(new_documents, normalize_embeddings=True).tolist()
    print(f"生成 {len(embeddings)} 個嵌入向量")

    collection.add(
        embeddings=embeddings,
        documents=new_documents,
        metadatas=new_metadatas,
        ids=new_ids
    )

    final_count = collection.count()
    print(f"擴充完成！知識庫現有 {final_count} 個文檔 (新增 {final_count - current_count} 個)")

    # 測試新知識
    test_queries = ["狗狗適合的運動量？", "我要如何跟我家狗好相處？", "貓咪運動"]
    print("\n測試新知識檢索：")
    for query in test_queries:
        try:
            context, sources = chat_service.safe_retrieve(query, top_k=2)
            print(f"\n查詢: {query}")
            print(f"找到內容: {'是' if context else '否'}")
            if context:
                print(f"內容預覽: {context[:100]}...")
        except Exception as e:
            print(f"  錯誤: {e}")

if __name__ == "__main__":
    expand_knowledge_base()