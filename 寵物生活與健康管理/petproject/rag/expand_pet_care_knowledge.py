#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

from petapp import chat_service
import chromadb
from chromadb.config import Settings

# 更多寵物護理專業知識，特別針對智能問題推薦
PET_CARE_KNOWLEDGE = [
    {
        "question": "如何護理寵物毛髮？",
        "answer": "寵物毛髮護理的基本方法：\n1. 定期梳毛：短毛寵物每週2-3次，長毛寵物每天梳理\n2. 選擇合適工具：針梳適合長毛，鋼梳適合短毛\n3. 洗澡頻率：狗狗每月1-2次，貓咪較少需要洗澡\n4. 使用寵物專用洗毛精，避免人用產品\n5. 吹乾毛髮：徹底吹乾避免皮膚問題\n6. 注意打結：長毛品種要特別注意防止打結\n7. 季節換毛期加強梳理，減少掉毛\n8. 發現皮膚異常立即諮詢獸醫"
    },
    {
        "question": "寵物指甲怎麼剪？",
        "answer": "寵物指甲修剪方法：\n1. 準備專用指甲剪，不要用人用指甲剪\n2. 選擇寵物放鬆的時候進行\n3. 輕握寵物爪子，輕壓露出指甲\n4. 剪指甲白色部分，避免剪到粉紅色血管\n5. 一次剪一點，寧可多剪幾次\n6. 狗狗約2-4週剪一次，貓咪2-3週\n7. 如意外剪到血管，用止血粉止血\n8. 剪後給予獎勵，建立正面聯想\n9. 初學者可請獸醫師示範"
    },
    {
        "question": "寵物耳朵如何清潔？",
        "answer": "寵物耳朵清潔步驟：\n1. 使用寵物專用耳朵清潔劑\n2. 將清潔劑滴入耳道，輕柔按摩耳根\n3. 讓寵物自然甩頭，甩出髒污\n4. 用棉球或紗布清潔外耳道\n5. 不要用棉花棒深入耳道\n6. 長耳朵品種需要更頻繁清潔\n7. 正常頻率：每週1-2次\n8. 發現異味、發紅、分泌物異常要就醫\n9. 游泳後要特別注意清潔乾燥"
    },
    {
        "question": "寵物牙齒如何護理？",
        "answer": "寵物口腔護理方法：\n1. 使用寵物專用牙刷和牙膏\n2. 從小開始訓練刷牙習慣\n3. 初期用手指套或紗布清潔\n4. 每天刷牙最理想，至少每週2-3次\n5. 提供潔牙骨或潔牙玩具\n6. 定期獸醫洗牙（全身麻醉）\n7. 觀察口臭、牙垢、牙齦紅腫\n8. 老年寵物更需要注意口腔健康\n9. 飲食中添加潔牙成分的飼料"
    },
    {
        "question": "寵物眼睛如何護理？",
        "answer": "寵物眼部護理要點：\n1. 每天用濕紙巾或乾淨布料清潔眼周\n2. 清除眼屎和淚痕，由內往外擦拭\n3. 使用生理食鹽水清潔，避免自來水\n4. 注意觀察眼睛分泌物顏色和量\n5. 扁臉品種容易有淚痕問題\n6. 避免毛髮刺激眼睛，定期修剪\n7. 發現眼睛紅腫、分泌物異常要就醫\n8. 不要自行使用人用眼藥水\n9. 白內障、青光眼等老年疾病要留意"
    },
    {
        "question": "寵物皮膚病如何預防？",
        "answer": "寵物皮膚病預防方法：\n1. 保持環境清潔乾燥\n2. 定期驅蟲，預防跳蚤、壁蝨\n3. 適度洗澡，過度清潔會破壞皮膚屏障\n4. 使用溫和的寵物專用清潔產品\n5. 保持毛髮乾燥，避免潮濕環境\n6. 營養均衡，Omega-3有助皮膚健康\n7. 避免接觸過敏原\n8. 定期檢查皮膚狀況\n9. 早期發現異常立即就醫\n10. 免疫力低下的寵物要特別注意"
    },
    {
        "question": "寵物洗澡頻率和方法？",
        "answer": "寵物洗澡的正確方法：\n1. 洗澡頻率：狗狗每月1-2次，貓咪很少需要\n2. 水溫控制在38-40°C，測試手背溫度\n3. 準備防滑墊，避免寵物滑倒\n4. 先濕潤毛髮，再塗抹洗毛精\n5. 避免水和洗劑進入眼睛、耳朵\n6. 徹底沖洗，殘留洗劑會刺激皮膚\n7. 用毛巾擦乾後，用吹風機完全吹乾\n8. 室外活動較多可增加洗澡頻率\n9. 皮膚病期間遵循獸醫指示"
    },
    {
        "question": "寵物換毛期如何護理？",
        "answer": "換毛期護理要點：\n1. 春秋兩季是主要換毛期\n2. 增加梳毛頻率，每天至少一次\n3. 使用除毛梳或專業工具\n4. 補充營養，特別是蛋白質和維生素\n5. 保持環境濕度適中\n6. 勤清理掉落的毛髮\n7. 注意觀察是否有異常大量掉毛\n8. 老年寵物換毛期可能延長\n9. 某些品種四季都會掉毛\n10. 過度掉毛可能是健康問題警訊"
    },
    {
        "question": "寵物肥胖如何預防和改善？",
        "answer": "寵物體重管理方法：\n1. 定期測量體重，建立記錄\n2. 控制食物份量，按年齡和活動量調整\n3. 選擇低卡路里、高纖維的減重飼料\n4. 減少零食和人食，零食不超過總熱量10%\n5. 增加運動量，循序漸進\n6. 多次少量餵食，避免暴飲暴食\n7. 絕育後特別注意體重控制\n8. 老年寵物新陳代謝較慢\n9. 體重過重會引發關節、心血管問題\n10. 制定減重計畫建議諮詢獸醫師"
    },
    {
        "question": "如何判斷寵物是否健康？",
        "answer": "健康寵物的指標：\n1. 精神狀態：活潑好動，對環境有反應\n2. 食慾正常：按時進食，食量穩定\n3. 排泄正常：大小便規律，質地正常\n4. 體溫：狗貓正常體溫38-39°C\n5. 呼吸：平穩規律，無異常喘息\n6. 眼睛：明亮清澈，無異常分泌物\n7. 鼻頭：濕潤微涼（睡覺時可能乾燥）\n8. 毛髮：有光澤，無過度掉毛\n9. 體重：維持理想體重\n10. 異常警訊：嗜睡、食慾不振、嘔吐、腹瀉等"
    }
]

def expand_pet_care_knowledge():
    print("正在添加寵物護理專業知識...")

    # 獲取現有ChromaDB集合
    client = chromadb.PersistentClient(
        path=chat_service.DB_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    collection = client.get_collection(chat_service.COLLECTION_NAME)
    current_count = collection.count()
    print(f"當前知識庫文檔數: {current_count}")

    # 準備新的寵物護理知識文檔
    new_documents = []
    new_metadatas = []
    new_ids = []

    for idx, knowledge in enumerate(PET_CARE_KNOWLEDGE):
        combined_text = f"Q: {knowledge['question']}\nA: {knowledge['answer']}"
        new_documents.append(combined_text)
        new_metadatas.append({
            'question': knowledge['question'],
            'answer': knowledge['answer'],
            'source': 'pet_care_knowledge',
            'id': f"pet_care_{idx+1}"
        })
        new_ids.append(f"pet_care_{idx+1}")

    print(f"準備加入 {len(new_documents)} 個寵物護理知識文檔")

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

    # 清除快取以使用新知識
    chat_service.clear_cache()
    print("已清除快取")

    # 測試新知識
    test_queries = [
        "如何護理寵物毛髮？",
        "寵物指甲怎麼剪？",
        "寵物耳朵清潔",
        "寵物牙齒護理",
        "寵物皮膚病預防",
        "寵物肥胖問題"
    ]

    print("\n測試新知識檢索：")
    for query in test_queries:
        try:
            context, sources = chat_service.safe_retrieve(query, top_k=2)
            print(f"\n查詢: {query}")
            print(f"找到內容: {'是' if context else '否'}")
            if context:
                print(f"相關來源: {len(sources)} 個")
                print(f"內容預覽: {context[:80]}...")
        except Exception as e:
            print(f"  錯誤: {e}")

if __name__ == "__main__":
    expand_pet_care_knowledge()