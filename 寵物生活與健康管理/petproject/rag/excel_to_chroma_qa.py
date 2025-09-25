
# excel_to_chroma_qa.py (Chroma v0.5+ PersistentClient)
import argparse
import os
import glob
import uuid
from typing import Iterable, Dict
import pandas as pd

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

def iter_excel_files(input_path: str) -> Iterable[str]:
    if os.path.isdir(input_path):
        for ext in ("*.xlsx", "*.xls", "*.xlsm"):
            for p in glob.glob(os.path.join(input_path, ext)):
                yield p
    else:
        yield input_path

def load_sheets(file_path: str) -> Dict[str, pd.DataFrame]:
    try:
        return pd.read_excel(file_path, sheet_name=None, dtype=str)
    except Exception:
        return pd.read_excel(file_path, sheet_name=None, dtype=str)

def main():
    ap = argparse.ArgumentParser(description="把 FAQ 類型 Excel（Question/Answer）轉為 Chroma 向量庫")
    ap.add_argument("--input", required=True, help="Excel 檔或資料夾")
    ap.add_argument("--persist_dir", default="chroma_db", help="Chroma 資料夾（會自動建立）")
    ap.add_argument("--collection", default="faq_collection", help="集合名稱")
    ap.add_argument("--model_name", default="BAAI/bge-small-zh-v1.5",
                    help="句向量模型（可填本機目錄路徑以離線使用）")
    ap.add_argument("--batch_size", type=int, default=128)
    ap.add_argument("--q_col", default="Question")
    ap.add_argument("--a_col", default="Answer")
    args = ap.parse_args()

    print(f"[Info] 載入模型：{args.model_name}")
    embedder = SentenceTransformer(args.model_name)

    # ✅ New Chroma API
    client = chromadb.PersistentClient(path=args.persist_dir)
    coll = client.get_or_create_collection(args.collection)

    total_docs = 0
    for file in iter_excel_files(args.input):
        sheets = load_sheets(file)
        print(f"\n[File] {file} -> {len(sheets)} 個工作表")
        for sheet_name, df in sheets.items():
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            if args.q_col not in df.columns or args.a_col not in df.columns:
                print(f"  - 跳過 {sheet_name}（找不到欄位 {args.q_col}/{args.a_col}）")
                continue

            texts, metadatas = [], []
            for idx, row in df.iterrows():
                q = str(row.get(args.q_col, "") or "").strip()
                a = str(row.get(args.a_col, "") or "").strip()
                if not (q or a):
                    continue
                content = f"問題：{q}\n答案：{a}"
                texts.append(content)
                metadatas.append({
                    "source_file": os.path.basename(file),
                    "sheet": sheet_name,
                    "row_index": int(idx),
                    "qa_question": q,
                    "qa_answer": a
                })

            if not texts:
                continue

            ids = [str(uuid.uuid4()) for _ in texts]

            embeddings = []
            for i in tqdm(range(0, len(texts), args.batch_size), desc=f"Embedding [{sheet_name}]"):
                batch = texts[i:i+args.batch_size]
                emb = embedder.encode(batch, normalize_embeddings=True).tolist()
                embeddings.extend(emb)

            coll.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
            print(f"  - {sheet_name} 加入 {len(texts)} 筆")
            total_docs += len(texts)

    print(f"\n✅ 完成，總計加入 {total_docs} 筆到集合：{args.collection}")
    print(f"📁 資料庫目錄：{os.path.abspath(args.persist_dir)}")

if __name__ == "__main__":
    main()
