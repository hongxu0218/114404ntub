@echo off
chcp 65001 >nul
echo ============================================
echo 虛擬機 AI 客服環境安裝腳本 (Windows 11)
echo ============================================
echo.

REM 檢查 Python 是否安裝
echo [1/5] 檢查 Python 環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 未安裝，請先安裝 Python 3.8+
    pause
    exit /b 1
)
python --version

REM 升級 pip
echo.
echo [2/5] 升級 pip...
python -m pip install --upgrade pip

REM 安裝 Python 依賴
echo.
echo [3/5] 安裝 AI 相關套件...
echo 正在安裝 sentence-transformers...
python -m pip install sentence-transformers

echo 正在安裝 chromadb...
python -m pip install chromadb

echo 正在安裝其他依賴...
python -m pip install pandas numpy requests

REM 安裝 Ollama (Windows 版本)
echo.
echo [4/5] 檢查 Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama 未安裝，請手動安裝：
    echo 1. 前往 https://ollama.com/download
    echo 2. 下載 Windows 版本安裝
    echo 3. 安裝完成後重新執行此腳本
    pause
    exit /b 1
) else (
    echo Ollama 已安裝
    ollama --version

    REM 下載模型
    echo 正在下載 qwen2.5:3b-instruct 模型...
    ollama pull qwen2.5:3b-instruct
)

REM 預載嵌入模型
echo.
echo [5/5] 預載嵌入模型...
python -c "
try:
    from sentence_transformers import SentenceTransformer
    print('正在下載 BAAI/bge-base-zh-v1.5 模型...')
    model = SentenceTransformer('BAAI/bge-base-zh-v1.5')
    print('模型下載完成，維度:', model.get_sentence_embedding_dimension())
except Exception as e:
    print('模型下載失敗:', e)
"

echo.
echo ============================================
echo 安裝完成！
echo ============================================
echo.
echo 接下來請執行：
echo 1. python setup_vm_ai.py  # 檢查環境
echo 2. python manage.py runserver 0.0.0.0:8000  # 啟動服務
echo.
echo 確保 Caddy 配置正確並指向 127.0.0.1:8000
echo.
pause