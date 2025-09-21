# petapp/management/commands/process_expired_appointments.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from petapp.models import VetAppointment

class Command(BaseCommand):
    help = '處理過期預約，將過期的預約標記為已取消或未到診'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-back',
            type=int,
            default=7,
            help='檢查過去多少天的預約 (預設: 7天)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅顯示將會處理的預約，不實際更新'
        )
        parser.add_argument(
            '--mark-as',
            choices=['cancelled', 'no_show'],
            default='cancelled',
            help='將過期預約標記為什麼狀態 (預設: cancelled)'
        )

    def handle(self, *args, **options):
        days_back = options['days_back']
        dry_run = options['dry_run']
        mark_as = options['mark_as']
        
        # 計算檢查範圍
        now = timezone.now()
        start_date = (now - timedelta(days=days_back)).date()
        end_date = now.date()
        
        # 查找過期的預約
        expired_appointments = VetAppointment.objects.filter(
            slot__date__range=[start_date, end_date],
            status__in=['pending', 'confirmed']
        ).select_related('slot', 'pet', 'owner')
        
        # 篩選真正過期的預約
        truly_expired = []
        for appointment in expired_appointments:
            if appointment.is_expired:
                truly_expired.append(appointment)
        
        if not truly_expired:
            self.stdout.write(
                self.style.SUCCESS(f'沒有找到過期的預約（檢查範圍：{start_date} 到 {end_date}）')
            )
            return
        
        self.stdout.write(f'找到 {len(truly_expired)} 筆過期預約：')
        
        updated_count = 0
        for appointment in truly_expired:
            appointment_time = datetime.combine(
                appointment.slot.date, 
                appointment.slot.end_time
            )
            
            status_display = '已取消' if mark_as == 'cancelled' else '未到診'
            self.stdout.write(
                f'  - [{appointment.id}] {appointment.pet.name} '
                f'({appointment.slot.date} {appointment.slot.start_time}-{appointment.slot.end_time}) '
                f'狀態: {appointment.status} -> {mark_as} ({status_display})'
            )
            
            if not dry_run:
                if appointment.mark_as_expired(mark_as=mark_as):
                    updated_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'模擬模式：將會更新 {len(truly_expired)} 筆預約')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'成功處理 {updated_count} 筆過期預約')
            )
    
    def get_appointment_display(self, appointment):
        """格式化預約顯示"""
        return (
            f"{appointment.pet.name} "
            f"({appointment.slot.date} "
            f"{appointment.slot.start_time}-{appointment.slot.end_time})"
        )