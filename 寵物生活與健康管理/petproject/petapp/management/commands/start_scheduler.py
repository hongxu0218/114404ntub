# petapp/management/commands/start_scheduler.py

import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util
from django.core.management import call_command

logger = logging.getLogger(__name__)

def send_appointment_reminders_job():
    """定時任務：發送預約提醒"""
    try:
        call_command('send_appointment_reminders')
        logger.info("預約提醒任務執行成功")
    except Exception as e:
        logger.error(f"預約提醒任務執行失敗: {e}")

@util.close_old_connections
def delete_old_job_executions(max_age=604_800):
    """刪除超過一週的任務執行記錄"""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)

class Command(BaseCommand):
    help = "啟動定時任務排程器"

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # 每天上午 9:00 發送預約提醒（提前一天）
        scheduler.add_job(
            send_appointment_reminders_job,
            trigger=CronTrigger(hour=9, minute=0),  # 每天上午9點
            id="send_appointment_reminders",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("已添加預約提醒任務：每天上午9:00執行")

        # 每週清理舊的任務執行記錄
        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
                day_of_week="mon", hour=0, minute=0
            ),  # 每週一午夜
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("已添加清理任務：每週一午夜執行")

        try:
            logger.info("正在啟動排程器...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("正在停止排程器...")
            scheduler.shutdown()
            logger.info("排程器已停止！")