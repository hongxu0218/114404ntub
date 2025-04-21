from django.contrib import admin

# Register your models here.
from .models import Profile
from django.utils.html import format_html

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_type', 'phone_number', 'is_verified_vet')  # ✅ 顯示驗證欄位
    list_filter = ('account_type', 'is_verified_vet')
    list_editable = ('is_verified_vet',)  # ✅ 可直接編輯

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = '使用者名稱'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def is_staff(self, obj):
        return obj.user.is_staff
    is_staff.boolean = True
    is_staff.short_description = '系統管理員'

    def vet_license_preview(self, obj):
        if obj.vet_license:
            return format_html('<a href="{}" target="_blank">查看檔案</a>', obj.vet_license.url)
        return "-"
    vet_license_preview.short_description = '獸醫證照'
