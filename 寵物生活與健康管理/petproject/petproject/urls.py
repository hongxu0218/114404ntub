"""
URL configuration for ntub114404 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from petapp import views    #
from django.urls import include
from django.views.generic import TemplateView
from allauth.account.views import LoginView
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.home, name='home'),  # 根路徑顯示首頁

    path('register/', include('petapp.urls')),
    path('accounts/', include('allauth.urls')),  # 加入 allauth 的帳號處理路由
    path('accounts/logout-success/', views.logout_success, name='logout_success'),
    # path('listone/',views.listone),
    # path('listall/',views.listall),
    # path('',views.index),
    # path('index/', views.index),
    path('', include('petapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
