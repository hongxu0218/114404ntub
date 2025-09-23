from django.contrib import admin
from .models import (
    Profile, VetDoctor, VetClinic, Pet, PetTag,
    UserProfile, Follow, Post, PostMedia, Like, Comment, CommentLike
)
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
        return 'Yes' if obj.user.is_staff else 'No'
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
            return "已驗證"
        return "未驗證"
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

@admin.register(PetTag)
class PetTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'tag_type', 'color', 'is_system_tag', 'created_at')
    list_filter = ('tag_type', 'color', 'is_system_tag')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('name', 'tag_type', 'color')
        }),
        ('詳細資訊', {
            'fields': ('description', 'is_system_tag', 'created_at')
        }),
    )

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'species', 'age_display', 'has_recent_visit', 'is_active')
    list_filter = ('species', 'gender', 'is_active', 'tags')
    search_fields = ('name', 'owner__username', 'owner__first_name', 'chip')
    filter_horizontal = ('tags',)
    readonly_fields = ('age_display', 'has_recent_visit', 'created_at', 'updated_at')
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('owner', 'name', 'species', 'breed', 'gender')
        }),
        ('詳細資訊', {
            'fields': ('birth_date', 'age_display', 'weight', 'sterilization_status', 'chip')
        }),
        ('醫療資訊', {
            'fields': ('tags', 'last_visit_date', 'has_recent_visit', 'medical_notes')
        }),
        ('緊急聯絡', {
            'fields': ('emergency_contact', 'emergency_phone')
        }),
        ('其他', {
            'fields': ('feature', 'picture', 'is_active')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at')
        }),
    )

# 安全地取消註冊，如果有被註冊的話才移除
for model in [EmailAddress, SocialAccount, SocialApp, SocialToken]:
    if model in admin.site._registry:
        admin.site.unregister(model)


# ===== 社群媒體模組管理 =====

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'followers_count', 'following_count', 'posts_count', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('followers_count', 'following_count', 'posts_count', 'created_at', 'updated_at')

    fieldsets = (
        ('基本資訊', {
            'fields': ('user', 'bio')
        }),
        ('媒體', {
            'fields': ('avatar', 'banner')
        }),
        ('統計', {
            'fields': ('followers_count', 'following_count', 'posts_count')
        }),
        ('時間', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('follower__username', 'following__username')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_preview', 'post_type', 'likes_count', 'comments_count', 'is_repost', 'created_at')
    list_filter = ('post_type', 'is_repost', 'created_at')
    search_fields = ('user__username', 'content')
    readonly_fields = ('likes_count', 'comments_count', 'shares_count', 'created_at', 'updated_at')

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '內容預覽'


class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 0


@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    list_display = ('post', 'media_type', 'order', 'created_at')
    list_filter = ('media_type', 'created_at')
    search_fields = ('post__user__username', 'post__content')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__content')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'content_preview', 'parent_comment', 'likes_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'content', 'post__content')
    readonly_fields = ('likes_count', 'created_at', 'updated_at')

    def content_preview(self, obj):
        return obj.content[:30] + '...' if len(obj.content) > 30 else obj.content
    content_preview.short_description = '內容預覽'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'comment__content')