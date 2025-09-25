# petapp/management/commands/cleanup_old_notifications.py
"""
通知清理管理命令
定期清理舊通知以維護系統性能
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from petapp.models import Notification


class Command(BaseCommand):
    help = '清理舊通知以維護系統性能'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='清理幾天前的已讀通知（默認90天）'
        )
        parser.add_argument(
            '--unread-days',
            type=int,
            default=365,
            help='清理幾天前的未讀通知（默認365天）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模擬運行，不實際刪除'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='批次處理大小（默認1000）'
        )

    def handle(self, *args, **options):
        days = options['days']
        unread_days = options['unread_days']
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        cutoff_date = timezone.now() - timedelta(days=days)
        unread_cutoff_date = timezone.now() - timedelta(days=unread_days)

        self.stdout.write(f"🧹 開始清理通知...")
        self.stdout.write(f"📅 已讀通知清理日期: {cutoff_date.strftime('%Y-%m-%d')}")
        self.stdout.write(f"📅 未讀通知清理日期: {unread_cutoff_date.strftime('%Y-%m-%d')}")

        # 統計要清理的通知
        old_read_notifications = Notification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_date
        )

        very_old_unread_notifications = Notification.objects.filter(
            is_read=False,
            created_at__lt=unread_cutoff_date
        )

        total_to_delete = old_read_notifications.count() + very_old_unread_notifications.count()

        if total_to_delete == 0:
            self.stdout.write(self.style.SUCCESS("✅ 沒有需要清理的通知"))
            return

        self.stdout.write(f"🔍 找到 {old_read_notifications.count()} 個舊的已讀通知")
        self.stdout.write(f"🔍 找到 {very_old_unread_notifications.count()} 個非常舊的未讀通知")
        self.stdout.write(f"📊 總計要清理: {total_to_delete} 個通知")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 模擬運行模式 - 不會實際刪除"))
            return

        # 確認刪除
        confirm = input("確定要刪除這些通知嗎？(y/N): ")
        if confirm.lower() != 'y':
            self.stdout.write("❌ 取消操作")
            return

        deleted_count = 0

        # 批次刪除已讀通知
        if old_read_notifications.exists():
            self.stdout.write("🗑️ 正在刪除舊的已讀通知...")
            while old_read_notifications.exists():
                batch = old_read_notifications[:batch_size]
                batch_ids = list(batch.values_list('id', flat=True))
                deleted = Notification.objects.filter(id__in=batch_ids).delete()[0]
                deleted_count += deleted
                self.stdout.write(f"   已刪除 {deleted} 個通知 (總計: {deleted_count})")

        # 批次刪除非常舊的未讀通知
        if very_old_unread_notifications.exists():
            self.stdout.write("🗑️ 正在刪除非常舊的未讀通知...")
            while very_old_unread_notifications.exists():
                batch = very_old_unread_notifications[:batch_size]
                batch_ids = list(batch.values_list('id', flat=True))
                deleted = Notification.objects.filter(id__in=batch_ids).delete()[0]
                deleted_count += deleted
                self.stdout.write(f"   已刪除 {deleted} 個通知 (總計: {deleted_count})")

        self.stdout.write(self.style.SUCCESS(f"✅ 清理完成！總共刪除 {deleted_count} 個通知"))

        # 顯示統計信息
        remaining_count = Notification.objects.count()
        self.stdout.write(f"📊 剩餘通知數量: {remaining_count}")