## 📦 環境變數設定（`.env`）

本專案使用 `.env` 管理機密設定與環境參數。請依照以下步驟設置你的開發環境：

### ✅ 步驟一：建立 `.env` 檔案

請在專案根目錄下建立 `.env` 檔案，可參考下列提供的 `.env` 檔案格式。

```bash
# ======== Django 安全設定 ========
SECRET_KEY=your-django-secret-key  # 請替換為你自己的 Django 密鑰
DEBUG=True  # 開發階段請設為 True，部署時建議設為 False

# ======== Google OAuth 登入用 ========
GOOGLE_CLIENT_ID=your-google-client-id  # 從 Google Cloud Console 取得
GOOGLE_CLIENT_SECRET=your-google-client-secret  # 從 Google Cloud Console 取得

# ======== Database 設定（MySQL）========
DB_NAME=your_db_name  # 資料庫名稱(pawday_db)
DB_USER=your_db_user  # 資料庫使用者名稱(root)
DB_PASSWORD=your_db_password  # 資料庫密碼
DB_HOST=localhost  # 通常為 localhost，除非是遠端資料庫
DB_PORT=5432  # PostgreSQL 預設為 5432

# ======== Email 設定（使用 SMTP 發信）========
EMAIL_HOST_USER=your-email@example.com  # SMTP 登入帳號，例如 Gmail。發信方
EMAIL_HOST_PASSWORD=your-email-password  # SMTP 密碼（如應用程式密碼）。發信方
DEFAULT_FROM_EMAIL=your-default-from@example.com  # 發信人 email。系統管理員
ADMIN_EMAIL=admin-notification@example.com  # 系統管理員通知用途。系統管理員

