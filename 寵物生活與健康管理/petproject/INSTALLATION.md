# 🚀 部署安裝指南

## 快速安裝

### 1. 克隆專案
```bash
git clone <your-repository-url>
cd petproject
```

### 2. 安裝 Python 依賴
```bash
pip install -r requirements.txt
```

### 3. 安裝 Ollama 服務
```bash
# Windows
# 下載並安裝 Ollama: https://ollama.ai/download
# 安裝 AI 模型
ollama pull qwen2.5:3b-instruct
```

### 4. 運行 AI 設定工具
```bash
# Windows
setup_ai.bat
# 選擇 [1] 完整安裝設定

# Linux/Mac
python ai_service_manager.py setup
```

### 5. 啟動 Django 服務
```bash
python manage.py runserver 0.0.0.0:8000
```

## 常見問題解決

### ❌ 錯誤：No module named 'ollama'
**解決方案：**
```bash
pip install ollama==0.5.4
```

### ❌ 錯誤：No module named 'chromadb'
**解決方案：**
```bash
pip install chromadb==1.1.0
```

### ❌ 錯誤：Ollama 服務連接失敗
**解決方案：**
1. 確認 Ollama 服務運行中：`ollama list`
2. 確認模型已安裝：`ollama pull qwen2.5:3b-instruct`
3. 檢查服務端口：`http://localhost:11434`

### ❌ 錯誤：ChromaDB 初始化失敗
**解決方案：**
```bash
# 重建向量資料庫
python ai_service_manager.py rebuild
```

## 環境檢查工具

使用內建工具檢查環境：
```bash
# 檢查所有依賴
python ai_service_manager.py check

# 檢查服務狀態
python ai_service_manager.py status

# 測試 AI 客服
python ai_service_manager.py test
```

## 手動安裝步驟

如果自動安裝失敗，可以手動執行：

### 1. 安裝 Python 套件
```bash
pip install Django==5.2.4
pip install django-allauth==65.10.0
pip install ollama==0.5.4
pip install chromadb==1.1.0
pip install sentence-transformers==5.1.1
pip install pandas==2.3.0
pip install openpyxl==3.1.5
```

### 2. 設定資料庫
```bash
python manage.py migrate
```

### 3. 建立向量資料庫
```bash
python ai_service_manager.py import
python ai_service_manager.py rebuild
```

## 系統需求

- **Python:** 3.8+
- **RAM:** 至少 4GB (推薦 8GB)
- **硬碟:** 至少 2GB 可用空間
- **網路:** 首次安裝需要網路連接下載 AI 模型

## 支援平台

- ✅ Windows 10/11
- ✅ Ubuntu 20.04+
- ✅ macOS 10.15+
- ✅ Docker (待支援)