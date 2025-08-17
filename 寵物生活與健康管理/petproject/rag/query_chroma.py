
# query_chroma.py (fixed: use query_embeddings with BAAI/bge-small-zh-v1.5 → 512-d)
import argparse
import chromadb
from sentence_transformers import SentenceTransformer  # NEW

_embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist_dir", default="chroma_db")
    ap.add_argument("--collection", default="faq_collection")
    ap.add_argument("--q", required=True, help="你的問題（中文）")
    ap.add_argument("--k", type=int, default=5, help="回傳幾筆")
    args = ap.parse_args()

    client = chromadb.PersistentClient(path=args.persist_dir)
    coll = client.get_or_create_collection(args.collection)

    q_emb = _embedder.encode([args.q], normalize_embeddings=True).tolist()  # 512-d
    res = coll.query(query_embeddings=q_emb, n_results=args.k)

    print(f"\n🔎 Query: {args.q}")
    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    mds = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0] if "distances" in res else [None]*len(ids)

    for i, (_id, doc, md, dist) in enumerate(zip(ids, docs, mds, dists), start=1):
        print("-"*80)
        print(f"[{i}] 距離/分數: {dist}")
        print(f"來源：{md.get('source_file')}｜工作表：{md.get('sheet')}｜列：{md.get('row_index')}")
        if "qa_question" in md:
            print(f"Q：{md.get('qa_question')}")
        if "qa_answer" in md:
            print(f"A：{md.get('qa_answer')}")
        print("—— 內容 ——")
        print(doc)

if __name__ == "__main__":
    main()
