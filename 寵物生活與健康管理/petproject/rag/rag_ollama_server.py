
# rag_ollama_server.py (Chroma v0.5+ PersistentClient)
from typing import List, Dict
from fastapi import FastAPI
from pydantic import BaseModel
import chromadb
import ollama

DEFAULT_MODEL = "qwen2.5:7b-instruct"
SYS_PROMPT = (
    "你是『毛日好 Paw&Day』網站的 AI 客服助理，請一律使用『繁體中文』回覆。"
    "回答時要：1) 先釐清與理解使用者問題，2) 優先引用提供的知識片段回覆，3) 用條列與步驟呈現。"
    "若知識片段不足，再以常識補充並標註（一般建議）。避免編造引用。"
)

app = FastAPI(title="Paw&Day RAG (Ollama + Chroma)", version="1.0.0")

class AskReq(BaseModel):
    q: str
    top_k: int = 4
    model: str = DEFAULT_MODEL
    persist_dir: str = "chroma_db"
    collection: str = "faq_collection"

class AskRes(BaseModel):
    answer: str
    sources: List[Dict]

def retrieve(persist_dir: str, collection: str, q: str, top_k: int = 4):
    client = chromadb.PersistentClient(path=persist_dir)
    coll = client.get_or_create_collection(collection)
    res = coll.query(query_texts=[q], n_results=top_k)
    return res.get("documents", [[]])[0], res.get("metadatas", [[]])[0]

def build_messages(q: str, docs: List[str], metas: List[Dict]) -> List[Dict]:
    context = []
    for d, m in zip(docs, metas):
        src = f"{m.get('source_file')}｜{m.get('sheet')}｜列{m.get('row_index')}"
        context.append(f"[來源：{src}]\n{d}")
    ctx = "\n\n---\n\n".join(context) if context else "（無檢索結果）"
    user_msg = (
        f"使用者問題：{q}\n\n"
        f"以下是與問題最相關的知識片段（可能包含問答）：\n"
        f"{ctx}\n\n"
        f"請根據以上內容，以清楚條列與可執行步驟回覆，並附上必要注意事項。"
    )
    return [
        {"role": "system", "content": SYS_PROMPT},
        {"role": "user", "content": user_msg},
    ]

@app.post("/ask", response_model=AskRes)
def ask(req: AskReq):
    docs, metas = retrieve(req.persist_dir, req.collection, req.q, req.top_k)
    messages = build_messages(req.q, docs, metas)
    resp = ollama.chat(model=req.model, messages=messages, options={"num_ctx": 4096})
    answer = resp["message"]["content"]
    return AskRes(
        answer=answer,
        sources=[
            {"source_file": m.get("source_file"), "sheet": m.get("sheet"), "row_index": m.get("row_index")}
            for m in metas
        ]
    )
