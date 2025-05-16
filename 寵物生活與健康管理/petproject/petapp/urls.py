# petapp/urls.py
from django.urls import path
from . import views
from .views import clear_signup_message
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('dashboard/owner/', views.owner_dashboard, name='owner_dashboard'),
    path('dashboard/vet/', views.vet_dashboard, name='vet_dashboard'),
    path('select-account-type/', views.select_account_type, name='select_account_type'),
    path('account/edit/', views.edit_profile, name='edit_profile'),
    path('accounts/mark-signup/', views.mark_from_signup_and_redirect, name='mark_from_signup_and_redirect'),
    path('accounts/clear-signup-message/', clear_signup_message, name='clear_signup_message'),
    path('pets/add/', views.add_pet, name='add_pet'),
    path('pets/', views.pet_list, name='pet_list'),
    path('pets/edit/<int:pet_id>/', views.edit_pet, name='edit_pet'),
    path('pets/delete/<int:pet_id>/', views.delete_pet, name='delete_pet'),

    path('pets/', views.pet_list, name='pet_list'),
    path('pets/health/', views.health_rec, name='health_rec'),
    path('pet/<int:pet_id>/add_daily_record/', views.add_daily_record, name='add_daily_record'),
    path('save_daily_record/', views.save_daily_record, name='save_daily_record'),
    path('pet/<int:pet_id>/health/delete_record/', views.delete_daily_record, name='delete_daily_record'),

]

# 靜態檔案處理
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)