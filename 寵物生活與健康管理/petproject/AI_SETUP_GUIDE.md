# 毛日好 AI 客服系統設置指南

## 🚀 系統概述

AI客服系統已成功整合到毛日好專案中，使用RAG (Retrieval-Augmented Generation) 技術，結合向量資料庫和Ollama本地大語言模型。

## ✅ 已完成的設置

1. **Python套件安裝**：所有必要的RAG套件已安裝
2. **向量資料庫**：ChromaDB已建立，包含豐富的寵物FAQ資料
3. **Django整合**：AI客服功能已整合到網站
4. **前端界面**：專業的聊天界面已建立

## 📋 待完成的設置

### 1. 安裝 Ollama

在Windows上安裝Ollama：

1. 前往 [Ollama官網](https://ollama.ai) 下載Windows版本
2. 運行安裝程式
3. 安裝完成後，重新啟動命令提示字元

### 2. 下載語言模型

開啟命令提示字元，執行：

```bash
# 下載建議的模型（輕量級，適合一般使用）
ollama pull qwen2.5:3b-instruct

# 或下載更強大的模型（需要更多資源）
ollama pull qwen2.5:7b-instruct
```

### 3. 啟動RAG服務

在專案的 `rag` 目錄中執行：

```bash
cd rag
uvicorn rag_ollama_server:app --host 127.0.0.1 --port 8001 --reload
```

## 🔧 使用方式

### 訪問AI客服

1. 登入毛日好網站
2. 導航到 `社群專區` > `AI 客服`
3. 或直接訪問：`http://localhost:8000/ai-chat/`

### 測試功能

訪問健康檢查端點：
```
http://localhost:8000/ai-health/
```

## 🛠️ 故障排除

### 常見問題

1. **無法連接到AI服務**
   - 確認RAG服務已啟動（端口8001）
   - 檢查Ollama是否正在運行

2. **模型載入失敗**
   - 確認已下載模型：`ollama list`
   - 重新下載：`ollama pull qwen2.5:3b-instruct`

3. **記憶體不足**
   - 使用較小的模型：`qwen2.5:3b-instruct`
   - 關閉其他耗費記憶體的應用程式

### 檢查服務狀態

```bash
# 檢查Ollama
ollama list

# 檢查RAG服務
curl http://127.0.0.1:8001/health

# 檢查模型狀態
curl http://127.0.0.1:8001/ollama
```

## 📁 檔案結構

```
petproject/
├── rag/                          # RAG相關檔案
│   ├── data/
│   │   └── faq_data.xlsx         # FAQ資料（已包含）
│   ├── chroma_db/                # 向量資料庫（已建立）
│   ├── rag_ollama_server.py      # RAG API服務器
│   └── excel_to_chroma_qa.py     # 資料轉換工具
├── petapp/
│   └── views.py                  # AI客服視圖（已整合）
└── templates/
    └── ai_chat/
        └── chat.html             # AI客服界面
```

## 🎯 功能特色

- **智能問答**：基於真實寵物FAQ資料的精準回答
- **向量檢索**：使用最先進的語義搜索技術
- **本地部署**：資料完全在本地，保護隱私
- **可擴展**：可以輕鬆添加更多FAQ資料

## 📞 支援

如有問題，請檢查：
1. 所有服務是否正常運行
2. 網路連接是否正常
3. 依賴套件是否完整安裝

## 🔄 更新資料

如需更新FAQ資料：

1. 編輯 `rag/data/faq_data.xlsx`
2. 重新建立向量資料庫：
   ```bash
   cd rag
   python excel_to_chroma_qa.py --input "./data/faq_data.xlsx" --persist_dir "./chroma_db" --collection faq_collection
   ```
3. 重啟RAG服務

---

🐾 **毛日好 AI 客服系統** - 為您的寵物提供24/7專業諮詢服務！