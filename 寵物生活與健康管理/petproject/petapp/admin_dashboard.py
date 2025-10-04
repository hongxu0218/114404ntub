"""
管理後台儀表板數據分析模組
提供商業智能分析與 KPI 指標
"""

from django.db.models import Count, Sum, Avg, Q, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.auth.models import User
from .models import (
    VetAppointment, Pet, VetDoctor, VetClinic, Post,
    UserProfile, MedicalRecord, VaccineRecord, AdoptionPet,
    Notification, HandoffTicket
)


class DashboardAnalytics:
    """儀表板數據分析類"""

    def __init__(self):
        self.now = timezone.now()
        self.today = self.now.date()
        self.week_ago = self.today - timedelta(days=7)
        self.month_ago = self.today - timedelta(days=30)
        self.year_ago = self.today - timedelta(days=365)

    def get_user_metrics(self):
        """用戶相關指標"""
        total_users = User.objects.count()
        active_users = User.objects.filter(last_login__gte=self.week_ago).count()
        new_users_week = User.objects.filter(date_joined__gte=self.week_ago).count()
        new_users_month = User.objects.filter(date_joined__gte=self.month_ago).count()

        # 用戶增長率
        prev_month_users = User.objects.filter(
            date_joined__lt=self.month_ago,
            date_joined__gte=self.month_ago - timedelta(days=30)
        ).count()
        growth_rate = ((new_users_month - prev_month_users) / prev_month_users * 100) if prev_month_users > 0 else 0

        # 用戶活躍度
        activity_rate = (active_users / total_users * 100) if total_users > 0 else 0

        return {
            'total': total_users,
            'active': active_users,
            'new_week': new_users_week,
            'new_month': new_users_month,
            'growth_rate': round(growth_rate, 2),
            'activity_rate': round(activity_rate, 2)
        }

    def get_appointment_metrics(self):
        """預約相關指標"""
        total = VetAppointment.objects.count()
        today_appointments = VetAppointment.objects.filter(slot__date=self.today).count()
        pending = VetAppointment.objects.filter(status='pending').count()
        confirmed = VetAppointment.objects.filter(status='confirmed').count()
        completed = VetAppointment.objects.filter(status='completed').count()
        cancelled = VetAppointment.objects.filter(status='cancelled').count()

        # 本週預約
        week_appointments = VetAppointment.objects.filter(
            slot__date__gte=self.week_ago
        ).count()

        # 取消率
        cancellation_rate = (cancelled / total * 100) if total > 0 else 0

        # 確認率
        confirmation_rate = ((confirmed + completed) / total * 100) if total > 0 else 0

        # 預約趨勢（過去7天）
        trend = []
        for i in range(7):
            date = self.today - timedelta(days=6-i)
            count = VetAppointment.objects.filter(slot__date=date).count()
            trend.append({
                'date': date.strftime('%m/%d'),
                'count': count
            })

        return {
            'total': total,
            'today': today_appointments,
            'pending': pending,
            'confirmed': confirmed,
            'completed': completed,
            'cancelled': cancelled,
            'week_total': week_appointments,
            'cancellation_rate': round(cancellation_rate, 2),
            'confirmation_rate': round(confirmation_rate, 2),
            'trend': trend
        }

    def get_pet_metrics(self):
        """寵物相關指標"""
        total = Pet.objects.count()
        active = Pet.objects.filter(is_active=True).count()

        # 物種分布
        species_distribution = list(
            Pet.objects.values('species')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        # 年齡分布
        age_groups = {
            '幼年 (0-1歲)': 0,
            '成年 (1-7歲)': 0,
            '老年 (7歲以上)': 0,
            '未知': 0
        }

        for pet in Pet.objects.all():
            if pet.birth_date:
                age = (self.today - pet.birth_date).days / 365
                if age < 1:
                    age_groups['幼年 (0-1歲)'] += 1
                elif age < 7:
                    age_groups['成年 (1-7歲)'] += 1
                else:
                    age_groups['老年 (7歲以上)'] += 1
            else:
                age_groups['未知'] += 1

        return {
            'total': total,
            'active': active,
            'species_distribution': species_distribution,
            'age_distribution': [
                {'label': k, 'value': v} for k, v in age_groups.items()
            ]
        }

    def get_clinic_metrics(self):
        """診所相關指標"""
        total_clinics = VetClinic.objects.count()
        verified_clinics = VetClinic.objects.filter(is_verified=True).count()
        total_doctors = VetDoctor.objects.count()
        verified_doctors = VetDoctor.objects.filter(license_verified_with_moa=True).count()

        # 醫師驗證率
        doctor_verification_rate = (verified_doctors / total_doctors * 100) if total_doctors > 0 else 0

        # 診所驗證率
        clinic_verification_rate = (verified_clinics / total_clinics * 100) if total_clinics > 0 else 0

        # 最活躍診所
        top_clinics = list(
            VetAppointment.objects.values('slot__doctor__clinic__clinic_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        return {
            'total_clinics': total_clinics,
            'verified_clinics': verified_clinics,
            'total_doctors': total_doctors,
            'verified_doctors': verified_doctors,
            'doctor_verification_rate': round(doctor_verification_rate, 2),
            'clinic_verification_rate': round(clinic_verification_rate, 2),
            'top_clinics': top_clinics
        }

    def get_social_metrics(self):
        """社群相關指標"""
        total_posts = Post.objects.count()
        week_posts = Post.objects.filter(created_at__gte=self.week_ago).count()

        # 貼文類型分布
        post_types = list(
            Post.objects.values('post_type')
            .annotate(count=Count('id'))
        )

        # 平均互動率
        posts_with_engagement = Post.objects.annotate(
            total_engagement=F('likes_count') + F('comments_count')
        )
        avg_engagement = posts_with_engagement.aggregate(Avg('total_engagement'))['total_engagement__avg'] or 0

        # 最活躍用戶
        top_users = list(
            Post.objects.values('user__username')
            .annotate(post_count=Count('id'))
            .order_by('-post_count')[:5]
        )

        # 每日發文趨勢
        post_trend = []
        for i in range(7):
            date = self.today - timedelta(days=6-i)
            count = Post.objects.filter(
                created_at__date=date
            ).count()
            post_trend.append({
                'date': date.strftime('%m/%d'),
                'count': count
            })

        return {
            'total_posts': total_posts,
            'week_posts': week_posts,
            'post_types': post_types,
            'avg_engagement': round(avg_engagement, 2),
            'top_users': top_users,
            'trend': post_trend
        }

    def get_health_metrics(self):
        """健康管理指標"""
        total_records = MedicalRecord.objects.count()
        week_records = MedicalRecord.objects.filter(visit_date__gte=self.week_ago).count()

        # 疫苗接種統計
        total_vaccines = VaccineRecord.objects.count()
        upcoming_vaccines = VaccineRecord.objects.filter(
            next_due_date__gte=self.today,
            next_due_date__lte=self.today + timedelta(days=30)
        ).count()
        overdue_vaccines = VaccineRecord.objects.filter(
            next_due_date__lt=self.today
        ).count()

        return {
            'total_records': total_records,
            'week_records': week_records,
            'total_vaccines': total_vaccines,
            'upcoming_vaccines': upcoming_vaccines,
            'overdue_vaccines': overdue_vaccines
        }

    def get_adoption_metrics(self):
        """領養相關指標"""
        total = AdoptionPet.objects.count()
        adopted = AdoptionPet.objects.filter(is_adopted=True).count()
        available = total - adopted

        # 領養成功率
        adoption_rate = (adopted / total * 100) if total > 0 else 0

        # 物種分布
        species_dist = list(
            AdoptionPet.objects.values('species')
            .annotate(count=Count('id'))
        )

        return {
            'total': total,
            'adopted': adopted,
            'available': available,
            'adoption_rate': round(adoption_rate, 2),
            'species_distribution': species_dist
        }

    def get_revenue_metrics(self):
        """營收相關指標（預估）"""
        # 基於完成的預約估算收入
        completed_appointments = VetAppointment.objects.filter(
            status='completed'
        ).count()

        # 假設每次預約平均收入 500 元
        avg_appointment_fee = 500
        estimated_revenue = completed_appointments * avg_appointment_fee

        # 本月收入
        month_appointments = VetAppointment.objects.filter(
            status='completed',
            slot__date__gte=self.month_ago
        ).count()
        month_revenue = month_appointments * avg_appointment_fee

        # 本週收入
        week_appointments = VetAppointment.objects.filter(
            status='completed',
            slot__date__gte=self.week_ago
        ).count()
        week_revenue = week_appointments * avg_appointment_fee

        return {
            'total_revenue': estimated_revenue,
            'month_revenue': month_revenue,
            'week_revenue': week_revenue,
            'avg_per_appointment': avg_appointment_fee
        }

    def get_system_health(self):
        """系統健康度指標"""
        # 通知統計
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(is_read=False).count()

        # 工單統計
        open_tickets = HandoffTicket.objects.filter(is_open=True).count()
        total_tickets = HandoffTicket.objects.count()

        # 系統活躍度
        active_users_today = User.objects.filter(last_login__date=self.today).count()

        return {
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'open_tickets': open_tickets,
            'total_tickets': total_tickets,
            'active_users_today': active_users_today
        }

    def get_visit_metrics(self):
        """網站訪問統計（基於 Cache）"""
        from django.core.cache import cache

        # 總訪問數
        total_visits = cache.get('visits_total', 0)

        # 今日訪問數（去重 session）
        today_sessions_key = f'visits_sessions_{self.today}'
        today_sessions = cache.get(today_sessions_key, set())
        today_visits = len(today_sessions)

        # 本週訪問數（去重 session，計算過去7天）
        week_sessions = set()
        for i in range(7):
            date = self.today - timedelta(days=i)
            date_sessions_key = f'visits_sessions_{date}'
            date_sessions = cache.get(date_sessions_key, set())
            week_sessions.update(date_sessions)
        week_visits = len(week_sessions)

        # 上週訪問數（7-14天前）
        last_week_sessions = set()
        for i in range(7, 14):
            date = self.today - timedelta(days=i)
            date_sessions_key = f'visits_sessions_{date}'
            date_sessions = cache.get(date_sessions_key, set())
            last_week_sessions.update(date_sessions)
        last_week_visits = len(last_week_sessions)

        # 計算週增長率
        growth_rate = 0
        if last_week_visits > 0:
            growth_rate = ((week_visits - last_week_visits) / last_week_visits) * 100
        elif week_visits > 0:
            growth_rate = 100

        # 每日訪問趨勢（過去7天）
        visit_trend = []
        for i in range(7):
            date = self.today - timedelta(days=6-i)
            date_sessions_key = f'visits_sessions_{date}'
            date_sessions = cache.get(date_sessions_key, set())
            visit_trend.append({
                'date': date.strftime('%m/%d'),
                'count': len(date_sessions)
            })

        # 平均日訪問量
        avg_daily_visits = week_visits / 7 if week_visits > 0 else 0

        return {
            'total_visits': total_visits,
            'today_visits': today_visits,
            'week_visits': week_visits,
            'growth_rate': round(growth_rate, 1),
            'avg_daily_visits': round(avg_daily_visits, 1),
            'unique_visitors_week': week_visits,
            'registered_visits': 0,  # Cache 版本不追蹤此數據
            'guest_visits': 0,  # Cache 版本不追蹤此數據
            'trend': visit_trend
        }

    def get_complete_dashboard_data(self):
        """獲取完整儀表板數據"""
        return {
            'user_metrics': self.get_user_metrics(),
            'appointment_metrics': self.get_appointment_metrics(),
            'pet_metrics': self.get_pet_metrics(),
            'clinic_metrics': self.get_clinic_metrics(),
            'social_metrics': self.get_social_metrics(),
            'health_metrics': self.get_health_metrics(),
            'adoption_metrics': self.get_adoption_metrics(),
            'revenue_metrics': self.get_revenue_metrics(),
            'system_health': self.get_system_health(),
            'visit_metrics': self.get_visit_metrics(),
            'last_updated': self.now.strftime('%Y-%m-%d %H:%M:%S')
        }
