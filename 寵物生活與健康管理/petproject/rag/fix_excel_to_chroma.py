# -*- coding: utf-8 -*-
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
import os

def main():
    # 設定檔案路徑
    excel_file = "data/faq_data.xlsx"
    chroma_dir = "chroma_db"
    collection_name = "faq_new"

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

    # 讀取Excel檔案
    xl = pd.ExcelFile(excel_file)
    total_docs = 0

    for sheet_name in xl.sheet_names:
        print(f"\n處理工作表：{sheet_name}")
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # 檢查欄位數量
        if len(df.columns) < 4:
            print(f"  跳過 {sheet_name} (欄位數量不足)")
            continue

        # 使用第2和第4欄(index 1和3)作為問題和答案
        question_col = df.columns[1]  # 第2欄
        answer_col = df.columns[3]    # 第4欄

        texts = []
        metadatas = []
        ids = []

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

        # 加入到ChromaDB
        if texts:
            print(f"  正在嵌入 {len(texts)} 個文檔...")
            embeddings = embedder.encode(texts, convert_to_tensor=False, show_progress_bar=True)

            collection.add(
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )

            total_docs += len(texts)
            print(f"  成功加入 {len(texts)} 個文檔")
        else:
            print(f"  {sheet_name} 沒有有效的問答資料")

    print(f"\n✅ 完成！總共加入 {total_docs} 個文檔到集合：{collection_name}")
    print(f"資料庫路徑：{chroma_dir}")

    # 驗證資料
    count = collection.count()
    print(f"驗證：資料庫中有 {count} 個文檔")

if __name__ == "__main__":
    main()