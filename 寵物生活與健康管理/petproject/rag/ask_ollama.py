
# ask_ollama.py (fixed: use query_embeddings with BAAI/bge-small-zh-v1.5 → 512-d)
import argparse
from typing import List, Dict
import chromadb
import ollama
from sentence_transformers import SentenceTransformer  # NEW

SYS_PROMPT = (
    "你是『毛日好 Paw&Day』網站的 AI 客服助理，請一律使用『繁體中文』回覆。"
    "回答時要：1) 先理解使用者問題，2) 優先使用提供的知識片段回覆，3) 給出清楚、可執行的步驟。"
    "若知識片段中沒有相關內容，再根據一般常識補充，並在段末標示（一般建議）。"
    "回答結尾加上：『需要我引用原始 FAQ 條目給你看嗎？』"
)

# 以與資料庫相同的模型產生查詢向量（512 維）
_embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5")

def retrieve(persist_dir: str, collection: str, q: str, top_k: int = 4):
    client = chromadb.PersistentClient(path=persist_dir)
    coll = client.get_or_create_collection(collection)
    q_emb = _embedder.encode([q], normalize_embeddings=True).tolist()  # 512-d
    res = coll.query(query_embeddings=q_emb, n_results=top_k)  # 用 embeddings 查
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    return docs, metas

def build_prompt(question: str, docs: List[str], metas: List[Dict]) -> List[Dict]:
    context_blocks = []
    for d, m in zip(docs, metas):
        src = f"{m.get('source_file')}｜{m.get('sheet')}｜列{m.get('row_index')}"
        context_blocks.append(f"[來源：{src}]\n{d}")
    context_text = "\n\n---\n\n".join(context_blocks) if context_blocks else "（無檢索結果）"
    user_msg = (
        f"使用者問題：{question}\n\n"
        f"以下是與問題最相關的知識片段（可能包含問答）：\n"
        f"{context_text}\n\n"
        f"請根據以上內容，以條列步驟與注意事項回覆。"
    )
    return [
        {"role": "system", "content": SYS_PROMPT},
        {"role": "user", "content": user_msg},
    ]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", required=True, help="你的問題（繁中）")
    ap.add_argument("--persist_dir", default="chroma_db")
    ap.add_argument("--collection", default="faq_collection")
    ap.add_argument("--top_k", type=int, default=4)
    ap.add_argument("--model", default="qwen2.5:7b-instruct", help="Ollama 模型名稱")
    args = ap.parse_args()

    docs, metas = retrieve(args.persist_dir, args.collection, args.q, args.top_k)
    messages = build_prompt(args.q, docs, metas)

    resp = ollama.chat(model=args.model, messages=messages, options={"num_ctx": 4096})
    print(resp["message"]["content"])

    if metas:
        print("\n— 引用來源 —")
        for i, m in enumerate(metas, start=1):
            print(f"[{i}] {m.get('source_file')}｜{m.get('sheet')}｜列{m.get('row_index')}")

if __name__ == "__main__":
    main()
