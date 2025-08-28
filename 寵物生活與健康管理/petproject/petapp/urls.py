# petapp/urls.py  # 此檔案定義 petapp 應用的 URL 路由設定

from django.urls import path, include  # 匯入 path，用來定義每個 URL 與對應的 view 函數
from . import views  # 匯入目前資料夾下的 views 模組
from .views import clear_signup_message  # 從 views 模組中個別匯入 clear_signup_message 函數
from . import chat_service   # 👈 引入新的檔案
from django.conf import settings  # 匯入 settings 模組，用來存取專案設定
from django.conf.urls.static import static  # 匯入 static，用來處理開發模式下的靜態檔案（如圖片）
from django.contrib import admin

urlpatterns = [
    # ============ 首頁 ============
    path('', views.home, name='home'),  # 首頁
    
    # ============ 診所註冊與管理系統 ============
    # 診所註冊
    path('clinic/register/', views.clinic_registration, name='clinic_registration'),  # 診所註冊頁面
    path('clinic/register/success/<int:clinic_id>/', views.clinic_registration_success, name='clinic_registration_success'),  # 註冊成功頁面
    
     # 診所驗證
    path('clinic/verify-license/', views.verify_vet_license, name='verify_vet_license'),
    # 診所管理主控台
    path('clinic/dashboard/', views.clinic_dashboard, name='clinic_dashboard'),  # 診所管理主控台
    
    # 醫師管理
    path('clinic/doctors/', views.manage_doctors, name='manage_doctors'),  # 管理診所醫師列表
    path('clinic/doctors/add/', views.add_doctor, name='add_doctor'),  # 新增獸醫師
    path('clinic/doctors/<int:doctor_id>/edit/', views.edit_doctor, name='edit_doctor'),  # 編輯獸醫師
    path('clinic/doctors/<int:doctor_id>/toggle/', views.toggle_doctor_status, name='toggle_doctor_status'),  # 啟用/停用獸醫師
    
    # 排班管理
    path('clinic/schedules/', views.manage_schedules, name='manage_schedules'),  # 管理排班（自己的排班）
    path('clinic/schedules/<int:doctor_id>/', views.manage_schedules, name='manage_doctor_schedules'),  # 管理指定醫師排班
    path('clinic/schedules/<int:doctor_id>/add/', views.add_schedule, name='add_schedule'),  # 新增排班
    path('clinic/schedules/<int:schedule_id>/edit/', views.edit_schedule, name='edit_schedule'),  # 編輯排班
    path('clinic/schedules/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),  # 刪除排班
    path('clinic/schedules/toggle/<int:schedule_id>/', views.toggle_schedule_status, name='toggle_schedule_status'),
    path('clinic/schedules/copy-week/<int:doctor_id>/', views.copy_week_schedule, name='copy_week_schedule'),
    
    # 診所預約管理
    path('clinic/appointments/', views.clinic_appointments, name='clinic_appointments'),  # 診所預約管理頁面
    path('clinic/appointments/<int:appointment_id>/', views.view_appointment_detail, name='view_appointment_detail'),  # 查看預約詳情
    path('clinic/appointments/<int:appointment_id>/confirm/', views.confirm_appointment, name='confirm_appointment'),  # 確認預約
    path('clinic/appointments/<int:appointment_id>/cancel/', views.clinic_cancel_appointment, name='clinic_cancel_appointment'),  # 診所取消預約


    # ============ Dashboard API ============
    path('api/dashboard/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/schedules/stats/', views.api_schedule_stats, name='api_schedule_stats'), 
    path('api/clinic/status/', views.api_clinic_status, name='api_clinic_status'),
    path('api/appointments/list/', views.api_appointments_list, name='api_appointments_list'),
    path('api/clinic/settings/', views.api_clinic_settings, name='api_clinic_settings'),
    
    # ============ 飼主預約系統（重新設計） ============
    path('appointments/create/<int:pet_id>/', views.create_appointment, name='create_appointment'),  # 新增預約（新流程）
    path('appointments/success/<int:appointment_id>/', views.appointment_success, name='appointment_success'),  # 預約成功頁面
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),  # 飼主取消預約
    path('appointments/my/', views.my_appointments, name='my_appointments'),  # 我的預約列表
    
    # ============ AJAX API（動態載入選項） ============
    path('api/doctors/', views.api_load_doctors, name='api_load_doctors'),  # 根據診所載入醫師列表
    path('api/time-slots/', views.api_load_time_slots, name='api_load_time_slots'),  # 根據條件載入可用時段
    path('api/clinics/search/', views.api_search_clinics, name='api_search_clinics'),  # 搜尋診所
    
    # ============ 通知系統 ============
    path('api/notifications/count/', views.get_notification_count, name='get_notification_count'),
    path('notifications/', views.notification_page, name='notification_page'),
    # ============ 註冊與帳號管理相關路由 ============
    path('select-account-type/', views.select_account_type, name='select_account_type'),  # 註冊後選擇帳號類型
    path('account/edit/', views.edit_profile, name='edit_profile'),  # 編輯個人資料
    path('accounts/mark-signup/', views.mark_from_signup_and_redirect, name='mark_from_signup_and_redirect'),  # 標記從註冊流程進來的狀態
    path('accounts/clear-signup-message/', clear_signup_message, name='clear_signup_message'),  # 清除註冊成功提示訊息

    # ============ 寵物資訊 CRUD（新增、列表、編輯、刪除） ============
    path('pets/add/', views.add_pet, name='add_pet'),  # 新增寵物
    path('pets/', views.pet_list, name='pet_list'),  # 寵物列表頁
    path('pets/edit/<int:pet_id>/', views.edit_pet, name='edit_pet'),  # 編輯指定寵物
    path('pets/delete/<int:pet_id>/', views.delete_pet, name='delete_pet'),  # 刪除指定寵物

    # ============ 寵物健康紀錄相關 ============
    path('pets/health/', views.health_rec, name='health_rec'),  # 健康紀錄首頁（所有寵物）
    path('pet/<int:pet_id>/add_daily_record/', views.add_daily_record, name='add_daily_record'),  # 新增每日健康紀錄
    path('save_daily_record/', views.save_daily_record, name='save_daily_record'),  # 儲存每日健康紀錄
    path('pet/<int:pet_id>/health/delete_record/', views.delete_daily_record, name='delete_daily_record'),  # 刪除每日健康紀錄
    path('daily_record/<int:record_id>/update/', views.update_daily_record, name='update_daily_record'),  # 更新每日健康紀錄

    # ============ 健康記錄-寵物體溫（列表、新增、編輯、刪除、共用函式） ============
    path('pets/<int:pet_id>/temperature/', views.tem_rec, name='tem_rec'),   # 體溫列表（趨勢圖+所有資料）
    path('pets/<int:pet_id>/temperature/add/', views.add_tem, name='add_tem'),  # 新增體溫記錄
    path('pets/<int:pet_id>/temperature/edit/<int:record_id>/', views.edit_tem, name='edit_tem'),  # 編輯體溫記錄
    path('pets/<int:pet_id>/temperature/delete/<int:record_id>/', views.delete_tem, name='delete_tem'),  # 刪除體溫記錄
    path('api/pet/<int:pet_id>/temperature/<int:year>/<int:month>/', views.get_monthly_tem, name='get_monthly_tem'),  # 共用函式（列表+健康記錄）

    # ============ 健康記錄-寵物體重（列表、新增、編輯、刪除、共用函式） ============
    path('pets/<int:pet_id>/weight/', views.weight_rec, name='weight_rec'),  # 體重列表（趨勢圖+所有資料）
    path('pets/<int:pet_id>/weight/add/', views.add_weight, name='add_weight'),  # 新增體重記錄
    path('pets/<int:pet_id>/weight/edit/<int:record_id>/', views.edit_weight, name='edit_weight'),  # 編輯體重記錄
    path('pets/<int:pet_id>/weight/delete/<int:record_id>/', views.delete_weight, name='delete_weight'),  # 刪除體重記錄
    path('api/pet/<int:pet_id>/weight/<int:year>/<int:month>/', views.get_monthly_weight, name='get_monthly_weight'),  # 共用函式（列表+健康記錄）

    # ============ 疫苗管理 ============
    path('vaccine/add/<int:pet_id>/', views.add_vaccine, name='add_vaccine'),  # 新增疫苗記錄
    path('vaccine/edit/<int:pet_id>/<int:vaccine_id>/', views.edit_vaccine, name='edit_vaccine'),  # 編輯疫苗記錄
    path('vaccine/delete/<int:vaccine_id>/', views.delete_vaccine, name='delete_vaccine'),  # 刪除疫苗記錄

    # ============ 驅蟲管理 ============
    path('deworm/add/<int:pet_id>/', views.add_deworm, name='add_deworm'),  # 新增驅蟲記錄
    path('deworm/edit/<int:pet_id>/<int:deworm_id>/', views.edit_deworm, name='edit_deworm'),  # 編輯驅蟲記錄
    path('deworm/delete/<int:deworm_id>/', views.delete_deworm, name='delete_deworm'),  # 刪除驅蟲記錄

    # ============ 報告管理 ============
    path('report/add/<int:pet_id>/', views.add_report, name='add_report'),  # 新增報告
    path('report/delete/<int:report_id>/', views.delete_report, name='delete_report'),  # 刪除報告

    # ============ 獸醫功能（保留部分，調整架構） ============
    path('vet/patients/', views.my_patients, name='vet_patients'),  # 獸醫的病患列表
    path('vet/appointments/', views.vet_appointments, name='vet_appointments'),  # 獸醫的預約列表
    path('vet/pets/<int:pet_id>/', views.vet_pet_detail, name='vet_pet_detail'),  # 獸醫查看寵物詳情

    # ============ 醫療記錄管理（獸醫專用） ============
    path('vet/medical-record/add/<int:pet_id>/', views.add_medical_record, name='add_medical_record'),  # 新增醫療記錄
    path('vet/medical-record/create/<int:pet_id>/', views.create_medical_record, name='create_medical_record'),  # 建立醫療記錄
    path('vet/medical-record/edit/<int:pet_id>/<int:record_id>/', views.edit_medical_record, name='edit_medical_record'),  # 編輯醫療記錄
    path('vet/medical-record/delete/<int:record_id>/', views.delete_medical_record, name='delete_medical_record'),  # 刪除醫療記錄

    # ============ 地圖功能相關 ============
    path('map/', views.map_home, name='map'),  # 地圖首頁
    path('api/locations/', views.api_locations, name='api_locations'),  # 地點資料API

    # ============ 24小時急診地圖功能 ============
    path('emergency_map/', views.emergency_map_home, name='emergency_map'),  # 24小時急診地圖首頁
    path('api/emergency-locations/', views.api_emergency_locations, name='api_emergency_locations'),  # 急診醫院資料API

    # ============ AI 聊天功能（本地模型 + FAQ） ============
    path("api/chat/", chat_service.api_chat),
    path("api/chat/stream/", chat_service.api_chat_stream),
    path("api/handoff/request/", chat_service.api_handoff_request),
    path("api/chat/kb_status", chat_service.api_kb_status),  # ← 健康檢查
]


# 靜態檔案處理（僅在開發模式下啟用）
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # 設定媒體檔案的 URL 路由