# petapp/management/commands/notification_maintenance.py
"""
通知系統維護命令
自動清理、聚合和優化通知數據
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.db import models
from petapp.notification_optimization import NotificationManager
from petapp.models import Notification
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '執行通知系統維護任務'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='清理舊通知'
        )
        parser.add_argument(
            '--aggregate',
            action='store_true',
            help='聚合相似通知'
        )
        parser.add_argument(
            '--optimize',
            action='store_true',
            help='優化數據庫'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='執行所有維護任務'
        )
        parser.add_argument(
            '--user-limit',
            type=int,
            default=100,
            help='每次處理的用戶數量限制'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='顯示統計信息'
        )

    def handle(self, *args, **options):
        self.stdout.write("開始通知系統維護...")

        if options['stats'] or options['all']:
            self.show_statistics()

        if options['cleanup'] or options['all']:
            self.cleanup_notifications(options['user_limit'])

        if options['aggregate'] or options['all']:
            self.aggregate_notifications(options['user_limit'])

        if options['optimize'] or options['all']:
            self.optimize_database()

        self.stdout.write(self.style.SUCCESS("通知系統維護完成"))

    def show_statistics(self):
        """顯示通知系統統計信息"""
        self.stdout.write("\n通知系統統計信息")
        self.stdout.write("=" * 50)

        # 總體統計
        total_notifications = Notification.objects.count()
        total_users = User.objects.filter(notifications__isnull=False).distinct().count()
        unread_notifications = Notification.objects.filter(is_read=False).count()
        read_notifications = total_notifications - unread_notifications

        self.stdout.write(f"總通知數: {total_notifications:,}")
        self.stdout.write(f"有通知用戶數: {total_users:,}")
        self.stdout.write(f"未讀通知: {unread_notifications:,} ({unread_notifications/total_notifications*100:.1f}%)" if total_notifications > 0 else "未讀通知: 0")
        self.stdout.write(f"已讀通知: {read_notifications:,} ({read_notifications/total_notifications*100:.1f}%)" if total_notifications > 0 else "已讀通知: 0")

        # 按類型統計
        self.stdout.write("\n📋 按類型統計:")
        type_stats = Notification.objects.values('notification_type').annotate(
            count=models.Count('id')
        ).order_by('-count')

        for stat in type_stats:
            notif_type = dict(Notification.NOTIFICATION_TYPES).get(
                stat['notification_type'], stat['notification_type']
            )
            self.stdout.write(f"  {notif_type}: {stat['count']:,}")

        # 時間統計
        now = timezone.now()
        recent_counts = {
            '今天': Notification.objects.filter(created_at__gte=now - timedelta(days=1)).count(),
            '本週': Notification.objects.filter(created_at__gte=now - timedelta(days=7)).count(),
            '本月': Notification.objects.filter(created_at__gte=now - timedelta(days=30)).count(),
        }

        self.stdout.write("\n📅 時間分布:")
        for period, count in recent_counts.items():
            self.stdout.write(f"  {period}: {count:,}")

        # 用戶通知分布
        self.stdout.write("\n👤 用戶通知分布:")
        user_stats = User.objects.filter(notifications__isnull=False).annotate(
            notification_count=models.Count('notifications')
        ).order_by('-notification_count')[:10]

        for user in user_stats:
            unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
            self.stdout.write(f"  {user.username}: {user.notification_count} 個 (未讀: {unread_count})")

    def cleanup_notifications(self, user_limit):
        """清理舊通知"""
        self.stdout.write("\n🧹 開始清理舊通知...")

        # 獲取有通知的用戶
        users = User.objects.filter(notifications__isnull=False).distinct()[:user_limit]
        total_cleaned = 0

        with transaction.atomic():
            for user in users:
                try:
                    # 檢查用戶通知數量
                    user_notification_count = Notification.objects.filter(recipient=user).count()

                    if user_notification_count > NotificationManager.MAX_NOTIFICATIONS_PER_USER:
                        # 保留最新的通知，刪除舊的
                        keep_count = NotificationManager.MAX_NOTIFICATIONS_PER_USER // 2

                        notifications_to_keep = Notification.objects.filter(
                            recipient=user
                        ).order_by('-created_at')[:keep_count]

                        keep_ids = list(notifications_to_keep.values_list('id', flat=True))

                        deleted_count = Notification.objects.filter(
                            recipient=user
                        ).exclude(id__in=keep_ids).delete()[0]

                        if deleted_count > 0:
                            total_cleaned += deleted_count
                            self.stdout.write(f"  清理用戶 {user.username}: {deleted_count} 個通知")

                    # 清理已讀的舊通知
                    cleaned_count = NotificationManager.cleanup_old_notifications(user)
                    total_cleaned += cleaned_count

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"清理用戶 {user.username} 失敗: {e}"))

        self.stdout.write(f"✅ 清理完成，總共清理 {total_cleaned} 個通知")

    def aggregate_notifications(self, user_limit):
        """聚合相似通知"""
        self.stdout.write("\n🔄 開始聚合相似通知...")

        users = User.objects.filter(notifications__isnull=False).distinct()[:user_limit]
        total_aggregated = 0

        with transaction.atomic():
            for user in users:
                try:
                    aggregated_count = NotificationManager.aggregate_similar_notifications(user)
                    if aggregated_count > 0:
                        total_aggregated += aggregated_count
                        self.stdout.write(f"  聚合用戶 {user.username}: {aggregated_count} 個通知")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"聚合用戶 {user.username} 失敗: {e}"))

        self.stdout.write(f"✅ 聚合完成，總共聚合 {total_aggregated} 個通知")

    def optimize_database(self):
        """優化數據庫"""
        self.stdout.write("\n⚡ 開始數據庫優化...")

        # 這裡可以添加數據庫優化邏輯
        # 例如：重建索引、更新統計信息等

        # 檢查是否需要添加缺失的索引
        self.check_database_indexes()

        self.stdout.write("✅ 數據庫優化完成")

    def check_database_indexes(self):
        """檢查並建議數據庫索引"""
        self.stdout.write("🔍 檢查數據庫索引...")

        # 這裡可以檢查常用查詢的索引情況
        # 並提供優化建議

        suggested_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_notification_recipient_read ON petapp_notification(recipient_id, is_read);",
            "CREATE INDEX IF NOT EXISTS idx_notification_type_created ON petapp_notification(notification_type, created_at);",
            "CREATE INDEX IF NOT EXISTS idx_notification_created_at ON petapp_notification(created_at DESC);",
        ]

        for index_sql in suggested_indexes:
            self.stdout.write(f"💡 建議索引: {index_sql}")

        self.stdout.write("📝 請在數據庫中執行上述索引創建語句以提升性能")