# petapp/management/commands/send_appointment_reminders.py

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import connection
from petapp.models import VetAppointment
from petapp.email_service import AppointmentEmailService
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send email reminders to owners one day before appointments'

    def handle(self, *args, **kwargs):
        try:
            # 確保資料庫連線是新的
            connection.ensure_connection()

            tomorrow = now().date() + timedelta(days=1)
            logger.info(f"查詢明天 ({tomorrow}) 的預約...")

            appointments = VetAppointment.objects.filter(
                slot__date=tomorrow,
                status__in=['confirmed', 'pending']  # 只提醒已確認或待確認的預約
            ).select_related('owner', 'pet', 'slot__clinic', 'slot__doctor__user')

            total_count = appointments.count()
            logger.info(f"找到 {total_count} 筆需要提醒的預約")

            success_count = 0
            fail_count = 0

            for appt in appointments:
                try:
                    # 使用新的郵件服務發送提醒
                    if AppointmentEmailService.send_appointment_reminder_to_owner(appt):
                        success_count += 1
                        logger.debug(f"成功發送提醒給預約 #{appt.id}")
                    else:
                        fail_count += 1
                        logger.warning(f"發送提醒失敗: 預約 #{appt.id}")
                except Exception as e:
                    fail_count += 1
                    logger.error(f"發送提醒時發生錯誤 (預約 #{appt.id}): {e}")

            self.stdout.write(
                self.style.SUCCESS(f"已成功發送 {success_count}/{total_count} 封提醒郵件")
            )

            if fail_count > 0:
                self.stdout.write(
                    self.style.WARNING(f"失敗: {fail_count} 封")
                )

            logger.info(f"預約提醒任務完成: 成功 {success_count}, 失敗 {fail_count}")

        except Exception as e:
            logger.error(f"預約提醒任務執行錯誤: {e}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f"任務執行失敗: {e}")
            )
        finally:
            # 確保關閉資料庫連線
            connection.close()
