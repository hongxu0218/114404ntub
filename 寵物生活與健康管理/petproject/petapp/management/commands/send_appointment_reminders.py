# petapp/management/commands/send_appointment_reminders.py

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from petapp.models import VetAppointment
from petapp.email_service import AppointmentEmailService
from datetime import timedelta

class Command(BaseCommand):
    help = 'Send email reminders to owners one day before appointments'

    def handle(self, *args, **kwargs):
        tomorrow = now().date() + timedelta(days=1)
        appointments = VetAppointment.objects.filter(
            slot__date=tomorrow,
            status__in=['confirmed', 'pending']  # 只提醒已確認或待確認的預約
        ).select_related('owner', 'pet', 'slot__clinic', 'slot__doctor__user')

        success_count = 0
        for appt in appointments:
            # 使用新的郵件服務發送提醒
            if AppointmentEmailService.send_appointment_reminder_to_owner(appt):
                success_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"已成功發送 {success_count}/{appointments.count()} 封提醒郵件")
        )
