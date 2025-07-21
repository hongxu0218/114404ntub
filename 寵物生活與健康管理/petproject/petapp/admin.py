from django.contrib import admin
from .models import Profile,VetDoctor,VetClinic
from django.utils.html import format_html

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'full_name', 'email', 'account_type', 'phone_number'
    )
    list_filter = ('account_type',)
    search_fields = ('user__username', 'user__first_name', 'user__email')
    list_editable = ()

    def get_fieldsets(self, request, obj=None):
        return (
            ('基本資料', {
                'fields': ('user', 'account_type', 'phone_number')
            }),
        )

    def full_name(self, obj):
        """顯示完整姓名"""
        if obj.user.first_name:
            return obj.user.first_name
        elif obj.user.last_name:
            return obj.user.last_name
        else:
            return obj.user.username
    full_name.short_description = '姓名'

    def email(self, obj):
        return obj.user.email
    email.short_description = '電子郵件'
    

    def is_staff_display(self, obj):
        return '✔️' if obj.user.is_staff else '❌'
    is_staff_display.short_description = '系統管理員'

@admin.register(VetDoctor)
class VetDoctorAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'clinic', 'vet_license_number', 'license_verified_display', 
        'moa_license_type', 'is_active'
    )
    list_filter = ('license_verified_with_moa', 'moa_license_type', 'is_active', 'clinic')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'vet_license_number')
    
    def license_verified_display(self, obj):
        if obj.license_verified_with_moa:
            return "✅ 已驗證"
        return "⏳ 未驗證"
    license_verified_display.short_description = '執照驗證狀態'
    
    actions = ['verify_selected_licenses']
    
    def verify_selected_licenses(self, request, queryset):
        """批量驗證選中的獸醫師執照"""
        success_count = 0
        
        for vet_doctor in queryset:
            if vet_doctor.vet_license_number:
                success, message = vet_doctor.verify_vet_license_with_moa()
                if success:
                    success_count += 1
        
        self.message_user(request, f"成功驗證 {success_count} 位獸醫師執照")
    
    verify_selected_licenses.short_description = "驗證選中的獸醫師執照"

@admin.register(VetClinic)
class VetClinicAdmin(admin.ModelAdmin):
    list_display = ('clinic_name', 'license_number', 'is_verified', 'verification_date')
    list_filter = ('is_verified', 'moa_county')
    search_fields = ('clinic_name', 'license_number')
    readonly_fields = ('verification_date', 'created_at', 'updated_at')

# 安全地取消註冊，如果有被註冊的話才移除
for model in [EmailAddress, SocialAccount, SocialApp, SocialToken]:
    if model in admin.site._registry:
        admin.site.unregister(model)