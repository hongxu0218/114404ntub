# petproject/urls.py - 這是整個 Django 專案的主路由設定檔

from django.contrib import admin  # 匯入 Django 後台管理模組
from django.urls import path  # 匯入 URL 路由設定功能
from django.urls import include  # 匯入 include 用來導入子應用路由
from petapp import views  # 匯入自定義 views 函數
from petapp.views import CustomSignupView, CustomSocialSignupView  # 匯入自定義的註冊 view

from django.conf import settings  # 匯入設定檔
from django.conf.urls.static import static  # 開發環境下處理媒體檔案

urlpatterns = [
    path('admin/', admin.site.urls),  # Django 管理後台入口
    path('', views.home, name='home'),  # 首頁 URL 對應 home 函數

    # Django Allauth 提供的預設登入、註冊、密碼重設等功能
    path('accounts/', include('allauth.urls')),

    # 自定義註冊與社群登入流程相關路由
    path('accounts/signup/', CustomSignupView.as_view(), name='account_signup'),  # 自訂註冊流程
    path('accounts/select-type/', views.select_type_then_social_login, name='select_type_then_social'),  # Google 登入前選擇帳號類型
    path('accounts/logout-success/', views.logout_success, name='logout_success'),  # 登出成功頁面
    path('accounts/social/signup/extra/', views.social_signup_extra, name='social_signup_extra'),  # Google 註冊補資料頁
    path("accounts/social/signup/", CustomSocialSignupView.as_view(), name="socialaccount_signup"),  # 覆寫 Allauth 的社群註冊

    # 將 petapp 應用的 urls.py 加入整體路由中（例如 dashboard、寵物管理等）
    path('', include('petapp.urls')),
]

# 開發環境下允許媒體檔案顯示（例如上傳的寵物照片）
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
