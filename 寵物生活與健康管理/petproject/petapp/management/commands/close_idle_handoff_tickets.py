"""
自動關閉閒置的人工客服工單
用法: python manage.py close_idle_handoff_tickets
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from petapp.models import HandoffTicket
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '自動關閉閒置超過指定時間的人工客服工單'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=15,
            help='閒置超時時間（分鐘），預設 15 分鐘'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模擬執行，不實際關閉工單'
        )

    def handle(self, *args, **options):
        timeout_minutes = options['timeout']
        dry_run = options['dry_run']

        self.stdout.write(f'開始檢查閒置工單（超時時間: {timeout_minutes} 分鐘）...')

        # 找出所有開啟中的工單
        open_tickets = HandoffTicket.objects.filter(is_open=True)
        total = open_tickets.count()
        self.stdout.write(f'找到 {total} 個開啟中的工單')

        closed_count = 0
        for ticket in open_tickets:
            idle_minutes = (timezone.now() - ticket.last_activity_at).total_seconds() / 60

            if ticket.is_idle_timeout(timeout_minutes):
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[模擬] 工單 #{ticket.id} 已閒置 {idle_minutes:.1f} 分鐘，將被關閉'
                        )
                    )
                else:
                    if ticket.auto_close_if_idle(timeout_minutes):
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ 工單 #{ticket.id} 已閒置 {idle_minutes:.1f} 分鐘，已自動關閉'
                            )
                        )
                        closed_count += 1
                        logger.info(f'Auto-closed ticket #{ticket.id} after {idle_minutes:.1f} minutes of inactivity')

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n[模擬模式] 共有 {closed_count} 個工單將被關閉'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n完成！共關閉 {closed_count} 個閒置工單'))
