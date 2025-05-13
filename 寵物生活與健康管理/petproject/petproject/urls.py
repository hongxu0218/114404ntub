# petproject/urls.py
from django.contrib import admin
from django.urls import path

from django.urls import include
from petapp import views
from petapp.views import CustomSignupView
from petapp.views import CustomSocialSignupView

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),  # 首頁

    path('accounts/', include('allauth.urls')),  # 登入、註冊、密碼等功能
    path('accounts/signup/', CustomSignupView.as_view(), name='account_signup'),
    path('accounts/select-type/', views.select_type_then_social_login, name='select_type_then_social'),
    path('accounts/logout-success/', views.logout_success, name='logout_success'),
    path('accounts/social/signup/extra/', views.social_signup_extra, name='social_signup_extra'),
    path("accounts/social/signup/", CustomSocialSignupView.as_view(), name="socialaccount_signup"),

    path('', include('petapp.urls')),  # 引入 petapp 自訂功能路由（例如註冊）
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)