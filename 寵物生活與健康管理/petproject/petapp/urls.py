# petapp/urls.py  # 此檔案定義 petapp 應用的 URL 路由設定

from django.urls import path  # 匯入 path，用來定義每個 URL 與對應的 view 函數
from . import views  # 匯入目前資料夾下的 views 模組
from .views import clear_signup_message  # 從 views 模組中個別匯入 clear_signup_message 函數
from django.conf import settings  # 匯入 settings 模組，用來存取專案設定
from django.conf.urls.static import static  # 匯入 static，用來處理開發模式下的靜態檔案（如圖片）

urlpatterns = [
    # 通知
    path('notifications/count/', views.get_notification_count, name='get_notification_count'),
    path('notifications/', views.notification_page, name='notification_page'),

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
    path('daily_record/<int:record_id>/update/', views.update_daily_record, name='update_daily_record'),


    # 飼主預約相關
    path('appointments/create/', views.create_vet_appointment, name='create_appointment'),  # 新增預約
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'), # 飼主取消預約（使用者為 appointment.owner）

    # 獸醫相關
    path('vet/appointments/', views.vet_appointments, name='vet_appointments'),
    path('vet/my-patients/', views.my_patients, name='my_patients'),
    path('vet/add-record/<int:pet_id>/', views.add_medical_record, name='add_medical_record'),
    path('vet/appointments/cancel/<int:appointment_id>/', views.vet_cancel_appointment, name='vet_cancel_appointment'), # 獸醫取消預約（使用者為 appointment.vet.user）
    path('medical_records/create/<int:pet_id>/', views.create_medical_record, name='create_medical_record'),
 
    # 獸醫預約相關 
    path('vet/availability/', views.vet_availability_settings, name='vet_availability_settings'),
    path('appointments/get-available-times/', views.get_available_times, name='get_available_times'),
    path('vet/availability/edit/<int:schedule_id>/', views.edit_vet_schedule, name='edit_vet_schedule'),
    path('vet/availability/delete/<int:schedule_id>/', views.delete_vet_schedule, name='delete_vet_schedule'),

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

    #  疫苗
    path('vaccine/add/<int:pet_id>/', views.add_vaccine, name='add_vaccine'),  #  新增疫苗
    path('vaccine/edit/<int:pet_id>/<int:vaccine_id>/', views.edit_vaccine, name='edit_vaccine'),  # 編輯疫苗
    path('vaccine/delete/<int:vaccine_id>/', views.delete_vaccine, name='delete_vaccine'),  # 刪除疫苗
    #  驅蟲
    path('deworm/add/<int:pet_id>/', views.add_deworm, name='add_deworm'),  #  新增驅蟲
    path('deworm/edit/<int:pet_id>/<int:deworm_id>/', views.edit_deworm, name='edit_deworm'),  # 編輯驅蟲
    path('deworm/delete/<int:deworm_id>/', views.delete_deworm, name='delete_deworm'),  # 刪除驅蟲
    # 報告
    path('report/add/<int:pet_id>/', views.add_report, name='add_report'),  # 新增報告
    path('report/delete/<int:report_id>/', views.delete_report, name='delete_report'),  # 刪除報告

    # 病歷
    path('vet/pets/<int:pet_id>/', views.vet_pet_detail, name='vet_pet_detail'),
    path('medical/edit/<int:pet_id>/<int:record_id>/', views.edit_medical_record, name='edit_medical_record'),
    path('medical/delete/<int:record_id>/', views.delete_medical_record, name='delete_medical_record'),

     # 地圖功能相關
    path('map/', views.map_home, name='map'),
    path('api/locations/', views.api_locations, name='api_locations'),

    # 🚨 24小時急診地圖功能
    path('emergency_map/', views.emergency_map_home, name='emergency_map'),  # 24小時急診地圖首頁
    path('api/emergency-locations/', views.api_emergency_locations, name='api_emergency_locations'),  # 急診醫院資料 API

    # 二手領養
    path('adoption/', views.adoption, name='adoption'),  # 二手領養頁面
    path('adoption/user/', views.my_adoption, name='my_adoption'),  # 飼主的送養記錄
    path('adoption/add/', views.add_adoption, name='add_adoption'), # 新增送養寵物
    path('adoption/pet/<int:adoption_id>/', views.adoption_petDetail, name='adoption_petDetail'), #寵物的詳細資料頁面
    path('pet/<int:pet_id>/send_for_adoption/', views.send_for_adoption, name='send_for_adoption'),# 從‘我的寵物’ 送養

    path('adoption/<int:pk>/edit/', views.edit_adoption, name='edit_adoption'), # 編輯資料頁面
    path('adoption/<int:adoption_id>/delete_image/<str:picture_field>/', views.delete_adoption_image, name='delete_adoption_image'), # 刪除 送養寵物的圖片
    path("adoption/<int:adoption_id>/delete_file/<str:field_name>/", views.delete_file, name="delete_file"),  # 刪除 送養寵物的檔案
    path('adoption/<int:pk>/delete/', views.delete_adoption, name='delete_adoption'), # 刪除資料（可用 GET 確認或 POST 真的刪除）

    path('pet/<int:pet_id>/change_owner/', views.change_owner, name='change_owner'),  # (寵物)更改飼主
    path('transfer/confirm/<int:transfer_id>/', views.transfer_confirm, name='transfer_confirm'), # 飼主確認被轉讓之寵物

]



# 靜態檔案處理（僅在開發模式下啟用）
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # 設定媒體檔案的 URL 路由
