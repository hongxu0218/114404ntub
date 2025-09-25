# petapp/management/commands/simple_cleanup.py
"""
簡化版通知清理命令
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from petapp.models import Notification


class Command(BaseCommand):
    help = '清理舊通知'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='清理幾天前的已讀通知（默認90天）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模擬運行，不實際刪除'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(f"開始清理 {days} 天前的已讀通知...")
        self.stdout.write(f"截止日期: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")

        # 統計要清理的通知
        old_notifications = Notification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_date
        )

        total_to_delete = old_notifications.count()

        if total_to_delete == 0:
            self.stdout.write("沒有需要清理的通知")
            return

        self.stdout.write(f"找到 {total_to_delete} 個需要清理的已讀通知")

        if dry_run:
            self.stdout.write("模擬運行模式 - 不會實際刪除")

            # 顯示詳細信息
            for notification in old_notifications[:10]:  # 只顯示前10個
                self.stdout.write(f"  - {notification.title} ({notification.created_at})")

            if total_to_delete > 10:
                self.stdout.write(f"  ... 還有 {total_to_delete - 10} 個")

            return

        # 實際刪除
        deleted_count, _ = old_notifications.delete()

        self.stdout.write(f"清理完成！刪除了 {deleted_count} 個通知")

        # 顯示統計
        remaining_count = Notification.objects.count()
        self.stdout.write(f"剩餘通知數量: {remaining_count}")