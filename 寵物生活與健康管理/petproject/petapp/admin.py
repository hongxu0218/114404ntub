from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import (
    Profile, VetDoctor, VetClinic, Pet, PetTag,
    UserProfile, Follow, Post, PostMedia, Like, Comment, CommentLike,
    VetAppointment, AppointmentSlot, VetSchedule, MedicalRecord,
    VaccineRecord, DewormRecord, DailyRecord, AdoptionPet,
    AnimalDrug, HandoffTicket, HandoffMessage, Notification,
    ScheduleChangeRequest, EnhancedVetSchedule
)

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

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        extra_context['verified_count'] = VetDoctor.objects.filter(license_verified_with_moa=True).count()
        extra_context['unverified_count'] = VetDoctor.objects.filter(license_verified_with_moa=False).count()
        extra_context['active_count'] = VetDoctor.objects.filter(is_active=True).count()

        return super().changelist_view(request, extra_context=extra_context)

@admin.register(VetClinic)
class VetClinicAdmin(admin.ModelAdmin):
    list_display = ('clinic_name', 'license_number', 'is_verified', 'verification_date')
    list_filter = ('is_verified', 'moa_county')
    search_fields = ('clinic_name', 'license_number')
    readonly_fields = ('verification_date', 'created_at', 'updated_at')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        week_ago = timezone.now() - timedelta(days=7)

        extra_context['verified_count'] = VetClinic.objects.filter(is_verified=True).count()
        extra_context['unverified_count'] = VetClinic.objects.filter(is_verified=False).count()
        extra_context['new_week'] = VetClinic.objects.filter(created_at__gte=week_ago).count()

        return super().changelist_view(request, extra_context=extra_context)

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

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        today = timezone.now().date()
        week_ago = timezone.now() - timedelta(days=7)
        month_ago = timezone.now() - timedelta(days=30)

        # 基本統計
        extra_context['today_count'] = Post.objects.filter(created_at__date=today).count()
        extra_context['week_count'] = Post.objects.filter(created_at__gte=week_ago).count()

        from django.db.models import Avg, F, Sum
        avg_engagement = Post.objects.aggregate(
            avg=Avg(F('likes_count') + F('comments_count'))
        )['avg']
        extra_context['avg_engagement'] = round(avg_engagement) if avg_engagement else 0

        # 社群數據統計
        social_stats = Post.objects.aggregate(
            total_likes=Sum('likes_count'),
            total_comments=Sum('comments_count'),
            total_shares=Sum('shares_count')
        )
        extra_context['total_likes'] = social_stats['total_likes'] or 0
        extra_context['total_comments'] = social_stats['total_comments'] or 0
        extra_context['total_shares'] = social_stats['total_shares'] or 0

        # 計算成長率（本週 vs 上週）
        two_weeks_ago = timezone.now() - timedelta(days=14)
        last_week_posts = Post.objects.filter(created_at__gte=two_weeks_ago, created_at__lt=week_ago)
        this_week_posts = Post.objects.filter(created_at__gte=week_ago)

        last_week_stats = last_week_posts.aggregate(
            likes=Sum('likes_count'),
            comments=Sum('comments_count'),
            shares=Sum('shares_count')
        )
        this_week_stats = this_week_posts.aggregate(
            likes=Sum('likes_count'),
            comments=Sum('comments_count'),
            shares=Sum('shares_count')
        )

        def calc_growth(current, previous):
            if not previous or previous == 0:
                return 100 if current and current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)

        extra_context['likes_growth'] = calc_growth(
            this_week_stats['likes'] or 0,
            last_week_stats['likes'] or 0
        )
        extra_context['comments_growth'] = calc_growth(
            this_week_stats['comments'] or 0,
            last_week_stats['comments'] or 0
        )
        extra_context['shares_growth'] = calc_growth(
            this_week_stats['shares'] or 0,
            last_week_stats['shares'] or 0
        )

        # 準備過去30天的趨勢數據
        import json
        from collections import defaultdict

        # 獲取過去30天的數據
        daily_data = defaultdict(lambda: {'likes': 0, 'comments': 0, 'shares': 0, 'posts': 0})
        posts_30_days = Post.objects.filter(created_at__gte=month_ago)

        for post in posts_30_days:
            date_key = post.created_at.date().isoformat()
            daily_data[date_key]['likes'] += post.likes_count or 0
            daily_data[date_key]['comments'] += post.comments_count or 0
            daily_data[date_key]['shares'] += post.shares_count or 0
            daily_data[date_key]['posts'] += 1

        # 生成完整的30天數據（包含沒有數據的日期）
        from datetime import timedelta as td
        dates = []
        likes_data = []
        comments_data = []
        shares_data = []
        posts_data = []

        for i in range(30):
            date = (timezone.now().date() - td(days=29-i)).isoformat()
            dates.append(date)
            likes_data.append(daily_data[date]['likes'])
            comments_data.append(daily_data[date]['comments'])
            shares_data.append(daily_data[date]['shares'])
            posts_data.append(daily_data[date]['posts'])

        extra_context['chart_dates'] = json.dumps(dates)
        extra_context['chart_likes'] = json.dumps(likes_data)
        extra_context['chart_comments'] = json.dumps(comments_data)
        extra_context['chart_shares'] = json.dumps(shares_data)
        extra_context['chart_posts'] = json.dumps(posts_data)

        return super().changelist_view(request, extra_context=extra_context)


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
    list_display = ('user', 'post', 'content_preview', 'likes_count', 'created_at')
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


# ===== 預約與排班管理 =====

@admin.register(VetAppointment)
class VetAppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'pet', 'owner', 'slot_info', 'status_badge', 'reason_preview', 'is_expired_display', 'created_at')
    list_filter = ('status', 'booking_type', 'slot__date')
    search_fields = ('pet__name', 'owner__username', 'owner__first_name', 'reason', 'contact_phone')
    readonly_fields = ('created_at', 'updated_at', 'is_expired_display')
    # 移除 date_hierarchy 避免時區問題

    fieldsets = (
        ('預約資訊', {
            'fields': ('pet', 'owner', 'slot', 'status', 'booking_type')
        }),
        ('預約詳情', {
            'fields': ('reason', 'notes', 'cancel_reason')
        }),
        ('聯絡資訊', {
            'fields': ('contact_phone', 'contact_email')
        }),
        ('通知狀態', {
            'fields': ('clinic_notified', 'reminder_sent')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at', 'is_expired_display')
        }),
    )

    def slot_info(self, obj):
        return f"{obj.slot.date} {obj.slot.start_time}-{obj.slot.end_time}"
    slot_info.short_description = '時段'

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'confirmed': '#28a745',
            'completed': '#17a2b8',
            'cancelled': '#dc3545',
            'no_show': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = '狀態'

    def reason_preview(self, obj):
        return obj.reason[:30] + '...' if len(obj.reason) > 30 else obj.reason
    reason_preview.short_description = '預約原因'

    def is_expired_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">是</span>')
        return format_html('<span style="color: green;">否</span>')
    is_expired_display.short_description = '已過期'

    actions = ['mark_as_confirmed', 'mark_as_cancelled', 'mark_as_completed']

    def mark_as_confirmed(self, request, queryset):
        count = queryset.filter(status='pending').update(status='confirmed')
        self.message_user(request, f'已確認 {count} 個預約')
    mark_as_confirmed.short_description = '標記為已確認'

    def mark_as_cancelled(self, request, queryset):
        count = queryset.exclude(status__in=['completed', 'cancelled']).update(
            status='cancelled',
            cancel_reason='管理員取消'
        )
        self.message_user(request, f'已取消 {count} 個預約')
    mark_as_cancelled.short_description = '標記為已取消'

    def mark_as_completed(self, request, queryset):
        count = queryset.filter(status='confirmed').update(status='completed')
        self.message_user(request, f'已完成 {count} 個預約')
    mark_as_completed.short_description = '標記為已完成'


@admin.register(VetSchedule)
class VetScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'weekday_display', 'time_range', 'is_active', 'created_at')
    list_filter = ('is_active', 'weekday', 'created_at')
    search_fields = ('doctor__user__username', 'notes')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本資訊', {
            'fields': ('doctor', 'weekday')
        }),
        ('時間設定', {
            'fields': ('start_time', 'end_time', 'appointment_duration')
        }),
        ('狀態與備註', {
            'fields': ('is_active', 'notes', 'max_appointments_per_slot')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def weekday_display(self, obj):
        days = ['一', '二', '三', '四', '五', '六', '日']
        return f'週{days[obj.weekday]}'
    weekday_display.short_description = '星期'

    def time_range(self, obj):
        return f"{obj.start_time}-{obj.end_time}"
    time_range.short_description = '時間範圍'


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'pet', 'attending_vet', 'visit_date', 'diagnosis_preview', 'treatment_preview')
    list_filter = ('attending_vet',)
    search_fields = ('pet__name', 'attending_vet__user__username', 'diagnosis', 'treatment')
    # 移除 date_hierarchy 避免時區問題
    readonly_fields = ('visit_date',)

    fieldsets = (
        ('基本資訊', {
            'fields': ('pet', 'attending_vet', 'recorded_by', 'visit_date', 'clinic_location')
        }),
        ('診斷與治療', {
            'fields': ('diagnosis', 'treatment', 'prescription')
        }),
        ('備註', {
            'fields': ('notes',)
        }),
    )

    def diagnosis_preview(self, obj):
        return obj.diagnosis[:50] + '...' if len(obj.diagnosis) > 50 else obj.diagnosis
    diagnosis_preview.short_description = '診斷'

    def treatment_preview(self, obj):
        return obj.treatment[:50] + '...' if len(obj.treatment) > 50 else obj.treatment
    treatment_preview.short_description = '治療'


@admin.register(VaccineRecord)
class VaccineRecordAdmin(admin.ModelAdmin):
    list_display = ('pet', 'name', 'date', 'next_due_date', 'vet', 'is_upcoming')
    list_filter = ('vet',)
    search_fields = ('pet__name', 'name', 'location')
    # 移除 date_hierarchy 避免時區問題

    def is_upcoming(self, obj):
        if obj.next_due_date:
            days_until = (obj.next_due_date - timezone.now().date()).days
            if days_until <= 7 and days_until >= 0:
                return format_html('<span style="color: orange;">本週到期</span>')
            elif days_until < 0:
                return format_html('<span style="color: red;">已逾期</span>')
        return '正常'
    is_upcoming.short_description = '提醒狀態'


@admin.register(AdoptionPet)
class AdoptionPetAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'gender', 'owner', 'is_adopted', 'is_publish', 'posted_date')
    list_filter = ('is_adopted', 'is_publish', 'species', 'gender')
    search_fields = ('name', 'breed', 'owner__username', 'physical_condition')
    # 移除 date_hierarchy 避免時區問題
    readonly_fields = ('posted_date',)

    fieldsets = (
        ('基本資訊', {
            'fields': ('owner', 'name', 'species', 'breed', 'gender')
        }),
        ('詳細資訊', {
            'fields': ('birth_date', 'weight', 'sterilization_status', 'chip')
        }),
        ('健康狀況', {
            'fields': ('vaccine', 'physical_condition', 'feature')
        }),
        ('聯絡資訊', {
            'fields': ('phone', 'line_id', 'adopt_place')
        }),
        ('領養狀態', {
            'fields': ('is_adopted', 'is_publish')
        }),
        ('媒體', {
            'fields': ('adopt_picture1', 'adopt_picture2', 'adopt_picture3', 'adopt_picture4')
        }),
        ('系統資訊', {
            'fields': ('posted_date',)
        }),
    )

    actions = ['mark_as_adopted', 'mark_as_published']

    def mark_as_adopted(self, request, queryset):
        count = queryset.update(is_adopted=True)
        self.message_user(request, f'已標記 {count} 隻寵物為已領養')
    mark_as_adopted.short_description = '標記為已領養'

    def mark_as_published(self, request, queryset):
        count = queryset.update(is_publish=True)
        self.message_user(request, f'已發布 {count} 隻寵物')
    mark_as_published.short_description = '標記為已發布'


@admin.register(AnimalDrug)
class AnimalDrugAdmin(admin.ModelAdmin):
    list_display = ('license_number', 'chinese_name', 'english_name', 'manufacturer', 'applicant', 'is_active')
    list_filter = ('is_active', 'dosage_form', 'target_animals')
    search_fields = ('license_number', 'chinese_name', 'english_name', 'manufacturer', 'applicant')
    readonly_fields = ('sync_date', 'created_at', 'updated_at')

    fieldsets = (
        ('許可證資訊', {
            'fields': ('license_number', 'is_active')
        }),
        ('產品資訊', {
            'fields': ('chinese_name', 'english_name', 'dosage_form', 'packaging')
        }),
        ('廠商資訊', {
            'fields': ('manufacturer', 'applicant')
        }),
        ('藥物特性', {
            'fields': ('indications', 'active_ingredients', 'target_animals')
        }),
        ('系統資訊', {
            'fields': ('sync_date', 'created_at', 'updated_at')
        }),
    )


class HandoffMessageInline(admin.TabularInline):
    """客服訊息內聯管理"""
    model = HandoffMessage
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('sender', 'text', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # 允許新增訊息（客服可以回覆）
        return True


@admin.register(HandoffTicket)
class HandoffTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_key', 'name', 'contact', 'channel', 'status_badge', 'message_count', 'created_at')
    list_filter = ('is_open', 'channel')
    search_fields = ('session_key', 'name', 'contact')
    readonly_fields = ('created_at', 'session_key')
    inlines = [HandoffMessageInline]
    # 移除 date_hierarchy 以避免時區問題

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        today = timezone.now().date()

        extra_context['open_count'] = HandoffTicket.objects.filter(is_open=True).count()
        extra_context['closed_count'] = HandoffTicket.objects.filter(is_open=False).count()
        extra_context['today_count'] = HandoffTicket.objects.filter(created_at__date=today).count()

        return super().changelist_view(request, extra_context=extra_context)

    fieldsets = (
        ('基本資訊', {
            'fields': ('session_key', 'name', 'contact', 'channel')
        }),
        ('狀態', {
            'fields': ('is_open',)
        }),
        ('系統資訊', {
            'fields': ('created_at',)
        }),
    )

    def status_badge(self, obj):
        if obj.is_open:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">開啟中</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">已關閉</span>'
        )
    status_badge.short_description = '狀態'

    def message_count(self, obj):
        count = obj.messages.count()
        return format_html(
            '<span style="background-color: #f97316; color: white; padding: 3px 10px; border-radius: 12px; font-weight: 600;">{}</span>',
            count
        )
    message_count.short_description = '訊息數'

    actions = ['close_tickets', 'reopen_tickets']

    def close_tickets(self, request, queryset):
        count = queryset.update(is_open=False)
        self.message_user(request, f'已關閉 {count} 個工單')
    close_tickets.short_description = '關閉工單'

    def reopen_tickets(self, request, queryset):
        count = queryset.update(is_open=True)
        self.message_user(request, f'已重新開啟 {count} 個工單')
    reopen_tickets.short_description = '重新開啟工單'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'notification_type', 'title', 'message_preview', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'title', 'message')
    readonly_fields = ('created_at',)
    # 移除 date_hierarchy 避免時區問題

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = '訊息'

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f'已標記 {count} 則通知為已讀')
    mark_as_read.short_description = '標記為已讀'

    def mark_as_unread(self, request, queryset):
        count = queryset.update(is_read=False)
        self.message_user(request, f'已標記 {count} 則通知為未讀')
    mark_as_unread.short_description = '標記為未讀'


# ===== 自訂後台首頁 =====

# 覆寫 admin site 的 index 方法
from django.contrib import admin as django_admin

original_index = django_admin.site.index

def custom_index(self, request, extra_context=None):
    from .admin_dashboard import DashboardAnalytics
    import traceback

    extra_context = extra_context or {}

    # 獲取完整儀表板數據
    try:
        analytics = DashboardAnalytics()
        dashboard_data = analytics.get_complete_dashboard_data()
        extra_context['dashboard_data'] = dashboard_data
        print(f"Dashboard data loaded successfully")
    except Exception as e:
        print(f"Dashboard data error: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        extra_context['dashboard_data'] = None

    return original_index(request, extra_context)

# 應用自訂 index
django_admin.site.index = custom_index.__get__(django_admin.site, django_admin.AdminSite)

# 自訂後台標題
django_admin.site.site_header = '🐾 PawDay管理系統 - 後台'
django_admin.site.site_title = '後台管理中心'
django_admin.site.index_title = ''


# 自訂用戶管理
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

class CustomUserAdmin(BaseUserAdmin):
    """自訂用戶管理 - 提供統計數據與角色識別"""

    list_display = ('username', 'email', 'first_name', 'last_name', 'user_role_display', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def user_role_display(self, obj):
        """顯示用戶角色"""
        roles = []

        # 檢查是否為超級管理員
        if obj.is_superuser:
            roles.append('🔑 超級管理員')

        # 檢查是否為診所管理員
        if hasattr(obj, 'managed_clinic') and obj.managed_clinic:
            roles.append(f'🏥 診所管理員 ({obj.managed_clinic.clinic_name})')

        # 檢查是否為獸醫師
        if hasattr(obj, 'profile'):
            profile = obj.profile
            if profile.account_type == 'veterinarian':
                roles.append('👨‍⚕️ 獸醫師')
            elif profile.account_type == 'clinic_admin' and not (hasattr(obj, 'managed_clinic') and obj.managed_clinic):
                roles.append('🏥 診所管理員')
            elif profile.account_type == 'owner':
                roles.append('🐾 飼主')

        # 檢查是否為後台管理員
        if obj.is_staff and not obj.is_superuser:
            roles.append('👤 後台管理員')

        if not roles:
            roles.append('👤 一般用戶')

        return format_html('<br>'.join(roles))

    user_role_display.short_description = '用戶角色'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # 計算統計數據
        week_ago = timezone.now() - timedelta(days=7)

        extra_context['active_count'] = User.objects.filter(is_active=True).count()
        extra_context['staff_count'] = User.objects.filter(is_staff=True).count()
        extra_context['new_week'] = User.objects.filter(date_joined__gte=week_ago).count()

        # 診所管理員統計
        extra_context['clinic_admin_count'] = VetClinic.objects.filter(clinic_admin__isnull=False).count()

        return super().changelist_view(request, extra_context=extra_context)

# 取消註冊原有的 UserAdmin，註冊新的
django_admin.site.unregister(User)
django_admin.site.register(User, CustomUserAdmin)


# 網站訪問記錄已改用 Cache 實作，不再使用資料庫 Model