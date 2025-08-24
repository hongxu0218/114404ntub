# rag_ollama_server.py (stable)
from typing import List, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
import ollama

# 建議先用 3B，體感快且較不會超時；要再提升再切 7B
DEFAULT_MODEL = "qwen2.5:3b-instruct"

SYS_PROMPT = (
    "你是『毛日好 Paw&Day』網站的 AI 客服助理，請一律使用『繁體中文』回覆。"
    "回答時要：1) 先釐清與理解使用者問題，2) 優先引用提供的知識片段回覆，3) 用條列與步驟呈現。"
    "若知識片段不足，再以常識補充並標註（一般建議）。避免編造引用。"
)

app = FastAPI(title="Paw&Day RAG (Ollama + Chroma)", version="1.1.0")

# 開發先開放 *；上線請改成你的網域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskReq(BaseModel):
    q: str
    top_k: int = 4
    model: str = DEFAULT_MODEL
    persist_dir: str = "chroma_db"
    collection: str = "faq"  # ✅ 和你實際匯入一致

class AskRes(BaseModel):
    answer: str
    sources: List[Dict]

@app.get("/health")
def health():
    """基本健康檢查（不觸發 Ollama）"""
    return {"ok": True, "service": "Paw&Day RAG"}

@app.get("/ollama")
def ollama_health():
    """檢查 Ollama 是否可用，以及是否已拉下模型"""
    try:
        models = ollama.list().get("models", [])
        names = [m.get("name") for m in models]
        return {"ok": True, "models": names}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def retrieve(persist_dir: str, collection: str, q: str, top_k: int = 4):
    client = chromadb.PersistentClient(path=persist_dir)
    coll = client.get_or_create_collection(collection)
    res = coll.query(query_texts=[q], n_results=top_k)
    return res.get("documents", [[]])[0], res.get("metadatas", [[]])[0]

def build_messages(q: str, docs: List[str], metas: List[Dict]) -> List[Dict]:
    # 避免把太長的片段丟進模型，降低超時風險
    def trunc(t: str, lim=800):
        t = t or ""
        return t if len(t) <= lim else t[:lim] + "…"

    context = []
    for d, m in zip(docs, metas):
        src = f"{m.get('source_file')}｜{m.get('sheet')}｜列{m.get('row_index')}"
        context.append(f"[來源：{src}]\n{trunc(d)}")

    ctx = "\n\n---\n\n".join(context) if context else "（無檢索結果）"
    user_msg = (
        f"使用者問題：{q}\n\n"
        f"以下是與問題最相關的知識片段（可能包含問答）：\n{ctx}\n\n"
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

    # 降低上下文長度 / 輸出長度，提升穩定性
    gen_opts = {
        "num_ctx": 2048,
        "num_predict": 256,
        "temperature": 0.3,
        # "keep_alive": "5m",  # 可選：避免模型被釋放
    }

    try:
        resp = ollama.chat(model=req.model, messages=messages, options=gen_opts)
        answer = resp["message"]["content"]
        return AskRes(
            answer=answer,
            sources=[{
                "source_file": m.get("source_file"),
                "sheet": m.get("sheet"),
                "row_index": m.get("row_index")
            } for m in metas]
        )
    except Exception as e:
        # 不丟 500；前端能顯示並提示使用者
        return AskRes(
            answer=f"（一般建議）AI 回覆發生錯誤：{e}",
            sources=[{
                "source_file": m.get("source_file"),
                "sheet": m.get("sheet"),
                "row_index": m.get("row_index")
            } for m in metas]
        )
