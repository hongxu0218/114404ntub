#  ===== 匯入模組與路徑設置 ===== 
from pathlib import Path    # 匯入 Path 類別，用來處理路徑相關操作
from decouple import config # 匯入 decouple 的 config 方法，用來安全讀取 .env 檔中的機密資訊
import os                   # 匯入 os 模組，用於處理目錄路徑等功能
from dotenv import load_dotenv
load_dotenv()  # 載入 .env 檔案

# 專案根目錄路徑（BASE_DIR 表示 manage.py 所在的資料夾）
BASE_DIR = Path(__file__).resolve().parent.parent



#  ===== 安全性設定 ===== 
# 秘密金鑰與除錯模式
SECRET_KEY = config('SECRET_KEY')   # 從 .env 檔案讀取 Django 的 SECRET_KEY
DEBUG = config('DEBUG', cast=bool)  # 從 .env 讀取，是否啟用除錯模式（開發環境為 True，上線務必為 False）

# ALLOWED_HOSTS 設定
ALLOWED_HOSTS_STR = config('ALLOWED_HOSTS', default='127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(',') if host.strip()]

# CSRF 設定
CSRF_TRUSTED_ORIGINS_STR = config('CSRF_TRUSTED_ORIGINS', default='http://127.0.0.1:8000,http://localhost:8000')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STR.split(',') if origin.strip()]

# 🚨 HTTPS 生產環境安全設定 (開發時停用)
if False:  # 暫時停用所有 HTTPS 設定
    # 確保 ALLOWED_HOSTS 不為空
    if not ALLOWED_HOSTS:
        ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'pawday114404.duckdns.org']

    # HTTPS 安全設定（Caddy 自動處理 SSL）
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Caddy 代理設定
    # SECURE_SSL_REDIRECT = True   # 強制 HTTPS 重定向 (開發時註解)
    SECURE_HSTS_SECONDS = 31536000  # HSTS 一年
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # SESSION 與 CSRF Cookie 安全設定
    SESSION_COOKIE_SECURE = True   # 僅 HTTPS 傳送
    CSRF_COOKIE_SECURE = True      # 僅 HTTPS 傳送
    # 生產環境也允許JavaScript訪問CSRF cookie（為了AJAX請求）
    CSRF_COOKIE_HTTPONLY = False
else:
    # 開發環境設置
    CSRF_COOKIE_HTTPONLY = False   # 開發環境允許JavaScript訪問CSRF cookie

# CSRF設置 - 適用於所有環境
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_SAMESITE = 'Lax'  # 防止CSRF攻擊但允許必要的跨站請求
CSRF_COOKIE_AGE = 3600  # CSRF cookie 1小時過期，增加安全性
CSRF_USE_SESSIONS = False  # 使用cookie而不是session存儲CSRF token

# 額外的安全措施
if not DEBUG:
    # 生產環境額外的CSP安全頭
    SECURE_CONTENT_SECURITY_POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"

    # 其他安全標頭
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    


#  ===== 安裝的應用程式（App） ===== 
INSTALLED_APPS = [
    # Django 預設功能模組(基本 app)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    

    # 本地 App
    'petapp',
    
    # 第三方登入驗證套件 allauth 社群登入支援
    'django.contrib.sites',     # 必須啟用才能使用 allauth
    'allauth',
    'allauth.account',          # 帳號系統
    'allauth.socialaccount',    # 社群帳號登入系統
    'allauth.socialaccount.providers.google',   # 啟用 Google 登入

    #換圖片就刪舊圖(寵物資料）
    'django_cleanup.apps.CleanupConfig',
]



# ===== 中介軟體設定（middleware pipeline）=====
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',    # 安全性設定
    'django.contrib.sessions.middleware.SessionMiddleware',     # Session 處理
    'django.middleware.common.CommonMiddleware',                # 一般請求處理
    'django.middleware.csrf.CsrfViewMiddleware',                # 防止 CSRF 攻擊
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # 驗證機制
    'django.contrib.messages.middleware.MessageMiddleware',     # 提示訊息機制
    'django.middleware.clickjacking.XFrameOptionsMiddleware',   # 防止點擊劫持攻擊

    'allauth.account.middleware.AccountMiddleware',     # allauth 專用中介軟體
]



# ===== URL 與 WSGI 設定 =====
# 網站的 URL 總路由設定檔位置
ROOT_URLCONF = 'petproject.urls'

# WSGI 應用程式設定（伺服器入口點）
WSGI_APPLICATION = 'petproject.wsgi.application'



# ===== Template 模板引擎設定 =====
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  # 使用 Django 原生模板系統
        'DIRS': [BASE_DIR / 'templates'],   # 加上templates路徑
        'APP_DIRS': True,   # 自動尋找 app 中的 templates 資料夾
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',   # 提供 request 物件給模板使用
                'django.contrib.auth.context_processors.auth',  # 使用者驗證狀態等資訊
                'django.contrib.messages.context_processors.messages',  # 訊息提示功能
            ],
        },
    },
]



# ===== 資料庫設定（使用 MySQL）=====
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),   # 如果在本機使用
        'PORT': os.getenv('DB_PORT'),        # MySQL 預設 port
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}



# ===== allauth 設定與自訂表單指定 =====
# 指定註冊時使用自訂表單（CustomSignupForm）
ACCOUNT_FORMS = {
    'signup': 'petapp.forms.CustomSignupForm',
}



# ===== 密碼驗證規則 =====
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', # 防止與個資相似
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',   # 設定密碼最小長度
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',  # 禁用常見密碼
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', # 禁用純數字密碼
    },
]



# ===== allauth 認證系統設定 =====
# 必須指定 SITE_ID 才能啟用 allauth
SITE_ID = 1

# 設定驗證後端，加入 allauth 的支援
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # 原生 Django 認證系統
    'allauth.account.auth_backends.AuthenticationBackend',  # 加入 allauth 的登入方式
)

# 登入與登出成功後導向頁面
LOGIN_REDIRECT_URL = '/login-redirect/'  # 登入成功導向智能重導向頁面
ACCOUNT_LOGOUT_REDIRECT_URL = '/'  # allauth 登出後導向首頁
LOGOUT_REDIRECT_URL = '/accounts/logout-success/'  # 自訂登出成功頁面
# SOCIALACCOUNT_LOGIN_REDIRECT_URL = '/'  # 註解掉，讓 adapter 的 get_login_redirect_url() 決定

# 設定登入方式為 email，email 為必填


ACCOUNT_LOGIN_METHODS = {'email'}     # 使用 email 作為帳號登入依據
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']# 必填欄位
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'         # 關閉 email 驗證（開發階段建議關），上線時請改為 'mandatory'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True 
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 7
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

# 郵件設定
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True

# 顯示信件主旨與寄件網址設定
ACCOUNT_EMAIL_SUBJECT_TEMPLATE = "password_reset_subject.txt"
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"  # HTTPS 部署

# 註冊成功後立即導向登入頁（GET 請求立即登入）
SOCIALACCOUNT_LOGIN_ON_GET = True

# 自訂 Google 登入行為
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = 'petapp.adapter.MySocialAccountAdapter'

# 禁用 allauth 的重複登入訊息
SOCIALACCOUNT_STORE_TOKENS = False
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"  # HTTPS 部署設定
SOCIALACCOUNT_LOGIN_ON_GET = True  # 已存在，但確保設定

# 禁用 allauth 的預設登入成功訊息
ACCOUNT_SESSION_REMEMBER = None
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = None
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = None

# 自訂 allauth 訊息標籤以避免重複
ACCOUNT_MESSAGES = {
    'logged_in': '',  # 禁用預設登入成功訊息
    'logged_out': '',  # 禁用預設登出訊息
}


# ===== 郵件後端設定（開發階段使用 console 模式）=====
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')
ADMIN_EMAIL = config('ADMIN_EMAIL')

# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'



# ===== 靜態與媒體檔案設定 =====
# 靜態檔案設定（CSS、JS）
STATIC_URL = '/static/'  # 靜態檔案 URL 路徑前綴
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # 產品環境的靜態檔案收集路徑
STATICFILES_DIRS = [
    BASE_DIR / 'static' # 加入 static 路徑
]

# 媒體檔案（使用者上傳檔案）設定
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')



# ===== 社群登入（Google OAuth） =====
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],  # 權限範圍
        'AUTH_PARAMS': {
            'prompt': 'select_account'  # 每次登入都要求選擇帳號
        },
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID'),    # 從 .env 讀取 Client ID
            'secret': config('GOOGLE_CLIENT_SECRET'),   # 從 .env 讀取 Client Secret
            'key': ''  # 預設空值即可
        }
    }
}

# Google OAuth 回調 URL 設定
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/logout-success/'

# ===== Logging 配置 =====
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'petapp.adapter': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'petapp.views': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}



# ===== 國際化與時區 =====
LANGUAGE_CODE = 'zh-hant'   # 預設 en-us 英文，改為繁體中文 zh-hant
TIME_ZONE = 'Asia/Taipei'   # 預設 UTC，改為台北時區

USE_I18N = True # 啟用國際化
USE_TZ = True   # 啟用時區支援



# ===== 預設主鍵欄位型別設定（從 Django 3.2 起建議）=====
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'