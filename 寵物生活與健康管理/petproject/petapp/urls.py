# petapp/urls.py  # 此檔案定義 petapp 應用的 URL 路由設定

from django.urls import path, include  # 匯入 path，用來定義每個 URL 與對應的 view 函數
from . import views  # 匯入目前資料夾下的 views 模組
from .views import clear_signup_message  # 從 views 模組中個別匯入 clear_signup_message 函數
from . import chat_service, views_handoff  # 匯入進階AI客服和人工客服模組
from django.conf import settings  # 匯入 settings 模組，用來存取專案設定
from django.conf.urls.static import static  # 匯入 static，用來處理開發模式下的靜態檔案（如圖片）
from django.contrib import admin

# 修正重複路由問題



urlpatterns = [
    # ============ 首頁 ============
    path('', views.home, name='home'),
    
    # ============ 測試頁面 ============
    path('test/theme/', views.test_theme, name='test_theme'),
    
    # ============ 診所註冊與管理系統 ============
    path('clinic/register/', views.clinic_registration, name='clinic_registration'),
    path('clinic/register/success/<int:clinic_id>/', views.clinic_registration_success, name='clinic_registration_success'),
    path('clinic/verify-license/', views.verify_vet_license, name='verify_vet_license'),
    path('clinic/dashboard/', views.clinic_dashboard, name='clinic_dashboard'),

    # ============ 診所模式管理 ============
    path('clinic/<int:clinic_id>/switch-mode/', views.switch_clinic_mode, name='switch_clinic_mode'),
    path('clinic/mode/check/', views.check_clinic_mode, name='check_clinic_mode'),

    # 營業時間 API
    path('api/business-hours/get/', views.api_get_business_hours, name='api_get_business_hours'),
    path('api/business-hours/save/', views.api_save_business_hours, name='api_save_business_hours'),
    path('api/clinic/business-status/', views.get_clinic_business_status, name='api_clinic_business_status'),
    
    # 醫師管理
    path('clinic/doctors/', views.manage_doctors, name='manage_doctors'),
    path('clinic/doctors/add/', views.add_doctor, name='add_doctor'),
    path('clinic/doctors/<int:doctor_id>/edit/', views.edit_doctor, name='edit_doctor'),
    path('clinic/doctors/<int:doctor_id>/update/', views.update_doctor, name='update_doctor'),
    path('clinic/doctors/<int:doctor_id>/toggle/', views.toggle_doctor_status, name='toggle_doctor_status'),
    
    # ============ 全新排班管理系統 ============
    # 排班總覽
    path('vet/schedule/', views.schedule_dashboard, name='schedule_dashboard'),
    path('vet/schedule/weekly/', views.weekly_calendar, name='weekly_calendar'),
    path('vet/schedule/monthly/', views.monthly_calendar, name='monthly_calendar'),
    path('vet/schedule/list/', views.schedule_list, name='schedule_list'),
    
    # 排班CRUD
    path('vet/schedule/create/', views.schedule_create, name='schedule_create'),
    path('vet/schedule/<int:schedule_id>/', views.schedule_detail, name='schedule_detail'),
    path('vet/schedule/<int:schedule_id>/edit/', views.schedule_edit, name='schedule_edit'),
    path('vet/schedule/<int:schedule_id>/<str:action>/', views.schedule_action, name='schedule_action'),
    
    # 排班異動管理
    path('vet/change-requests/', views.change_request_list, name='change_request_list'),
    path('api/change-requests/<int:request_id>/review/', views.api_review_change_request, name='api_review_change_request'),
    
    # 排班 API
    path('api/schedule/check-conflicts/', views.api_check_schedule_conflicts, name='api_check_schedule_conflicts'),
    path('api/schedule/<int:schedule_id>/conflicts/', views.api_schedule_conflicts, name='api_schedule_conflicts'),
    path('api/dashboard/schedule-stats/', views.api_schedule_stats, name='api_schedule_stats'),
    path('api/dashboard/schedules/', views.api_dashboard_schedules, name='api_dashboard_schedules'),

    # ============ 快速設定功能 ============
    
    path('clinic/simple-setup/', views.simple_clinic_setup, name='simple_clinic_setup'),
    path('clinic/business-hours/quick-set/', views.quick_set_business_hours, name='quick_set_business_hours'),

    # ============ 舊版排班 API 和例外處理 - 已完全移除 ============
    # 所有排班相關的API、例外處理都已移除
    
    # ============ 所有排班相關API已移除 ============
    
    # =========診所模式 API ============
    path('api/clinic/mode/', views.api_get_clinic_mode,  name='api_get_clinic_mode'),
    path('api/clinic/can-switch-mode/', views.api_can_switch_mode, name='api_can_switch_mode'),
    path('api/doctors/status/', views.api_doctors_status, name='api_doctors_status'),
    
    # ============ 預約管理系統 ============
    path('clinic/appointments/', views.clinic_appointments, name='clinic_appointments'),
    path('clinic/appointments/<int:appointment_id>/', views.view_appointment_detail, name='view_appointment_detail'),
    path('clinic/appointments/<int:appointment_id>/confirm/', views.confirm_appointment, name='confirm_appointment'),
    path('clinic/appointments/<int:appointment_id>/cancel/', views.clinic_cancel_appointment, name='clinic_cancel_appointment'),
    path('clinic/appointments/<int:appointment_id>/complete/', views.complete_appointment, name='complete_appointment'),

    # ============ 獸醫師工作台系統 ============
    path('vet/home/', views.vet_home, name='vet_home'),
    path('vet/patients/', views.my_patients_enhanced, name='my_patients'),
    path('vet/appointments/', views.vet_appointments, name='vet_appointments'),
    path('clinic/appointments/create-walkin/', views.create_walkin_appointment, name='create_walkin_appointment'),
    path('vet/appointments/<int:appointment_id>/cancel/', views.vet_cancel_appointment, name='vet_cancel_appointment'),
    path('api/vet/appointments/batch-operation/', views.vet_batch_appointment_operation, name='vet_batch_appointment_operation'),
    path('vet/pets/<int:pet_id>/', views.pet_detail, name='pet_detail'),
    path('vet/profile/edit/', views.edit_vet_profile, name='edit_vet_profile'),
    
    # 醫療記錄管理
    path('vet/records/create/<int:pet_id>/', views.create_medical_record, name='create_medical_record_for_pet'),
    path('vet/records/history/', views.vet_medical_history, name='vet_medical_history'),
    path('vet/records/edit/<int:pet_id>/<int:record_id>/', views.edit_medical_record, name='edit_medical_record'),
    path('vet/records/delete/<int:record_id>/', views.delete_medical_record, name='delete_medical_record'),

    # 獸醫師疫苗和驅蟲記錄管理
    path('vet/vaccine/add/<int:pet_id>/', views.vet_add_vaccine, name='vet_add_vaccine'),
    path('vet/deworm/add/<int:pet_id>/', views.vet_add_deworm, name='vet_add_deworm'),

    # 獸醫師報告管理
    path('vet/report/upload/<int:pet_id>/', views.upload_report, name='upload_report'),
    path('vet/report/delete/<int:report_id>/', views.delete_vet_report, name='delete_vet_report'),

    # ============ Dashboard API（統一整理）============
    path('api/dashboard/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/clinic/status/', views.api_clinic_status, name='api_clinic_status'),
    path('api/appointments/list/', views.api_appointments_list, name='api_appointments_list'),
    path('api/clinic/settings/', views.api_clinic_settings, name='api_clinic_settings'),
    path('api/clinic/business-hours/', views.api_clinic_business_hours, name='api_clinic_business_hours'),
    
    # ============ 獸醫師專用 API ============
    path('api/vet/patients-overview/', views.api_vet_patients_overview, name='api_vet_patients_overview'),
    path('api/vet/today-schedule/', views.api_vet_today_schedule, name='api_vet_today_schedule'),
    
    # ============ 其他 API ============
    path('api/doctors/', views.api_load_doctors, name='api_load_doctors'),
    path('api/time-slots/', views.api_load_time_slots, name='api_load_time_slots'),
    path('api/doctor-time-slots/', views.api_doctor_time_slots, name='api_doctor_time_slots'),
    path('api/clinics/search/', views.api_search_clinics, name='api_search_clinics'),
    path('api/business-hours/get/', views.api_get_business_hours, name='api_get_business_hours'),
    path('api/business-hours/save/', views.api_save_business_hours, name='api_save_business_hours'),
    path('api/notifications/count/', views.get_notification_count, name='get_notification_count'),
    path('api/appointments/process-expired/', views.api_process_expired_appointments, name='api_process_expired_appointments'),
    
    # ============ 動物用藥資料庫 API ============
    path('api/drugs/search/', views.drug_search_api, name='drug_search_api'),
    
    # ============ 飼主預約系統 ============
    path('appointments/create/<int:pet_id>/', views.create_appointment, name='create_appointment'),
    path('appointments/success/<int:appointment_id>/', views.appointment_success, name='appointment_success'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/my/', views.my_appointments, name='my_appointments'),
    
    # AJAX路由
    path('api/search-clinics/', views.search_clinics, name='search_clinics'),
    path('api/load-doctors/', views.load_doctors, name='load_doctors'),
    
    # ============ 通知系統 API ============
    path('api/notifications/', views.get_notifications_api, name='get_notifications_api'),
    path('api/notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # ============ 註冊與帳號管理 ============
    path('select-account-type/', views.select_account_type, name='select_account_type'),
    path('account/edit/', views.edit_profile, name='edit_profile'),
    path('accounts/mark-signup/', views.mark_from_signup_and_redirect, name='mark_from_signup_and_redirect'),
    path('accounts/clear-signup-message/', clear_signup_message, name='clear_signup_message'),

    # ============ 寵物資訊 CRUD ============
    path('pets/add/', views.add_pet, name='add_pet'),
    path('pets/', views.pet_list, name='pet_list'),
    path('pets/edit/<int:pet_id>/', views.edit_pet, name='edit_pet'),
    path('pets/delete/<int:pet_id>/', views.delete_pet, name='delete_pet'),
    
    # ============ 寵物 API ============
    path('api/breed-choices/', views.get_breed_choices, name='get_breed_choices'),

    # ============ 寵物健康紀錄 ============
    path('pets/health/', views.health_rec, name='health_rec'),
    path('pet/<int:pet_id>/add_daily_record/', views.add_daily_record, name='add_daily_record'),
    path('save_daily_record/', views.save_daily_record, name='save_daily_record'),
    path('pet/<int:pet_id>/health/delete_record/', views.delete_daily_record, name='delete_daily_record'),
    path('daily_record/<int:record_id>/update/', views.update_daily_record, name='update_daily_record'),
    path('api/chart-data/', views.daily_record_chart_data, name='daily_record_chart_data'),


    # ============ 疫苗管理 ============
    path('vaccine/add/<int:pet_id>/', views.add_vaccine, name='add_vaccine'),
    path('vaccine/edit/<int:pet_id>/<int:vaccine_id>/', views.edit_vaccine, name='edit_vaccine'),
    path('vaccine/delete/<int:vaccine_id>/', views.delete_vaccine, name='delete_vaccine'),

    # ============ 驅蟲管理 ============
    path('deworm/add/<int:pet_id>/', views.add_deworm, name='add_deworm'),
    path('deworm/edit/<int:pet_id>/<int:deworm_id>/', views.edit_deworm, name='edit_deworm'),
    path('deworm/delete/<int:deworm_id>/', views.delete_deworm, name='delete_deworm'),

    # ============ 報告管理 ============
    path('report/add/<int:pet_id>/', views.add_report, name='add_report'),
    path('report/delete/<int:report_id>/', views.delete_report, name='delete_report'),

    # ============ 領養專區 ============
    path('adoption/', views.adoption, name='adoption'),
    path('adoption/add/', views.add_adoption, name='add_adoption'),
    path('adoption/add_adoptpet/', views.add_adoptpet, name='add_adoptpet'),
    path('adoption/my/', views.my_adoption, name='my_adoption'),
    path('adoption/<int:adoption_id>/', views.adoption_petDetail, name='adoption_petDetail'),
    path('adoption/edit/<int:pk>/', views.edit_adoption, name='edit_adoption'),
    path('adoption/delete/<int:pk>/', views.delete_adoption, name='delete_adoption'),
    path('adoption/toggle_status/<int:pk>/', views.toggle_status, name='toggle_status'),
    path('adoption/transfer_request/<int:pk>/', views.adoption_transfer_request, name='adoption_transfer_request'),
    path('adoption/transfers/my/', views.my_adoption_transfers, name='my_adoption_transfers'),
    path('adoption/transfer/confirm/<int:transfer_id>/', views.adoption_transfer_confirm, name='adoption_transfer_confirm'),
    path('adoption/send_for_adoption/<int:pet_id>/', views.send_for_adoption, name='send_for_adoption'),
    path('adoption/delete_image/<int:adoption_id>/<str:picture_field>/', views.delete_adoption_image, name='delete_adoption_image'),
    path('adoption/delete_file/<int:adoption_id>/<str:field_name>/', views.delete_file, name='delete_adoption_file'),
    
    # ============ 寵物轉讓 ============
    path('transfer/change_owner/<int:pet_id>/', views.change_owner, name='change_owner'),
    path('transfer/confirm/<int:transfer_id>/', views.transfer_confirm, name='transfer_confirm'),

    # ============ 地圖功能 (已移除) ============
    # path('map/', views.map_home, name='map'),
    # path('api/locations/', views.api_locations, name='api_locations'),
    # path('emergency_map/', views.emergency_map_home, name='emergency_map'),
    # path('api/emergency-locations/', views.api_emergency_locations, name='api_emergency_locations'),

    # ============ 醫療記錄 API ============
    path('api/medical-records/<int:record_id>/', views.api_medical_record_detail, name='api_medical_record_detail'),

    # ============ 登入重導向 ============
    path('login-redirect/', views.login_redirect, name='login_redirect'),

    # ============ 帳號刪除 ============
    path('account/delete/confirm/', views.delete_account_confirm, name='delete_account_confirm'),
    path('account/delete/', views.delete_account, name='delete_account'),

    # ============ AI 客服功能 ============
    path('ai-health/', views.ai_health_check, name='ai_health_check'),

    # ============ 進階AI客服API ============
    path('api/chat/', include([
        path('', chat_service.api_chat, name='api_chat'),
        path('stream/', chat_service.api_chat_stream, name='api_chat_stream'),
        path('kb_status/', chat_service.api_kb_status, name='api_kb_status'),
        path('clear_cache/', chat_service.api_clear_cache, name='api_clear_cache'),
    ])),

    # ============ 人工客服轉接 ============
    path('api/handoff/', include([
        path('request/', views_handoff.api_handoff_request, name='api_handoff_request'),
        path('user/send/', views_handoff.api_handoff_user_send, name='api_handoff_user_send'),
        path('user/end/', views_handoff.api_handoff_user_end, name='api_handoff_user_end'),
        path('poll/', views_handoff.api_handoff_poll, name='api_handoff_poll'),
    ])),

    # ============ 客服控台（職員端） ============
    path('staff/handoff/', include([
        path('', views_handoff.handoff_console, name='handoff_console'),
        path('<int:ticket_id>/', views_handoff.handoff_console, name='handoff_console_ticket'),
        path('tickets/poll/', views_handoff.handoff_staff_tickets_poll, name='handoff_staff_tickets_poll'),
        path('<int:ticket_id>/reply/', views_handoff.handoff_agent_reply, name='handoff_agent_reply'),
        path('<int:ticket_id>/close/', views_handoff.handoff_agent_close, name='handoff_agent_close'),
        path('<int:ticket_id>/accept/', views_handoff.handoff_agent_accept, name='handoff_agent_accept'),
        path('<int:ticket_id>/poll/', views_handoff.handoff_staff_poll, name='handoff_staff_poll'),
    ])),
]

# 靜態檔案處理
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)