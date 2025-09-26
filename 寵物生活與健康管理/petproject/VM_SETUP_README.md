# Windows 11 虛擬機 AI 客服設置指南

## 文件說明

此目錄包含三個重要文件，用於在 Windows 11 虛擬機上設置 AI 客服環境：

### 📋 文件列表

1. **`install_ai_deps.bat`** - 自動安裝所有依賴套件
2. **`setup_vm_ai.py`** - 環境檢查腳本
3. **`rebuild_vectordb.py`** - 重建向量資料庫腳本（執行檢查腳本時自動創建）

## 🚀 快速開始

### 步驟 1：複製文件到虛擬機
將以下文件複製到虛擬機的專案目錄：
```
- 整個 petproject 資料夾
- 特別確保包含：
  ✓ setup_vm_ai.py
  ✓ install_ai_deps.bat
  ✓ .env 文件
  ✓ petapp/chat_service.py
  ✓ rag/chroma_db/ 目錄
```

### 步驟 2：安裝 Python（如果尚未安裝）
1. 前往 [Python 官網](https://www.python.org/downloads/)
2. 下載 Python 3.8 或更新版本
3. 安裝時記得勾選 "Add Python to PATH"

### 步驟 3：安裝 Ollama（如果尚未安裝）
1. 前往 [Ollama 官網](https://ollama.com/download)
2. 下載 Windows 版本
3. 安裝完成後重新啟動命令提示字元

### 步驟 4：執行自動安裝
在專案目錄下，**以系統管理員身分**開啟命令提示字元，執行：
```batch
install_ai_deps.bat
```

這個腳本會：
- 檢查 Python 環境
- 安裝所有必要的 Python 套件
- 下載 Ollama AI 模型
- 預載嵌入模型

### 步驟 5：檢查環境
安裝完成後，執行環境檢查：
```batch
python setup_vm_ai.py
```

## 🔧 手動安裝（如果自動安裝失敗）

### 安裝 Python 套件：
```batch
pip install sentence-transformers chromadb pandas numpy requests torch
```

### 安裝 Ollama 模型：
```batch
ollama pull qwen2.5:3b-instruct
```

### 下載嵌入模型：
```batch
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-zh-v1.5')"
```

## 🔍 問題排除

### 常見問題：

1. **"python 不是內部或外部命令"**
   - 確認 Python 已安裝並加入 PATH
   - 或使用 `py` 替代 `python`

2. **"ollama 不是內部或外部命令"**
   - 確認 Ollama 已安裝
   - 重新啟動命令提示字元

3. **模型下載失敗**
   - 檢查網路連接
   - 確認可以訪問 huggingface.co

4. **向量資料庫錯誤**
   - 執行 `python rebuild_vectordb.py`
   - 確認 rag/chroma_db 目錄存在

5. **編碼錯誤**
   - 確認 .env 文件使用 UTF-8 編碼
   - 使用記事本另存為時選擇 UTF-8

## 🏃‍♂️ 啟動服務

環境檢查通過後，啟動 Django 服務：
```batch
python manage.py runserver 0.0.0.0:8000
```

## 🌐 Caddy 配置

確保 Caddy 配置正確：
```caddy
pawday114404.duckdns.org {
    handle_path /static/* {
        root * "C:/path/to/your/project/staticfiles"
        file_server
    }

    handle_path /media/* {
        root * "C:/path/to/your/project/media"
        file_server
    }

    reverse_proxy 127.0.0.1:8000 {
        header_up Host {host}
        header_up X-Forwarded-Proto {scheme}
        header_up X-Real-IP {remote_host}
    }
}
```

## 📞 測試 AI 客服

服務啟動後，AI 客服應該能正確回答：
- ✅ "如何按讚和留言"
- ✅ "社群功能有哪些"
- ✅ "怎麼發布動態"
- ✅ 寵物健康護理相關問題

## 📝 注意事項

1. **防火牆設定**：確保開放 Port 8000（內部）、80 和 443（外部）
2. **資源需求**：建議虛擬機至少 4GB RAM，因為 AI 模型需要記憶體
3. **定期更新**：定期更新 Ollama 和模型版本
4. **備份資料**：定期備份 rag/chroma_db 向量資料庫

## 🆘 求助

如果遇到問題：
1. 先執行 `python setup_vm_ai.py` 檢查環境
2. 查看錯誤訊息並對照此文檔
3. 確認所有步驟都已正確執行