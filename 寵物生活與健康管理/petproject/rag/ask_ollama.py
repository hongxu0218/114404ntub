# ask_ollama.py
# 更快的 RAG 版：
# - query_embeddings（512 維，與 BAAI/bge-small-zh-v1.5 一致）
# - 片段截斷 (--snippet_chars) 減少上下文字量
# - 快通道 (--fast_threshold) 命中夠高直接回 FAQ 答案（毫秒級）
# - 串流 (--stream) 邊生成邊輸出，體感超快
# - 可調整模型 (--model)、生成長度 (--num_predict)、上下文長度 (--num_ctx)
#
# 範例：
#   python ask_ollama.py --q "寵物走失了該怎麼辦？" --top_k 3 --model qwen2.5:3b-instruct --num_predict 256 --stream

import argparse
from typing import List, Dict
import chromadb
import ollama
from sentence_transformers import SentenceTransformer
import textwrap

SYS_PROMPT = (
    "你是『毛日好 Paw&Day』網站的 AI 客服助理，請一律使用『繁體中文』回覆。"
    "回答時要：1) 先理解使用者問題，2) 優先使用提供的知識片段回覆，3) 給出清楚、可執行的步驟。"
    "若知識片段中沒有相關內容，再根據一般常識補充，並在段末標示（一般建議）。"
    "回答結尾加上：『需要我引用原始 FAQ 條目給你看嗎？』"
)

# 與索引相同的嵌入模型（512 維）
_embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5")

def retrieve(persist_dir: str, collection: str, q: str, top_k: int = 4):
    client = chromadb.PersistentClient(path=persist_dir)
    coll = client.get_or_create_collection(collection)
    q_emb = _embedder.encode([q], normalize_embeddings=True).tolist()  # 512-d
    res = coll.query(query_embeddings=q_emb, n_results=top_k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0] if "distances" in res else [None]*len(docs)
    return docs, metas, dists

def build_prompt(question: str, docs: List[str], metas: List[Dict], *, snippet_chars: int) -> List[Dict]:
    context_blocks = []
    for d, m in zip(docs, metas):
        src = f"{m.get('source_file')}｜{m.get('sheet')}｜列{m.get('row_index')}"
        snippet = d if snippet_chars <= 0 else d[:snippet_chars]
        context_blocks.append(f"[來源：{src}]\n{snippet}")
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

def maybe_fast_path(metas: List[Dict], dists: List[float], fast_threshold: float | None) -> str | None:
    """相似度超高時，直接回資料庫答案（可選）。"""
    if fast_threshold is None or not metas or not dists or dists[0] is None:
        return None
    if dists[0] <= fast_threshold:
        ans = (metas[0].get("qa_answer") or "").strip()
        q = metas[0].get("qa_question") or ""
        src = f"{metas[0].get('source_file')}｜{metas[0].get('sheet')}｜列{metas[0].get('row_index')}"
        if ans:
            return textwrap.dedent(f"""\
            （直接引用 FAQ，高相似度命中）
            問題：{q}
            答案：{ans}

            來源：{src}
            """).strip()
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", required=True, help="你的問題（繁中）")
    ap.add_argument("--persist_dir", default="chroma_db")
    ap.add_argument("--collection", default="faq_collection")
    ap.add_argument("--top_k", type=int, default=4)
    # ↓ 改用較快的 3B，仍可自訂
    ap.add_argument("--model", default="qwen2.5:3b-instruct", help="Ollama 模型名稱")
    # 生成/上下文長度，可依需要再縮短加速
    ap.add_argument("--num_ctx", type=int, default=2048)
    ap.add_argument("--num_predict", type=int, default=256)
    # 截斷每段上下文（只影響丟給模型的字數，不改輸出格式）
    ap.add_argument("--snippet_chars", type=int, default=320)
    # 快通道門檻（不給就不啟用）
    ap.add_argument("--fast_threshold", type=float, default=None)
    # 串流輸出（不加就維持一次性輸出與原本格式）
    ap.add_argument("--stream", action="store_true")
    args = ap.parse_args()

    docs, metas, dists = retrieve(args.persist_dir, args.collection, args.q, args.top_k)

    # 快通道：若相似度夠高，直接回 FAQ（極快）
    fast = maybe_fast_path(metas, dists, args.fast_threshold)
    if fast:
        print(fast)
        if metas:
            print("\n— 引用來源 —")
            for i, (m, d) in enumerate(zip(metas, dists), start=1):
                print(f"[{i}] {m.get('source_file')}｜{m.get('sheet')}｜列{m.get('row_index')}")
        return

    messages = build_prompt(args.q, docs, metas, snippet_chars=args.snippet_chars)
    options = {"num_ctx": args.num_ctx, "num_predict": args.num_predict}

    if args.stream:
        # 串流輸出（內容一樣，只是邊生成邊顯示）
        full = []
        for part in ollama.chat(model=args.model, messages=messages, options=options, stream=True):
            chunk = part["message"]["content"]
            full.append(chunk)
            print(chunk, end="", flush=True)
        print()
    else:
        # 維持原本的「一次性輸出」格式
        resp = ollama.chat(model=args.model, messages=messages, options=options)
        print(resp["message"]["content"])

    if metas:
        print("\n— 引用來源 —")
        for i, m in enumerate(metas, start=1):
            print(f"[{i}] {m.get('source_file')}｜{m.get('sheet')}｜列{m.get('row_index')}")

if __name__ == "__main__":
    main()