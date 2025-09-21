# petapp/management/commands/cleanup_expired_appointments.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from petapp.utils import process_expired_appointments
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '定期清理過期預約，將其標記為已取消'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-back',
            type=int,
            default=1,
            help='處理過去多少天的過期預約 (預設: 1天)'
        )
        parser.add_argument(
            '--mark-as',
            choices=['cancelled', 'no_show'],
            default='cancelled',
            help='將過期預約標記為什麼狀態 (預設: cancelled)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅顯示將會處理的預約，不實際更新'
        )

    def handle(self, *args, **options):
        days_back = options['days_back']
        mark_as = options['mark_as']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.HTTP_INFO(
                f'開始處理過去 {days_back} 天的過期預約...'
            )
        )
        
        try:
            # 處理過期預約
            result = process_expired_appointments(days_back=days_back, mark_as=mark_as)
            
            if result['processed_count'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'成功處理 {result["processed_count"]} 筆過期預約，'
                        f'狀態標記為：{mark_as}'
                    )
                )
                
                # 記錄處理詳情
                for appointment in result['processed_appointments']:
                    self.stdout.write(
                        f'  - [ID:{appointment["id"]}] {appointment["pet_name"]} '
                        f'({appointment["date"]} {appointment["time"]}) '
                        f'{appointment["previous_status"]} → {appointment["new_status"]}'
                    )
                    
                logger.info(
                    f'Processed {result["processed_count"]} expired appointments'
                )
            else:
                self.stdout.write(
                    self.style.HTTP_INFO('沒有找到需要處理的過期預約')
                )
                
        except Exception as e:
            error_msg = f'處理過期預約時發生錯誤: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise
            
        self.stdout.write(
            self.style.HTTP_INFO('過期預約處理完成')
        )