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

# 進階寵物護理專業知識
ADVANCED_PET_KNOWLEDGE = [
    {
        "question": "寵物環境豐富化如何設計？",
        "answer": "寵物環境豐富化設計原則：\n1. 垂直空間利用：貓樹、攀爬架提供立體活動\n2. 藏匿空間：提供安全感的隱蔽處\n3. 互動玩具：益智玩具刺激大腦活動\n4. 感官刺激：不同材質、氣味、聲音\n5. 觀察窗：讓寵物觀察外界環境\n6. 輪換玩具：定期更換保持新鮮感\n7. 多功能區域：進食、休息、遊戲分區\n8. 自然元素：植物（確保安全）、陽光\n9. 社交機會：多寵物互動或人寵互動"
    },
    {
        "question": "如何建立寵物日常作息？",
        "answer": "寵物日常作息建立方法：\n1. 固定餵食時間：建立生理時鐘\n2. 規律運動時段：每天相同時間運動\n3. 睡眠環境：安靜舒適的休息空間\n4. 梳理時間：固定護理時段\n5. 訓練時間：短時間高效率訓練\n6. 社交時間：與家人互動的固定時段\n7. 獨處時間：培養獨立性\n8. 戶外活動：天氣許可的戶外時間\n9. 漸進調整：慢慢建立新習慣\n10. 一致性：全家人配合執行"
    },
    {
        "question": "寵物急救基本知識有哪些？",
        "answer": "寵物急救基本知識：\n1. 緊急聯絡：準備24小時獸醫院資訊\n2. 基本生命徵象：體溫、心跳、呼吸檢查\n3. 外傷處理：止血、包紮基本技巧\n4. 中毒處理：立即移除毒源，聯絡獸醫\n5. 異物梗塞：海姆利希法急救\n6. 中暑處理：降溫、補水、通風\n7. 失溫處理：保暖、避免劇烈升溫\n8. 癲癇處理：保護頭部，記錄發作時間\n9. 急救用品：消毒劑、紗布、體溫計\n10. 運送方法：安全固定運送受傷寵物"
    },
    {
        "question": "寵物老化照護要點是什麼？",
        "answer": "寵物老化照護重點：\n1. 定期健康檢查：每6個月一次完整檢查\n2. 飲食調整：老年專用飼料，易消化食物\n3. 運動適度：溫和運動維持肌肉量\n4. 關節保健：補充軟骨素、控制體重\n5. 認知功能：保持心智活動，避免退化\n6. 環境改善：防滑地墊、軟墊床鋪\n7. 慢性病管理：定期服藥、監測指數\n8. 牙齒護理：更頻繁的口腔檢查\n9. 皮膚護理：注意皮膚彈性和毛質\n10. 陪伴關愛：更多溫柔的陪伴時光"
    },
    {
        "question": "新手養寵物需要準備什麼？",
        "answer": "新手養寵物準備清單：\n1. 基本用品：食碗、水碗、床鋪、玩具\n2. 清潔用品：寵物洗毛精、毛巾、梳子\n3. 安全設備：項圈、牽繩、外出籠\n4. 健康用品：體溫計、指甲剪、耳朵清潔劑\n5. 飼料選擇：年齡適合的優質飼料\n6. 獸醫聯絡：找到可信賴的獸醫師\n7. 寵物保險：考慮醫療保險計劃\n8. 居家安全：收納有毒物品、插座保護\n9. 訓練準備：學習基本訓練方法\n10. 心理準備：長期照護的責任與愛心"
    },
    {
        "question": "寵物分離焦慮如何處理？",
        "answer": "寵物分離焦慮處理方法：\n1. 漸進訓練：從短時間分離開始\n2. 建立正面聯想：離開時給予特殊玩具\n3. 忽略離別儀式：平靜地離開和回家\n4. 環境豐富化：提供足夠的刺激活動\n5. 運動消耗：出門前充分運動\n6. 安全空間：建立舒適的獨處環境\n7. 放鬆音樂：播放舒緩的背景音樂\n8. 費洛蒙產品：使用合成費洛蒙鎮定\n9. 行為訓練：教導「等待」和「放鬆」指令\n10. 嚴重案例：諮詢行為訓練師或獸醫"
    },
    {
        "question": "多寵物家庭如何管理？",
        "answer": "多寵物家庭管理要點：\n1. 逐步引入：新寵物循序漸進介紹\n2. 資源分配：各自的食碗、床鋪、玩具\n3. 空間規劃：提供足夠的個人空間\n4. 階層管理：尊重寵物間的自然階層\n5. 公平對待：避免偏心造成衝突\n6. 分別訓練：個別進行訓練課程\n7. 健康管理：定期檢查避免疾病傳播\n8. 安全監督：監控互動避免打架\n9. 個性配對：考慮寵物個性相容性\n10. 專業協助：必要時尋求行為專家幫助"
    },
    {
        "question": "寵物旅行注意事項有哪些？",
        "answer": "寵物旅行準備事項：\n1. 健康證明：疫苗證明、健康檢查證書\n2. 運輸籠選擇：適當大小、通風良好\n3. 食物準備：攜帶平常食用的飼料\n4. 水源供應：充足的飲用水\n5. 藥品準備：常用藥物、急救用品\n6. 熟悉物品：帶著平常用的毯子或玩具\n7. 休息安排：長途旅行安排休息停靠\n8. 溫度控制：避免過熱或過冷環境\n9. 目的地資訊：當地獸醫院聯絡方式\n10. 寵物旅館：提前預訂寵物友善住宿"
    },
    {
        "question": "寵物行為異常如何判斷？",
        "answer": "寵物行為異常判斷指標：\n1. 食慾變化：突然拒食或暴食\n2. 活動改變：異常活躍或嗜睡\n3. 排泄異常：頻率、顏色、質地改變\n4. 社交變化：躲避或過度黏人\n5. 聲音異常：過度吠叫、呻吟、沉默\n6. 重複行為：強迫性舔拭、轉圈\n7. 攻擊行為：對人或其他動物攻擊\n8. 破壞行為：撕咬家具、挖掘\n9. 姿態異常：弓背、跛行、頭部傾斜\n10. 警訊：持續超過24小時應就醫檢查"
    },
    {
        "question": "寵物季節性照護重點？",
        "answer": "寵物四季照護要點：\n春季：\n1. 換毛期加強梳理\n2. 預防花粉過敏\n3. 驅蟲預防跳蚤\n4. 疫苗補強時機\n\n夏季：\n5. 防中暑措施\n6. 增加飲水量\n7. 避免熱燙地面\n8. 防曬保護皮膚\n\n秋季：\n9. 準備換季毛髮\n10. 關節保暖\n11. 免疫力提升\n12. 食慾調整\n\n冬季：\n13. 保暖設備\n14. 室內空氣品質\n15. 皮膚乾燥預防\n16. 運動量調整"
    }
]

def expand_advanced_pet_knowledge():
    print("正在添加進階寵物護理專業知識...")

    # 獲取現有ChromaDB集合
    client = chromadb.PersistentClient(
        path=chat_service.DB_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    collection = client.get_collection(chat_service.COLLECTION_NAME)
    current_count = collection.count()
    print(f"當前知識庫文檔數: {current_count}")

    # 準備新的進階寵物知識文檔
    new_documents = []
    new_metadatas = []
    new_ids = []

    for idx, knowledge in enumerate(ADVANCED_PET_KNOWLEDGE):
        combined_text = f"Q: {knowledge['question']}\nA: {knowledge['answer']}"
        new_documents.append(combined_text)
        new_metadatas.append({
            'question': knowledge['question'],
            'answer': knowledge['answer'],
            'source': 'advanced_pet_care',
            'id': f"advanced_pet_{idx+1}"
        })
        new_ids.append(f"advanced_pet_{idx+1}")

    print(f"準備加入 {len(new_documents)} 個進階寵物護理知識文檔")

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
        "寵物環境豐富化",
        "寵物日常作息",
        "寵物急救知識",
        "寵物老化照護",
        "新手養寵物準備",
        "寵物分離焦慮",
        "多寵物管理",
        "寵物旅行注意事項",
        "寵物行為異常",
        "寵物季節照護"
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
    expand_advanced_pet_knowledge()