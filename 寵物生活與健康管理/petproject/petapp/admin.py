from django.contrib import admin
from .models import Profile
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