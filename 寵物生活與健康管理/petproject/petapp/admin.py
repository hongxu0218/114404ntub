from django.contrib import admin
from .models import Profile,AdoptionAnimal, AdoptionShelter, AdoptionFavorite, AdoptionApplication

from django.utils.html import format_html

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'last_name', 'first_name', 'email', 'account_type',
        'phone_number', 'is_verified_display'
    )
    list_filter = ('account_type', 'is_verified_vet')
    list_editable = ()  # 不要直接編輯 is_verified_vet，因為飼主不應看到

    def is_verified_display(self, obj):
        if obj.account_type == 'vet':
            return obj.is_verified_vet
        return "-"
    is_verified_display.short_description = '獸醫身分已驗證'
    is_verified_display.admin_order_field = 'is_verified_vet'

    def get_fieldsets(self, request, obj=None):
        if obj and obj.account_type == 'owner':
            return (
                ('基本資料', {
                    'fields': ('user', 'account_type', 'phone_number')
                }),
            )
        else:
            return (
                ('基本資料', {
                    'fields': ('user', 'account_type', 'phone_number')
                }),
                ('獸醫資料', {
                    'fields': ('vet_license_preview', 'vet_license_city', 'clinic_name', 'clinic_address','is_verified_vet')
                }),
            )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and obj.account_type == 'owner':
            return readonly_fields + ('vet_license', 'vet_license_city', 'is_verified_vet')
        else:
            return readonly_fields + ('vet_license_preview',)

    def vet_license_preview(self, obj):
        if obj.vet_license:
            return format_html('<a href="{}" target="_blank">查看檔案</a>', obj.vet_license.url)
        return "-"
    vet_license_preview.short_description = '獸醫證照'

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = '使用者名稱'

    def last_name(self, obj):
        return obj.user.last_name
    last_name.short_description = '姓氏'

    def first_name(self, obj):
        return obj.user.first_name
    first_name.short_description = '名字'

    def email(self, obj):
        return obj.user.email
    email.short_description = '電子郵件'

    def is_staff_display(self, obj):
        return '✔️' if obj.user.is_staff else '❌'
    is_staff_display.short_description = '系統管理員'

# 安全地取消註冊，如果有被註冊的話才移除
for model in [EmailAddress, SocialAccount, SocialApp, SocialToken]:
    if model in admin.site._registry:
        admin.site.unregister(model)


@admin.register(AdoptionShelter)
class AdoptionShelterAdmin(admin.ModelAdmin):
    list_display = ['shelter_code', 'shelter_name', 'phone', 'created_at']
    search_fields = ['shelter_name', 'address']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(AdoptionAnimal)
class AdoptionAnimalAdmin(admin.ModelAdmin):
    list_display = [
        'animal_id', 'animal_title', 'animal_kind', 'animal_sex', 
        'animal_status', 'shelter_name', 'image_preview', 'animal_update'
    ]
    list_filter = [
        'animal_kind', 'animal_sex', 'animal_bodytype', 'animal_status',
        'animal_sterilization', 'animal_bacterin', 'shelter', 'is_active'
    ]
    search_fields = [
        'animal_id', 'animal_title', 'animal_kind', 'animal_colour', 
        'shelter_name', 'animal_foundplace'
    ]
    readonly_fields = [
        'animal_id', 'created_at', 'updated_at', 'image_preview_large'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': (
                'animal_id', 'animal_title', 'is_active', 'image_preview_large'
            )
        }),
        ('動物詳情', {
            'fields': (
                'animal_kind', 'animal_sex', 'animal_bodytype', 'animal_colour',
                'animal_age', 'animal_subid', 'animal_sterilization', 'animal_bacterin'
            )
        }),
        ('狀態與地點', {
            'fields': (
                'animal_status', 'animal_place', 'animal_foundplace', 'shelter'
            )
        }),
        ('收容所資訊', {
            'fields': (
                'shelter_pkid', 'shelter_name', 'shelter_address', 'shelter_tel'
            )
        }),
        ('時間資訊', {
            'fields': (
                'animal_opendate', 'animal_closeddate', 'animal_update',
                'animal_createtime', 'created_at', 'updated_at'
            )
        }),
        ('圖片與備註', {
            'fields': (
                'album_file', 'album_update', 'animal_remark', 'animal_caption'
            )
        }),
    )
    
    actions = ['mark_as_adopted', 'mark_as_available', 'deactivate_animals']
    
    def image_preview(self, obj):
        if obj.album_file:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />',
                obj.album_file
            )
        return "無圖片"
    image_preview.short_description = "預覽"
    
    def image_preview_large(self, obj):
        if obj.album_file:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                obj.album_file
            )
        return "無圖片"
    image_preview_large.short_description = "圖片預覽"
    
    def mark_as_adopted(self, request, queryset):
        updated = queryset.update(animal_status='已認養')
        self.message_user(request, f'已將 {updated} 隻動物標記為已認養')
    mark_as_adopted.short_description = "標記為已認養"
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(animal_status='開放認養')
        self.message_user(request, f'已將 {updated} 隻動物標記為開放認養')
    mark_as_available.short_description = "標記為開放認養"
    
    def deactivate_animals(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'已停用 {updated} 隻動物')
    deactivate_animals.short_description = "停用動物"

@admin.register(AdoptionFavorite)
class AdoptionFavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'animal', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']

@admin.register(AdoptionApplication)
class AdoptionApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'applicant_name', 'animal', 'status', 'created_at'
    ]
    list_filter = ['status', 'family_consent', 'created_at']
    search_fields = ['applicant_name', 'applicant_email', 'animal__animal_title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('申請資訊', {
            'fields': ('animal', 'applicant', 'status')
        }),
        ('申請人資料', {
            'fields': (
                'applicant_name', 'applicant_phone', 'applicant_email', 
                'applicant_address'
            )
        }),
        ('認養相關', {
            'fields': (
                'experience', 'housing_type', 'family_consent'
            )
        }),
        ('管理資訊', {
            'fields': (
                'admin_notes', 'created_at', 'updated_at'
            )
        }),
    )
    
    actions = ['approve_applications', 'reject_applications']
    
    def approve_applications(self, request, queryset):
        updated = queryset.update(status='APPROVED')
        self.message_user(request, f'已通過 {updated} 個申請')
    approve_applications.short_description = "通過申請"
    
    def reject_applications(self, request, queryset):
        updated = queryset.update(status='REJECTED')
        self.message_user(request, f'已拒絕 {updated} 個申請')
    reject_applications.short_description = "拒絕申請"