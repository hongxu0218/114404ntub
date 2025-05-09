# petapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('dashboard/owner/', views.owner_dashboard, name='owner_dashboard'),
    path('dashboard/vet/', views.vet_dashboard, name='vet_dashboard'),
    path('select-account-type/', views.select_account_type, name='select_account_type'),
    path('account/edit/', views.edit_profile, name='edit_profile'),

]
