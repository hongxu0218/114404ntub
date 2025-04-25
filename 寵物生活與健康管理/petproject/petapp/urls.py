from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.register, name='register'),
    path('pets/add/', views.add_pet, name='add_pet'),
    path('pets/', views.pet_list, name='pet_list'),
    path('pets/edit/<int:pet_id>/', views.edit_pet, name='edit_pet'),
    path('pets/delete/<int:pet_id>/', views.delete_pet, name='delete_pet'),
]

# 靜態檔案處理
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)