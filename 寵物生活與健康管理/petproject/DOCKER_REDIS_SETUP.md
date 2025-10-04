# 🐳 Docker + Redis 安裝手冊

## 📅 更新日期
2025-10-04

## 🎯 目的
為專案配置 Redis 快取系統，用於：
- 網站到訪數統計
- 通知系統快取
- 提升系統效能

---

## 📋 目錄
1. [安裝 Docker Desktop](#1-安裝-docker-desktop)
2. [驗證 Docker 安裝](#2-驗證-docker-安裝)
3. [安裝 Redis 容器](#3-安裝-redis-容器)
4. [測試 Redis 連線](#4-測試-redis-連線)
5. [設定開機自動啟動](#5-設定開機自動啟動)
6. [Python 套件安裝](#6-python-套件安裝)
7. [Django 設定](#7-django-設定)
8. [測試 Django 與 Redis](#8-測試-django-與-redis)
9. [常見問題](#9-常見問題)
10. [Docker 常用指令](#10-docker-常用指令)

---

## 1️⃣ 安裝 Docker Desktop

### 1.1 下載 Docker Desktop
1. 開啟瀏覽器，前往：**https://www.docker.com/products/docker-desktop/**
2. 點擊「**Download for Windows**」按鈕
3. 下載完成後會得到 `Docker Desktop Installer.exe` 檔案

### 1.2 安裝 Docker Desktop
1. **雙擊** `Docker Desktop Installer.exe` 執行安裝程式
2. 安裝選項：
   - ✅ **勾選**「Use WSL 2 instead of Hyper-V」（推薦）
   - ✅ **勾選**「Add shortcut to desktop」
3. 點擊「**OK**」開始安裝
4. 安裝完成後，點擊「**Close and restart**」**重新啟動電腦**

### 1.3 首次啟動設定
1. 重啟後，Docker Desktop 會自動啟動（如果沒有，點桌面的 Docker 圖示）
2. 可能會要求：
   - **更新 WSL 2 核心**：點擊連結下載並安裝（如果出現提示）
   - **登入 Docker Hub**：可以點「Skip」跳過（不需要帳號）
3. 看到 Docker Desktop 主畫面，**左下角顯示「Engine running」綠燈** ✅

---

## 2️⃣ 驗證 Docker 安裝

### 2.1 開啟終端機
- 按 **Windows 鍵 + R**，輸入 `cmd` 或 `powershell`
- 或搜尋「**命令提示字元**」或「**PowerShell**」

### 2.2 檢查 Docker 版本
```bash
docker --version
```

**預期輸出**：
```
Docker version 24.0.7, build afdd53b
```

### 2.3 測試 Docker 運作
```bash
docker run hello-world
```

**預期輸出**：
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
...
```

✅ 看到此訊息代表 Docker 安裝成功！

---

## 3️⃣ 安裝 Redis 容器

### 3.1 下載並啟動 Redis
在終端機（CMD 或 PowerShell）執行：

```bash
docker run -d -p 6379:6379 --name redis --restart always redis:latest
```

**指令說明**：
- `docker run` - 執行容器
- `-d` - 背景執行
- `-p 6379:6379` - 對應埠號（6379 是 Redis 預設埠號）
- `--name redis` - 容器名稱為 redis
- `--restart always` - **電腦重開機後自動啟動**
- `redis:latest` - 使用最新版 Redis 映像檔

**第一次執行會下載 Redis**，預期輸出：
```
Unable to find image 'redis:latest' locally
latest: Pulling from library/redis
...
Status: Downloaded newer image for redis:latest
a1b2c3d4e5f6...（容器 ID）
```

### 3.2 確認 Redis 容器運行
```bash
docker ps
```

**預期輸出**：
```
CONTAINER ID   IMAGE          STATUS         PORTS                    NAMES
a1b2c3d4e5f6   redis:latest   Up 10 seconds  0.0.0.0:6379->6379/tcp   redis
```

✅ STATUS 顯示 "Up" 代表正在運行！

---

## 4️⃣ 測試 Redis 連線

### 4.1 測試 Redis 服務
```bash
docker exec -it redis redis-cli ping
```

**預期輸出**：
```
PONG
```

✅ 看到 PONG 代表 Redis 正常運作！

### 4.2 測試基本操作（選用）
```bash
# 進入 Redis 命令列
docker exec -it redis redis-cli

# 測試指令
127.0.0.1:6379> SET test "Hello Redis"
OK
127.0.0.1:6379> GET test
"Hello Redis"
127.0.0.1:6379> exit
```

---

## 5️⃣ 設定開機自動啟動

### 5.1 Docker Desktop 自動啟動
1. 點擊 Windows 系統列的 **Docker 圖示**（鯨魚）
2. 點擊 **Settings**（齒輪圖示）
3. 左側選單點 **General**
4. ✅ **勾選**「**Start Docker Desktop when you log in**」
5. 點擊「**Apply & restart**」

### 5.2 Redis 容器自動重啟
已在步驟 3.1 使用 `--restart always` 設定，無需額外操作。

**驗證方式**：
1. 重啟電腦
2. 開機後執行 `docker ps`
3. 應該會看到 redis 容器正在運行

---

## 6️⃣ Python 套件安裝

### 6.1 切換到專案目錄
```bash
cd D:\114404ntub\寵物生活與健康管理\petproject
```

### 6.2 安裝 Redis 相關套件
```bash
pip install redis django-redis
```

**預期輸出**：
```
Successfully installed django-redis-6.0.0 redis-6.4.0
```

---

## 7️⃣ Django 設定

### 7.1 修改 `petproject/settings.py`

找到 Cache 設定區塊（約第 159 行），**替換為**：

```python
# ===== Cache 快取設定 (用於到訪數等功能) =====
# 統一使用 Redis 快取（開發和生產環境都用 Redis）
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',  # Redis 連線位置
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,  # 最大連線數
                'retry_on_timeout': True,  # 超時重試
            },
            'SOCKET_CONNECT_TIMEOUT': 5,  # 連線超時（秒）
            'SOCKET_TIMEOUT': 5,  # 讀寫超時（秒）
        }
    }
}
```

### 7.2 更新 `requirements.txt`

在「資料庫」區塊下方新增：

```txt
# Redis 快取
redis==6.4.0
django-redis==6.0.0
```

---

## 8️⃣ 測試 Django 與 Redis

### 8.1 確認 Docker 和 Redis 正在運行
```bash
# 檢查 Docker Desktop 狀態（系統列應有鯨魚圖示）
# 檢查 Redis 容器
docker ps
```

應該看到 redis 容器在運行中。

### 8.2 測試 Django Cache 連線
```bash
cd D:\114404ntub\寵物生活與健康管理\petproject
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'OK'); print('✅ Redis 連線成功！' if cache.get('test') == 'OK' else '❌ 失敗')"
```

**預期輸出**：
```
✅ Redis 連線成功！
```

### 8.3 啟動 Django 開發伺服器測試
```bash
python manage.py runserver
```

訪問網站後，到管理後台查看「到訪數統計」是否正常顯示。

---

## 9️⃣ 常見問題

### ❓ Q1: Redis 連線失敗（Error 10061）

**錯誤訊息**：
```
ConnectionError: Error 10061 connecting to 127.0.0.1:6379
```

**解決方法**：
1. 檢查 Docker Desktop 是否在運行（系統列有鯨魚圖示）
2. 檢查 Redis 容器狀態：
   ```bash
   docker ps
   ```
3. 如果沒看到 redis，重新啟動：
   ```bash
   docker start redis
   ```
4. 如果仍失敗，重新創建容器：
   ```bash
   docker rm -f redis
   docker run -d -p 6379:6379 --name redis --restart always redis:latest
   ```

---

### ❓ Q2: Docker 指令找不到（command not found）

**原因**：Docker Desktop 未啟動或環境變數問題

**解決方法**：
1. 開啟 Docker Desktop 應用程式
2. 等待左下角顯示「Engine running」綠燈
3. 重新開啟終端機

---

### ❓ Q3: 重啟電腦後 Redis 沒有自動啟動

**檢查步驟**：
1. 確認 Docker Desktop 設定：
   - Settings → General → 勾選「Start Docker Desktop when you log in」
2. 確認 Redis 容器重啟策略：
   ```bash
   docker inspect redis | findstr "RestartPolicy"
   ```
   應該顯示 `"Name": "always"`

3. 如果不是 always，重新創建容器：
   ```bash
   docker rm -f redis
   docker run -d -p 6379:6379 --name redis --restart always redis:latest
   ```

---

### ❓ Q4: pip 安裝失敗

**錯誤訊息**：
```
ERROR: Could not find a version that satisfies the requirement redis
```

**解決方法**：
1. 更新 pip：
   ```bash
   python -m pip install --upgrade pip
   ```
2. 重新安裝：
   ```bash
   pip install redis django-redis
   ```

---

### ❓ Q5: Docker Desktop 佔用太多資源

**優化設定**：
1. 開啟 Docker Desktop → Settings → Resources
2. 調整：
   - **CPUs**: 2-4（依電腦規格）
   - **Memory**: 2-4 GB
   - **Swap**: 1 GB
3. 點擊「Apply & restart」

---

## 🔟 Docker 常用指令

### 容器管理
```bash
# 查看運行中的容器
docker ps

# 查看所有容器（包含停止的）
docker ps -a

# 啟動容器
docker start redis

# 停止容器
docker stop redis

# 重啟容器
docker restart redis

# 刪除容器
docker rm redis

# 強制刪除運行中的容器
docker rm -f redis
```

### Redis 操作
```bash
# 進入 Redis CLI
docker exec -it redis redis-cli

# 測試連線
docker exec -it redis redis-cli ping

# 查看 Redis 資訊
docker exec -it redis redis-cli INFO

# 清空所有快取
docker exec -it redis redis-cli FLUSHALL
```

### 日誌查看
```bash
# 查看 Redis 日誌
docker logs redis

# 即時查看日誌（按 Ctrl+C 退出）
docker logs -f redis

# 查看最後 100 行日誌
docker logs --tail 100 redis
```

### 系統管理
```bash
# 查看 Docker 資源使用狀況
docker stats redis

# 查看容器詳細資訊
docker inspect redis

# 清理未使用的映像檔和容器
docker system prune
```

---

## 📊 專案中使用 Cache 的功能

### ✅ 會用到 Redis 的功能：

1. **網站到訪數統計** (`petapp/middleware.py`)
   - 記錄總訪問數
   - 記錄今日/本週訪問數
   - 用 session 去重

2. **管理後台儀表板** (`petapp/admin_dashboard.py`)
   - 顯示總訪問數
   - 顯示今日/本週訪問數據

3. **通知系統** (`petapp/notification_views.py`)
   - 快取通知列表（5分鐘）
   - 快取未讀通知數量（1分鐘）
   - 快取通知統計資料（10分鐘）

### ❌ 不會用到 Redis 的功能：

- 寵物管理
- 預約系統
- 醫療記錄
- 社交功能
- 診所管理
- Email 通知
- AI 聊天
- 健康記錄

---

## 🚀 部署到虛擬機

### Windows 11 虛擬機部署步驟

1. **在虛擬機上安裝 Docker Desktop**
   - 按照本手冊步驟 1-5 安裝

2. **複製專案到虛擬機**
   ```bash
   # 確保 requirements.txt 包含：
   redis==6.4.0
   django-redis==6.0.0
   ```

3. **安裝 Python 套件**
   ```bash
   pip install -r requirements.txt
   ```

4. **確認 Redis 運行**
   ```bash
   docker ps
   ```

5. **測試連線**
   ```bash
   python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'OK'); print('OK' if cache.get('test') == 'OK' else 'FAIL')"
   ```

6. **啟動 Django**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

---

## 📝 系統需求

### 最低需求
- **作業系統**: Windows 10/11 Pro/Enterprise（需支援 WSL2）
- **記憶體**: 4 GB RAM
- **硬碟空間**: 10 GB
- **處理器**: 支援虛擬化技術的 64-bit CPU

### 建議配置
- **記憶體**: 8 GB RAM 以上
- **硬碟空間**: 20 GB SSD
- **處理器**: 4 核心以上

---

## 🎯 總結

完成本手冊後，你的系統將具備：

✅ Docker Desktop 環境
✅ Redis 快取服務（開機自動啟動）
✅ Django 與 Redis 整合
✅ 網站到訪數統計功能
✅ 通知系統效能優化

---

## 📚 參考資源

- [Docker 官方文檔](https://docs.docker.com/)
- [Redis 官方文檔](https://redis.io/docs/)
- [django-redis 文檔](https://github.com/jazzband/django-redis)
- [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

---

## 👨‍💻 維護資訊

- **建立日期**: 2025-10-04
- **最後更新**: 2025-10-04
- **版本**: v1.0
- **維護者**: Claude Code

如有問題請聯絡開發團隊。
