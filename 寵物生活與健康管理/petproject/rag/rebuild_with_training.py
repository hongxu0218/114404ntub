# -*- coding: utf-8 -*-
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
import os

def main():
    # 設定檔案路徑
    excel_file = "data/faq_data.xlsx"
    chroma_dir = "chroma_db"
    collection_name = "faq_with_training"  # 新的集合名稱

    print(f"載入模型：BAAI/bge-small-zh-v1.5")
    embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5")

    # 建立ChromaDB連接
    client = chromadb.PersistentClient(path=chroma_dir)

    # 嘗試刪除舊集合
    try:
        client.delete_collection(collection_name)
        print(f"刪除舊集合：{collection_name}")
    except Exception as e:
        print(f"集合不存在或無法刪除：{e}")

    # 建立新集合
    collection = client.create_collection(collection_name)

    # 訓練相關問答（先添加這些）
    training_qa = [
        {
            "question": "我要如何訓練我的狗？",
            "answer": "狗狗訓練需要耐心和一致性。基本步驟：1.建立固定的訓練時間和地點 2.使用正向強化（獎勵好行為）3.從簡單指令開始（坐下、待著、來這裡）4.保持訓練時間短而頻繁（5-10分鐘）5.每次訓練後給予獎勵和讚美。記住要保持耐心，每隻狗的學習速度不同。",
            "sheet": "寵物訓練"
        },
        {
            "question": "我要如何訓練我家的狗？",
            "answer": "訓練家中的狗狗需要建立明確的規則和一致的訓練方式。重點包括：1.制定家規（哪裡可以去、哪裡不能去）2.定時餵食和遛狗建立規律 3.使用正向獎勵制度 4.全家人保持一致的指令和態度 5.提供足夠的運動和刺激。耐心是關鍵，每天短時間多次練習效果最好。",
            "sheet": "寵物訓練"
        },
        {
            "question": "我要如何訓練我的貓？",
            "answer": "貓咪訓練與狗狗不同，需要更多耐心。方法：1.使用點心和讚美作為獎勵 2.訓練時間要短（3-5分鐘）3.選擇貓咪精神好的時候訓練 4.從簡單行為開始（坐下、握手）5.絕不使用懲罰，只用正向強化。貓咪較獨立，要尊重牠們的個性和意願。",
            "sheet": "寵物訓練"
        },
        {
            "question": "如何訓練狗狗定點上廁所？",
            "answer": "定點如廁訓練步驟：1.選定固定的廁所位置 2.建立規律的帶出時間（餐後、睡醒、遊戲後）3.當狗狗在正確位置如廁時立即獎勵 4.發現意外時不要責罵，清理乾淨即可 5.使用「去廁所」等口令建立聯結。通常需要2-4週的耐心訓練。",
            "sheet": "寵物訓練"
        },
        {
            "question": "如何訓練貓咪使用貓砂盆？",
            "answer": "貓砂盆訓練要點：1.選擇合適大小的砂盆（貓咪身長的1.5倍）2.放在安靜、容易到達的地方 3.保持砂盆清潔，每天清理 4.選擇貓咪喜歡的貓砂類型 5.多貓家庭要準備足夠數量的砂盆（貓咪數量+1）。大部分貓咪會自然使用砂盆。",
            "sheet": "寵物訓練"
        },
        {
            "question": "狗狗不聽話怎麼辦？",
            "answer": "改善狗狗不聽話的方法：1.檢查是否理解指令（重新教導基本指令）2.確保訓練的一致性（全家人使用相同指令）3.增加運動量（疲憊的狗較容易專注）4.使用高價值獎勵（特別喜歡的零食）5.尋求專業訓練師協助。記住要保持冷靜和耐心。",
            "sheet": "寵物訓練"
        },
        {
            "question": "貓咪亂抓家具怎麼辦？",
            "answer": "解決貓咪抓家具問題：1.提供足夠的抓板（不同材質和角度）2.在家具旁放置抓板 3.使用貓草或費洛蒙吸引貓咪使用抓板 4.定期修剪貓咪指甲 5.在家具上貼雙面膠或使用保護套。當貓咪使用抓板時要給予獎勵。",
            "sheet": "寵物訓練"
        },
        {
            "question": "如何訓練狗狗基本指令？",
            "answer": "基本指令訓練方法：\n坐下：手拿零食舉高，狗狗自然會坐下，立即說「坐下」並獎勵\n待著：從坐下開始，手掌向前說「待著」，逐漸增加時間\n來這裡：用開心語調呼喚，狗狗過來時立即獎勵\n趴下：從坐下姿勢，零食往下移動到地面\n每個指令重複練習，保持耐心和一致性。",
            "sheet": "寵物訓練"
        },
        {
            "question": "幼犬什麼時候開始訓練？",
            "answer": "幼犬訓練時機：1.8-12週是社會化關鍵期，可開始基本訓練 2.疫苗完成前在家進行基礎訓練 3.3-6個月是學習黃金期 4.從簡單指令和規矩開始 5.每天短時間多次訓練效果最好。越早開始訓練，狗狗越容易養成好習慣。",
            "sheet": "寵物訓練"
        }
    ]

    # 先處理訓練問答
    texts = []
    metadatas = []
    ids = []

    for i, qa in enumerate(training_qa):
        content = f"問題：{qa['question']}\n答案：{qa['answer']}"
        texts.append(content)
        metadatas.append({
            "source_file": "training_additions",
            "sheet": qa["sheet"],
            "row_index": i,
            "question": qa["question"],
            "answer": qa["answer"]
        })
        ids.append(f"training_{i}")

    # 讀取Excel檔案
    xl = pd.ExcelFile(excel_file)
    total_docs = len(training_qa)  # 已經有訓練問答了

    for sheet_name in xl.sheet_names:
        print(f"\n處理工作表：{sheet_name}")
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # 檢查欄位數量
        if len(df.columns) < 4:
            print(f"  跳過 {sheet_name} (欄位數量不足)")
            continue

        for idx, row in df.iterrows():
            try:
                question = str(row.iloc[1]).strip()  # 第2欄
                answer = str(row.iloc[3]).strip()    # 第4欄

                # 跳過空的問答
                if not question or not answer or question == 'nan' or answer == 'nan':
                    continue

                # 組合問題和答案
                content = f"問題：{question}\n答案：{answer}"

                texts.append(content)
                metadatas.append({
                    "source_file": "faq_data.xlsx",
                    "sheet": sheet_name,
                    "row_index": int(idx),
                    "question": question,
                    "answer": answer
                })
                ids.append(f"{sheet_name}_{idx}")

            except Exception as e:
                print(f"  處理第{idx}行時發生錯誤：{e}")
                continue

    # 一次性加入所有到ChromaDB
    if texts:
        print(f"\n正在嵌入 {len(texts)} 個文檔...")
        embeddings = embedder.encode(texts, convert_to_tensor=False, show_progress_bar=True)

        collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

        total_docs = len(texts)
        print(f"成功加入 {total_docs} 個文檔")

    print(f"\n✅ 完成！總共加入 {total_docs} 個文檔到集合：{collection_name}")
    print(f"資料庫路徑：{chroma_dir}")

    # 驗證資料
    count = collection.count()
    print(f"驗證：資料庫中有 {count} 個文檔")

    # 測試訓練相關查詢
    print("\n測試訓練問題查詢：")
    test_queries = ["我要如何訓練我的狗", "我要如何訓練我家的狗", "狗狗不聽話怎麼辦"]
    for query in test_queries:
        try:
            result = collection.query(query_texts=[query], n_results=1)
            if result and result.get('documents') and result['documents'][0]:
                print(f"✅ {query}: 找到答案")
            else:
                print(f"❌ {query}: 未找到答案")
        except Exception as e:
            print(f"❌ {query}: 查詢錯誤 - {e}")

if __name__ == "__main__":
    main()