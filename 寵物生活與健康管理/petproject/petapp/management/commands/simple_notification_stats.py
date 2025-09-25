# petapp/management/commands/simple_notification_stats.py
"""
簡化版通知統計命令
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from petapp.models import Notification
from datetime import timedelta


class Command(BaseCommand):
    help = '顯示通知系統統計信息'

    def handle(self, *args, **options):
        self.stdout.write("通知系統統計報告")
        self.stdout.write("=" * 40)

        # 基本統計
        total_notifications = Notification.objects.count()
        total_users = User.objects.filter(notifications__isnull=False).distinct().count()
        unread_notifications = Notification.objects.filter(is_read=False).count()
        read_notifications = total_notifications - unread_notifications

        self.stdout.write(f"總通知數: {total_notifications}")
        self.stdout.write(f"有通知的用戶數: {total_users}")
        self.stdout.write(f"未讀通知: {unread_notifications}")
        self.stdout.write(f"已讀通知: {read_notifications}")

        if total_notifications > 0:
            unread_rate = unread_notifications / total_notifications * 100
            self.stdout.write(f"未讀率: {unread_rate:.1f}%")

        # 按類型統計
        self.stdout.write("\n按類型統計:")
        type_stats = Notification.objects.values('notification_type').annotate(
            count=models.Count('id')
        ).order_by('-count')

        for stat in type_stats:
            notif_type = dict(Notification.NOTIFICATION_TYPES).get(
                stat['notification_type'], stat['notification_type']
            )
            self.stdout.write(f"  {notif_type}: {stat['count']}")

        # 時間統計
        now = timezone.now()
        today_count = Notification.objects.filter(created_at__gte=now - timedelta(days=1)).count()
        week_count = Notification.objects.filter(created_at__gte=now - timedelta(days=7)).count()
        month_count = Notification.objects.filter(created_at__gte=now - timedelta(days=30)).count()

        self.stdout.write(f"\n時間分布:")
        self.stdout.write(f"  今天: {today_count}")
        self.stdout.write(f"  本週: {week_count}")
        self.stdout.write(f"  本月: {month_count}")

        # 用戶通知Top 10
        self.stdout.write(f"\n用戶通知排行榜 (Top 10):")
        user_stats = User.objects.filter(notifications__isnull=False).annotate(
            notification_count=models.Count('notifications')
        ).order_by('-notification_count')[:10]

        for i, user in enumerate(user_stats, 1):
            unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
            self.stdout.write(f"  {i:2d}. {user.username}: {user.notification_count} 個 (未讀: {unread_count})")

        self.stdout.write("\n統計完成")