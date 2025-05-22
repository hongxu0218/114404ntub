# petapp/urls.py  # 此檔案定義 petapp 應用的 URL 路由設定

from django.urls import path  # 匯入 path，用來定義每個 URL 與對應的 view 函數
from . import views  # 匯入目前資料夾下的 views 模組
from .views import clear_signup_message  # 從 views 模組中個別匯入 clear_signup_message 函數
from django.conf import settings  # 匯入 settings 模組，用來存取專案設定
from django.conf.urls.static import static  # 匯入 static，用來處理開發模式下的靜態檔案（如圖片）

urlpatterns = [
    # 導向不同使用者主控台的路由設定
    path('dashboard/', views.dashboard_redirect, name='dashboard'),  # 導向主控台（根據帳號角色判斷導向）
    path('dashboard/owner/', views.owner_dashboard, name='owner_dashboard'),  # 飼主主控台
    path('dashboard/vet/', views.vet_dashboard, name='vet_dashboard'),  # 獸醫主控台

    # 註冊與帳號管理相關路由
    path('select-account-type/', views.select_account_type, name='select_account_type'),  # 註冊後選擇帳號類型
    path('account/edit/', views.edit_profile, name='edit_profile'),  # 編輯個人資料
    path('accounts/mark-signup/', views.mark_from_signup_and_redirect, name='mark_from_signup_and_redirect'),  # 標記從註冊流程進來的狀態
    path('accounts/clear-signup-message/', clear_signup_message, name='clear_signup_message'),  # 清除註冊成功提示訊息

    # 寵物資訊 CRUD（新增、列表、編輯、刪除）
    path('pets/add/', views.add_pet, name='add_pet'),  # 新增寵物
    path('pets/', views.pet_list, name='pet_list'),  # 寵物列表頁
    path('pets/edit/<int:pet_id>/', views.edit_pet, name='edit_pet'),  # 編輯指定寵物
    path('pets/delete/<int:pet_id>/', views.delete_pet, name='delete_pet'),  # 刪除指定寵物

    # 寵物健康紀錄相關
    path('pets/health/', views.health_rec, name='health_rec'),  # 健康紀錄首頁（所有寵物）
    path('pet/<int:pet_id>/add_daily_record/', views.add_daily_record, name='add_daily_record'),  # 新增每日健康紀錄
    path('save_daily_record/', views.save_daily_record, name='save_daily_record'),  # 儲存每日健康紀錄
    path('pet/<int:pet_id>/health/delete_record/', views.delete_daily_record, name='delete_daily_record'),  # 刪除每日健康紀錄

    # 健康記錄-寵物體溫（列表、新增、編輯、刪除、共用函式）
    path('pets/<int:pet_id>/temperature/', views.tem_rec, name='tem_rec'),   #體溫列表（趨勢圖+所有資料）
    path('pets/<int:pet_id>/temperature/add/', views.add_tem, name='add_tem'),  #新增體溫記錄
    path('pets/<int:pet_id>/temperature/edit/<int:record_id>/', views.edit_tem, name='edit_tem'),  #編輯體溫記錄
    path('pets/<int:pet_id>/temperature/delete/<int:record_id>/', views.delete_tem, name='delete_tem'),  #刪除體溫記錄
    path('api/pet/<int:pet_id>/temperature/<int:year>/<int:month>/', views.get_monthly_tem, name='get_monthly_tem'),  #共用函式（列表+健康記錄）

    # 健康記錄-寵物體重（列表、新增、編輯、刪除、共用函式）
    path('pets/<int:pet_id>/weight/', views.weight_rec, name='weight_rec'),  #體重列表（趨勢圖+所有資料）
    path('pets/<int:pet_id>/weight/add/', views.add_weight, name='add_weight'),  #新增體重記錄
    path('pets/<int:pet_id>/weight/edit/<int:record_id>/', views.edit_weight, name='edit_weight'),  #編輯體重記錄
    path('pets/<int:pet_id>/weight/delete/<int:record_id>/', views.delete_weight, name='delete_weight'),  #刪除體重記錄
    path('api/pet/<int:pet_id>/weight/<int:year>/<int:month>/', views.get_monthly_weight, name='get_monthly_weight'),  #共用函式（列表+健康記錄）

    # 地圖功能相關
    path('map/', views.map_home, name='map_home'),
    path('api/locations/', views.api_locations, name='api_locations'),
    path('api/stats/', views.api_stats, name='api_stats'),

]

# 靜態檔案處理（僅在開發模式下啟用）
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # 設定媒體檔案的 URL 路由
