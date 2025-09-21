# petapp/management/commands/send_appointment_reminders.py

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.core.mail import send_mail
from petapp.models import VetAppointment
from datetime import timedelta
from django.conf import settings

class Command(BaseCommand):
    help = 'Send email reminders to owners one day before appointments'

    def handle(self, *args, **kwargs):
        tomorrow = now().date() + timedelta(days=1)
        appointments = VetAppointment.objects.filter(date=tomorrow)

        for appt in appointments:
            owner = appt.owner
            pet = appt.pet
            vet = appt.vet

            subject = f"【毛日好】提醒您明日看診：{pet.name}"
            message = f"""親愛的 {owner.last_name or ''}{owner.first_name or owner.username}，您好：

這是您預約的提醒通知：

寵物：{pet.name}  
日期：{appt.date}  
時間：{appt.time.strftime('%H:%M')}  
診所：{vet.clinic_name or '（未填寫）'}

請準時到診，如需取消請盡早操作，謝謝您！

— 毛日好（Paw&Day）系統
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [owner.email],
                fail_silently=False
            )

        self.stdout.write(self.style.SUCCESS(f"已寄出 {appointments.count()} 封提醒信件"))
