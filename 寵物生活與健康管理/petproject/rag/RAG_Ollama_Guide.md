# 寵物生活與健康管理 RAG + Ollama 使用說明

## 0) 進入專案資料夾
```bash
cd "C:\Users\susan\OneDrive - ntub.edu.tw\畢業專題\114404ntub\寵物生活與健康管理\petproject\rag"
```

---

## 1) 安裝/檢查 Ollama 與下載模型
```bash
ollama list
ollama pull qwen2.5:3b-instruct
ollama pull qwen2.5:7b-instruct
ollama pull llama3.2:3b-instruct
ollama pull phi3:3.8b-mini-instruct
```

若出現連不上服務（`ECONNREFUSED`），啟動：
```bash
ollama serve
```

---

## 2) 安裝 Python 套件（RAG 所需）

### 方式 A（推薦，用需求檔）
```bash
pip install -r .\requirements_rag.txt
```

### 方式 B（逐一安裝）
```bash
pip install pandas chromadb sentence-transformers tqdm ollama fastapi uvicorn[standard]
```

---

## 3) 句向量模型（HuggingFace）
線上使用會自動下載；若要離線：
```bash
huggingface-cli download BAAI/bge-small-zh-v1.5 --local-dir .\models\bge-small-zh-v1.5
```

---

## 4) Excel → 向量資料庫（一次或資料更新時）
```bash
python .\excel_to_chroma_qa.py --input ".\data\faq_data.xlsx" --persist_dir ".\chroma_db" --collection faq_collection
```

### 重建乾淨庫
```bash
rmdir /s /q ".\chroma_db"
```

---

## 5) 純檢索測試
```bash
python .\query_chroma.py --persist_dir ".\chroma_db" --collection faq_collection --q "寵物走失了該怎麼辦？"
```

---

## 6) 問答（命令列版）

### 6A) 原版（含加速參數）
```bash
python .\ask_ollama.py --q "寵物走失了該怎麼辦？" --persist_dir ".\chroma_db" --collection faq_collection --top_k 3 --model qwen2.5:3b-instruct --num_ctx 2048 --num_predict 256 --snippet_chars 320 --stream
```

### 6B) 加速版
```bash
python .\ask_ollama_fast.py --q "寵物走失了該怎麼辦？" --persist_dir ".\chroma_db" --collection faq_collection --top_k 3 --model qwen2.5:3b-instruct --num_ctx 2048 --num_predict 256 --snippet_chars 320 --fast_threshold 0.33 --stream
```

---

## 7) 啟動 API 服務
```bash
uvicorn rag_ollama_server:app --host 127.0.0.1 --port 8001 --reload
```

### 呼叫方式（POST）
```
POST http://127.0.0.1:8001/ask
Content-Type: application/json
```

Body 範例：
```json
{
  "q": "怎麼幫貓咪洗澡比較放鬆？",
  "top_k": 3,
  "model": "qwen2.5:3b-instruct",
  "persist_dir": "chroma_db",
  "collection": "faq_collection"
}
```

---

## 8) Django 介接
建立 **endpoint** 轉發到：
```
http://127.0.0.1:8001/ask
```

---

## 9) 加速技巧
- 模型小一點：`qwen2.5:3b-instruct`
- 縮短生成：`--num_predict 200`
- 少帶上下文：`--snippet_chars 260`、`--top_k 2`
- 串流：`--stream`
- 資料庫放本機非 OneDrive，例如：`C:\PawDayRAG\chroma_db`

---

## 10) 快速檢查
```bash
ollama list
ollama serve
ollama pull qwen2.5:3b-instruct
pip install ollama fastapi uvicorn[standard]
```
