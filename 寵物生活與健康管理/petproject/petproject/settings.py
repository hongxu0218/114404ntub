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

# 設定允許的主機（可加入網域/IP），開發階段可為空，部署時必填
ALLOWED_HOSTS = []



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
            'charset': 'utf8mb4',
            'use_unicode': True,
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'autocommit': True,
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
LOGIN_REDIRECT_URL = '/'  # 登入成功導向首頁
ACCOUNT_LOGOUT_REDIRECT_URL = '/'  # allauth 登出後導向首頁
LOGOUT_REDIRECT_URL = '/accounts/logout-success/'  # 自訂登出成功頁面
SOCIALACCOUNT_LOGIN_REDIRECT_URL = '/'  # Google 登入後導向首頁

# 設定登入方式為 email，email 為必填


ACCOUNT_LOGIN_METHODS = {'email'}     # 使用 email 作為帳號登入依據
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']# 必填欄位
ACCOUNT_EMAIL_VERIFICATION = 'none'         # 關閉 email 驗證（開發階段建議關），上線時請改為 'mandatory'

# 註冊成功後立即導向登入頁（GET 請求立即登入）
SOCIALACCOUNT_LOGIN_ON_GET = True

# 自訂 Google 登入行為
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_ADAPTER = 'petapp.adapter.MySocialAccountAdapter'


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
STATIC_URL = 'static/'  # 靜態檔案 URL 路徑前綴
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

# 簡單的記憶體快取設定
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}


# ===== 國際化與時區 =====
LANGUAGE_CODE = 'zh-hant'   # 預設 en-us 英文，改為繁體中文 zh-hant
TIME_ZONE = 'Asia/Taipei'   # 預設 UTC，改為台北時區

USE_I18N = True # 啟用國際化
USE_TZ = True   # 啟用時區支援



# ===== 預設主鍵欄位型別設定（從 Django 3.2 起建議）=====
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'