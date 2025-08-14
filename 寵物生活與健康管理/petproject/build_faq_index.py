# build_faq_index.py — Paw&Day FAQ 向量索引建置（含 Ollama→ST 備援、絕對路徑）
import os, pandas as pd, textwrap, traceback, requests
import chromadb
from chromadb.config import Settings

# === 路徑設定（用絕對路徑更穩） ===
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(BASE_DIR, "faq_data.xlsx")               # 若你放 data/faq/faq_data.xlsx 就改這行
DB_DIR     = os.path.join(BASE_DIR, "normalized_tables", "faq_db") # views.py 的 DB_DIR 也要一致

# === 嵌入設定 ===
OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"
EMBED_MODEL      = "bge-m3"   # 多語模型，繁中效果佳

# sentence-transformers 緩存（僅備援時載入）
_st_model = None
def _embed_with_sentence_transformers(texts):
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer("BAAI/bge-m3")
    return _st_model.encode(texts, normalize_embeddings=True).tolist()

def embed(texts):
    """
    先試 Ollama /api/embeddings；若 404/連不到/逾時/格式不符，則改用 sentence-transformers 備援。
    """
    try:
        out = []
        for t in texts:
            r = requests.post(OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "input": t}, timeout=30)
            if r.status_code == 404:
                print("[embed] /api/embeddings 回 404，改用 sentence-transformers。")
                return _embed_with_sentence_transformers(texts)
            r.raise_for_status()
            data = r.json()
            if "embeddings" in data:
                out.append(data["embeddings"][0])
            elif "embedding" in data:
                out.append(data["embedding"])
            else:
                print("[embed] 無法解析 Ollama 回傳格式，改用 sentence-transformers。")
                return _embed_with_sentence_transformers(texts)
        return out
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        print("[embed] 無法連線/逾時，改用 sentence-transformers。")
        return _embed_with_sentence_transformers(texts)
    except Exception as e:
        print("[embed] 其他例外，改用 sentence-transformers：", e)
        return _embed_with_sentence_transformers(texts)

def main():
    print("=== Paw&Day FAQ 索引建置開始 ===")
    print(f"[PATH] Excel: {EXCEL_PATH}")
    print(f"[PATH] DB   : {DB_DIR}")

    try:
        xls = pd.ExcelFile(EXCEL_PATH)
    except FileNotFoundError:
        print(f"❌ 找不到 Excel：{EXCEL_PATH}")
        return

    rows = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet)
        # 偵測常見欄名：Question/Answer 或 Q/A 或 問題/答案/回覆/解答
        def pick(colnames, candidates):
            for c in colnames:
                if c.strip().lower() in candidates:
                    return c
            return None
        qcol = pick(df.columns, {"question","q","問題","題目"})
        acol = pick(df.columns, {"answer","a","答案","回覆","解答"})
        if not qcol or not acol:
            continue
        for _, r in df.iterrows():
            q = str(r[qcol]).strip() if pd.notna(r[qcol]) else ""
            a = str(r[acol]).strip() if pd.notna(r[acol]) else ""
            if q and a:
                rows.append({"text": f"問題：{q}\n回答：{a}", "meta": {"sheet": sheet}})

    if not rows:
        print("⚠️ 沒有讀到任何 Q/A 列（請確認欄名與內容）")
        return

    # 切片（避免太長）
    docs = []
    for i, row in enumerate(rows):
        chunks = textwrap.wrap(row["text"], width=400, replace_whitespace=False)
        for j, chunk in enumerate(chunks):
            docs.append((f"id_{i}_{j}", chunk, row["meta"]))

    os.makedirs(DB_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=DB_DIR, settings=Settings(anonymized_telemetry=False))
    # 先刪舊的 collection，確保乾淨
    try:
        client.delete_collection("faq")
    except Exception:
        pass
    col = client.get_or_create_collection(name="faq", metadata={"hnsw:space":"cosine"})

    # 產生向量並寫入
    embeddings = embed([d[1] for d in docs])
    col.add(
        ids=[d[0] for d in docs],
        documents=[d[1] for d in docs],
        metadatas=[d[2] for d in docs],
        embeddings=embeddings
    )
    print(f"✅ 完成索引，文件數：{col.count()}，資料庫位置：{DB_DIR}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ 建索引失敗：", e)
        traceback.print_exc()
