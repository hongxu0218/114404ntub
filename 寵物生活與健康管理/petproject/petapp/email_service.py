# petapp/email_service.py
"""
統一的郵件通知服務
處理所有預約相關的 Email 通知
"""

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class AppointmentEmailService:
    """預約相關的郵件通知服務"""

    @staticmethod
    def send_appointment_created_to_owner(appointment):
        """
        發送「預約成功」通知給飼主

        Args:
            appointment: VetAppointment 對象
        """
        try:
            owner = appointment.owner
            pet = appointment.pet
            slot = appointment.slot
            clinic = slot.clinic
            doctor = slot.doctor

            subject = f'【毛日好】預約申請成功 - {pet.name}'

            message = f"""親愛的 {owner.last_name or ''}{owner.first_name or owner.username}，您好：

您已成功送出預約申請！

【預約資訊】
預約編號：{appointment.id}
寵物名稱：{pet.name}
診所名稱：{clinic.clinic_name}
看診醫師：{doctor.user.get_full_name() if doctor else '待分配'}
預約日期：{slot.date}
預約時間：{slot.start_time.strftime('%H:%M')}
就診原因：{appointment.reason or '一般看診'}
聯絡電話：{appointment.contact_phone}
預約狀態：{'已確認' if appointment.status == 'confirmed' else '待確認'}

{'' if appointment.status == 'confirmed' else '診所將盡快與您聯絡確認預約時間。'}

如需取消預約，請登入系統至「我的預約」進行操作。

【診所資訊】
診所名稱：{clinic.clinic_name}
診所地址：{clinic.address or '請參閱診所網站'}
診所電話：{clinic.phone_number or '請參閱診所網站'}

感謝您使用毛日好寵物健康管理平台！

—————————————————————
毛日好 Paw&Day 寵物健康管理平台
網站：{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://pawday.com'}
客服信箱：pawday114404@gmail.com
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner.email],
                fail_silently=True,
            )

            logger.info(f"✅ 預約成功通知已發送給飼主：{owner.email} (預約編號：{appointment.id})")
            return True

        except Exception as e:
            logger.error(f"❌ 發送預約成功通知給飼主失敗：{e}")
            return False

    @staticmethod
    def send_appointment_created_to_vet(appointment):
        """
        發送「新預約通知」給獸醫師/診所

        Args:
            appointment: VetAppointment 對象
        """
        try:
            owner = appointment.owner
            pet = appointment.pet
            slot = appointment.slot
            clinic = slot.clinic
            doctor = slot.doctor

            # 收件人：獸醫師 + 診所管理員
            recipients = []

            # 加入指定的獸醫師
            if doctor and doctor.user.email:
                recipients.append(doctor.user.email)

            # 加入診所管理員
            if clinic.admin and clinic.admin.email:
                if clinic.admin.email not in recipients:
                    recipients.append(clinic.admin.email)

            # 加入診所其他管理員（如果有的話）
            clinic_admins = clinic.vet_doctors.filter(
                role__in=['admin', 'manager'],
                is_active=True
            )
            for admin in clinic_admins:
                if admin.user.email and admin.user.email not in recipients:
                    recipients.append(admin.user.email)

            if not recipients:
                logger.warning(f"⚠️ 預約 {appointment.id} 沒有可用的獸醫師/診所管理員 Email")
                return False

            subject = f'【毛日好】新預約通知 - {pet.name} ({owner.username})'

            message = f"""親愛的 {doctor.user.get_full_name() if doctor else '醫師'}，您好：

您收到一筆新的預約申請！

【預約資訊】
預約編號：{appointment.id}
預約時間：{slot.date} {slot.start_time.strftime('%H:%M')}
預約狀態：{'已確認' if appointment.status == 'confirmed' else '待確認'}

【飼主資訊】
飼主姓名：{owner.last_name or ''}{owner.first_name or owner.username}
聯絡電話：{appointment.contact_phone}
飼主信箱：{owner.email}

【寵物資訊】
寵物名稱：{pet.name}
寵物種類：{pet.get_species_display()}
品種：{pet.breed or '未提供'}
年齡：{pet.age or '未提供'}歲
性別：{pet.get_gender_display() if hasattr(pet, 'gender') else '未提供'}

【就診資訊】
就診原因：{appointment.reason or '一般看診'}
備註說明：{appointment.notes or '無'}

{'' if appointment.status == 'confirmed' else '請登入系統確認此預約。'}

【操作連結】
請登入診所管理系統查看詳細資訊：
{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://pawday.com'}/clinic/appointments/

—————————————————————
毛日好 Paw&Day 寵物健康管理平台
診所：{clinic.clinic_name}
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=True,
            )

            logger.info(f"✅ 新預約通知已發送給獸醫師/診所：{', '.join(recipients)} (預約編號：{appointment.id})")
            return True

        except Exception as e:
            logger.error(f"❌ 發送新預約通知給獸醫師失敗：{e}")
            return False

    @staticmethod
    def send_appointment_confirmed_to_owner(appointment):
        """
        發送「預約已確認」通知給飼主

        Args:
            appointment: VetAppointment 對象
        """
        try:
            owner = appointment.owner
            pet = appointment.pet
            slot = appointment.slot
            clinic = slot.clinic
            doctor = slot.doctor

            subject = f'【毛日好】預約已確認 - {pet.name}'

            message = f"""親愛的 {owner.last_name or ''}{owner.first_name or owner.username}，您好：

您的預約已經確認！

【預約資訊】
預約編號：{appointment.id}
寵物名稱：{pet.name}
診所名稱：{clinic.clinic_name}
看診醫師：{doctor.user.get_full_name() if doctor else '待分配'}
預約日期：{slot.date}
預約時間：{slot.start_time.strftime('%H:%M')}

請記得準時到診，如需取消請盡早操作。

【診所資訊】
診所名稱：{clinic.clinic_name}
診所地址：{clinic.address or '請參閱診所網站'}
診所電話：{clinic.phone_number or '請參閱診所網站'}

【注意事項】
• 請提前 10 分鐘到診所報到
• 攜帶寵物健康手冊（如有）
• 如需取消請至少提前 24 小時通知

感謝您使用毛日好寵物健康管理平台！

—————————————————————
毛日好 Paw&Day 寵物健康管理平台
客服信箱：pawday114404@gmail.com
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner.email],
                fail_silently=True,
            )

            logger.info(f"✅ 預約確認通知已發送給飼主：{owner.email} (預約編號：{appointment.id})")
            return True

        except Exception as e:
            logger.error(f"❌ 發送預約確認通知給飼主失敗：{e}")
            return False

    @staticmethod
    def send_appointment_cancelled_to_owner(appointment, cancel_reason='', cancelled_by='system'):
        """
        發送「預約已取消」通知給飼主

        Args:
            appointment: VetAppointment 對象
            cancel_reason: 取消原因
            cancelled_by: 取消者 ('owner', 'vet', 'system')
        """
        try:
            owner = appointment.owner
            pet = appointment.pet
            slot = appointment.slot
            clinic = slot.clinic

            subject = f'【毛日好】預約已取消 - {pet.name}'

            canceller_text = {
                'owner': '您已',
                'vet': '診所已',
                'system': '系統已'
            }.get(cancelled_by, '已')

            message = f"""親愛的 {owner.last_name or ''}{owner.first_name or owner.username}，您好：

{canceller_text}取消預約。

【預約資訊】
預約編號：{appointment.id}
寵物名稱：{pet.name}
診所名稱：{clinic.clinic_name}
原預約日期：{slot.date}
原預約時間：{slot.start_time.strftime('%H:%M')}
取消原因：{cancel_reason or '未提供'}

如需重新預約，請登入系統選擇其他時段。

感謝您使用毛日好寵物健康管理平台！

—————————————————————
毛日好 Paw&Day 寵物健康管理平台
客服信箱：pawday114404@gmail.com
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner.email],
                fail_silently=True,
            )

            logger.info(f"✅ 預約取消通知已發送給飼主：{owner.email} (預約編號：{appointment.id})")
            return True

        except Exception as e:
            logger.error(f"❌ 發送預約取消通知給飼主失敗：{e}")
            return False

    @staticmethod
    def send_appointment_cancelled_to_vet(appointment, cancel_reason='', cancelled_by='owner'):
        """
        發送「預約已取消」通知給獸醫師/診所

        Args:
            appointment: VetAppointment 對象
            cancel_reason: 取消原因
            cancelled_by: 取消者 ('owner', 'vet', 'system')
        """
        try:
            owner = appointment.owner
            pet = appointment.pet
            slot = appointment.slot
            clinic = slot.clinic
            doctor = slot.doctor

            # 收件人：獸醫師 + 診所管理員
            recipients = []

            if doctor and doctor.user.email:
                recipients.append(doctor.user.email)

            if clinic.admin and clinic.admin.email:
                if clinic.admin.email not in recipients:
                    recipients.append(clinic.admin.email)

            if not recipients:
                logger.warning(f"⚠️ 預約 {appointment.id} 沒有可用的獸醫師/診所管理員 Email")
                return False

            canceller_text = {
                'owner': '飼主已',
                'vet': '診所已',
                'system': '系統已'
            }.get(cancelled_by, '已')

            subject = f'【毛日好】預約已取消 - {pet.name} ({owner.username})'

            message = f"""親愛的 {doctor.user.get_full_name() if doctor else '醫師'}，您好：

{canceller_text}取消預約。

【預約資訊】
預約編號：{appointment.id}
原預約時間：{slot.date} {slot.start_time.strftime('%H:%M')}
取消原因：{cancel_reason or '未提供'}

【飼主資訊】
飼主姓名：{owner.last_name or ''}{owner.first_name or owner.username}
聯絡電話：{appointment.contact_phone}

【寵物資訊】
寵物名稱：{pet.name}
寵物種類：{pet.get_species_display()}

此時段已釋出，可供其他預約使用。

—————————————————————
毛日好 Paw&Day 寵物健康管理平台
診所：{clinic.clinic_name}
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=True,
            )

            logger.info(f"✅ 預約取消通知已發送給獸醫師/診所：{', '.join(recipients)} (預約編號：{appointment.id})")
            return True

        except Exception as e:
            logger.error(f"❌ 發送預約取消通知給獸醫師失敗：{e}")
            return False

    @staticmethod
    def send_appointment_reminder_to_owner(appointment):
        """
        發送「預約提醒」給飼主（預約前一天）

        Args:
            appointment: VetAppointment 對象
        """
        try:
            owner = appointment.owner
            pet = appointment.pet
            slot = appointment.slot
            clinic = slot.clinic
            doctor = slot.doctor

            subject = f'【毛日好】明日看診提醒 - {pet.name}'

            message = f"""親愛的 {owner.last_name or ''}{owner.first_name or owner.username}，您好：

提醒您明日有預約看診！

【預約資訊】
預約編號：{appointment.id}
寵物名稱：{pet.name}
診所名稱：{clinic.clinic_name}
看診醫師：{doctor.user.get_full_name() if doctor else '待分配'}
預約日期：{slot.date}
預約時間：{slot.start_time.strftime('%H:%M')}

【診所資訊】
診所名稱：{clinic.clinic_name}
診所地址：{clinic.address or '請參閱診所網站'}
診所電話：{clinic.phone_number or '請參閱診所網站'}

【注意事項】
• 請提前 10 分鐘到診所報到
• 攜帶寵物健康手冊（如有）
• 如需取消請盡早通知診所

祝您與 {pet.name} 看診順利！

—————————————————————
毛日好 Paw&Day 寵物健康管理平台
客服信箱：pawday114404@gmail.com
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner.email],
                fail_silently=True,
            )

            logger.info(f"✅ 預約提醒已發送給飼主：{owner.email} (預約編號：{appointment.id})")
            return True

        except Exception as e:
            logger.error(f"❌ 發送預約提醒給飼主失敗：{e}")
            return False

    @staticmethod
    def send_appointment_updated_notification(appointment, changes=''):
        """
        發送「預約變更」通知給飼主和獸醫師

        Args:
            appointment: VetAppointment 對象
            changes: 變更內容描述
        """
        try:
            owner = appointment.owner
            pet = appointment.pet
            slot = appointment.slot
            clinic = slot.clinic
            doctor = slot.doctor

            # 通知飼主
            subject_owner = f'【毛日好】預約變更通知 - {pet.name}'
            message_owner = f"""親愛的 {owner.last_name or ''}{owner.first_name or owner.username}，您好：

您的預約資訊已變更。

【預約資訊】
預約編號：{appointment.id}
寵物名稱：{pet.name}
診所名稱：{clinic.clinic_name}
看診醫師：{doctor.user.get_full_name() if doctor else '待分配'}
預約日期：{slot.date}
預約時間：{slot.start_time.strftime('%H:%M')}

【變更內容】
{changes or '詳細資訊請參閱預約詳情'}

如有任何問題，請聯絡診所。

—————————————————————
毛日好 Paw&Day 寵物健康管理平台
客服信箱：pawday114404@gmail.com
"""

            send_mail(
                subject=subject_owner,
                message=message_owner,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner.email],
                fail_silently=True,
            )

            # 通知獸醫師
            if doctor and doctor.user.email:
                subject_vet = f'【毛日好】預約變更通知 - {pet.name} ({owner.username})'
                message_vet = f"""親愛的 {doctor.user.get_full_name()}，您好：

預約資訊已變更。

【預約資訊】
預約編號：{appointment.id}
預約時間：{slot.date} {slot.start_time.strftime('%H:%M')}
飼主：{owner.last_name or ''}{owner.first_name or owner.username}
寵物：{pet.name}

【變更內容】
{changes or '詳細資訊請參閱系統'}

—————————————————————
毛日好 Paw&Day 寵物健康管理平台
診所：{clinic.clinic_name}
"""

                send_mail(
                    subject=subject_vet,
                    message=message_vet,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[doctor.user.email],
                    fail_silently=True,
                )

            logger.info(f"✅ 預約變更通知已發送 (預約編號：{appointment.id})")
            return True

        except Exception as e:
            logger.error(f"❌ 發送預約變更通知失敗：{e}")
            return False
