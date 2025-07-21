## 📦 環境變數設定（`.env`）
> 跟 `manage.py` 放在同一層 

本專案使用 `.env` 管理機密設定與環境參數。請依照以下步驟設置你的開發環境：

### ✅ 步驟一：建立 `.env` 檔案

請在專案根目錄下建立 `.env` 檔案，可參考下列提供的 `.env` 檔案格式。

```bash
# ======== Django 安全設定 ========
SECRET_KEY=your-django-secret-key  # 請替換為你自己的 Django 密鑰
DEBUG=True  # 開發階段請設為 True，部署時建議設為 False

ALLOWED_HOSTS=127.0.0.1,localhost,127.0.0.1:8000
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

# ======== Google OAuth 登入用 ========
GOOGLE_CLIENT_ID=your-google-client-id  # 從 Google Cloud Console 取得
GOOGLE_CLIENT_SECRET=your-google-client-secret  # 從 Google Cloud Console 取得

# ======== Database 設定（MySQL）========
DB_NAME=your_db_name  # 資料庫名稱(pawday_db)
DB_USER=your_db_user  # 資料庫使用者名稱(root)
DB_PASSWORD=your_db_password  # 資料庫密碼
DB_HOST=localhost  # 通常為 localhost，除非是遠端資料庫
DB_PORT=3306  # PostgreSQL 預設為 5432 // MySQL 預設為 3306

# ======== Email 設定（使用 SMTP 發信）========
EMAIL_HOST_USER=your-email@example.com  # SMTP 登入帳號，例如 Gmail。發信方
EMAIL_HOST_PASSWORD=your-email-password  # SMTP 密碼（如應用程式密碼）。發信方
DEFAULT_FROM_EMAIL=your-default-from@example.com  # 發信人 email。系統管理員
ADMIN_EMAIL=admin-notification@example.com  # 系統管理員通知用途。系統管理員
```
### ✅ 步驟二：從 Google Cloud Console 取得 ID 和 金鑰

★注意： `settings.py` 裡15、16、196、197 有金鑰，金鑰放在 `.env`

到 Google Cloud Console 申請 OAuth 憑證
👉 前往：Google Cloud Console

步驟：
1. 創建專案

2. 啟用 API：搜尋並啟用「Google+ API」與「OAuth 2.0 API」

3. 建立 OAuth 同意畫面

    • 使用者類型：External（外部）
   
    • Email、應用名稱等資料填寫即可

5. 建立憑證 → OAuth client ID

    • 應用類型選：Web application
   
    • 授權的 redirect URI 請填入：
   
   ```bash
   http://127.0.0.1:8000/accounts/google/login/callback/
   ```

7. 記下 Client ID 與 Client Secret

### ✅ 步驟三：下載 MySQL

下載MySQL：<https://dev.mysql.com/downloads/file/?id=539682>

> 點藍色字 "No thanks, just start my download."

參考教學影片：<https://www.youtube.com/watch?v=3zzszKQ8Kk4>

#### 使用 MySQL Workbench 建立資料庫

#### 📌 安裝
- 下載：<https://dev.mysql.com/downloads/workbench/>

#### 📌 建立資料庫步驟

1. 開啟 **MySQL Workbench**
2. 連接你的資料庫（預設為：
   - Host: `localhost`
   - User: `root`
3. 在左邊點選 **Schemas（資料庫）**
4. 在空白處點右鍵，選擇 **Create Schema**
5. 在彈出視窗中輸入以下資訊：
   - **Schema Name**：輸入你想要的資料庫名稱（例如：`pawday_db`）
   - **Default Collation**：選擇 `utf8mb4_general_ci`
6. 點選 **Apply**
7. 再次點選 **Apply**
8. 點選 **Finish**

🎉 這樣就建立完成囉 🎉
> 建好之後記得 **同步資料表** 、 **新增 admin 帳號**
> ```bash
> python manage.py makemigrations
> ```
> ```bash
> python manage.py migrate
> ```
> 如果是第一次換資料庫（例如從 SQLite 換成 MySQL），那原本 admin 帳號就不會跟著過去，你要重新建立一次：
> ```bash
> python manage.py createsuperuser
> ```


### ✅ 步驟四：設定（使用 SMTP 發信）
★注意： `settings.py` 裡 91~96
相關帳號密碼在 LINE 群組 記事本
