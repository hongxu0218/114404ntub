# petapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import (
    UserProfile, Notification, Follow, Like, Comment, CommentLike,
    Post, VetAppointment, VaccineRecord, DewormRecord
)
from .google_calendar_service import GoogleCalendarService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_social_profile(sender, instance, created, **kwargs):
    """當用戶被創建時，自動創建社群檔案"""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_social_profile(sender, instance, **kwargs):
    """當用戶被保存時，確保社群檔案存在"""
    if hasattr(instance, 'social_profile'):
        instance.social_profile.save()
    else:
        UserProfile.objects.get_or_create(user=instance)


# ===== 通知觸發信號 =====

@receiver(post_save, sender=Follow)
def create_follow_notification(sender, instance, created, **kwargs):
    """當有人追蹤時發送通知"""
    if created:
        Notification.objects.create(
            recipient=instance.following,
            sender=instance.follower,
            notification_type='follow',
            title='新的追蹤者',
            message=f'{instance.follower.username} 開始追蹤您！'
        )


@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    """當貼文被按讚時發送通知"""
    if created and instance.user != instance.post.user:  # 不通知自己按讚自己的貼文
        Notification.objects.create(
            recipient=instance.post.user,
            sender=instance.user,
            notification_type='like',
            title='貼文被按讚',
            message=f'{instance.user.username} 讚了您的貼文',
            post=instance.post
        )


@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    """當貼文被留言時發送通知"""
    if created and instance.user != instance.post.user:  # 不通知自己留言自己的貼文
        Notification.objects.create(
            recipient=instance.post.user,
            sender=instance.user,
            notification_type='comment',
            title='新的留言',
            message=f'{instance.user.username} 留言了您的貼文：{instance.content[:50]}',
            post=instance.post,
            comment=instance
        )


@receiver(post_save, sender=CommentLike)
def create_comment_like_notification(sender, instance, created, **kwargs):
    """當留言被按讚時發送通知"""
    if created and instance.user != instance.comment.user:  # 不通知自己按讚自己的留言
        Notification.objects.create(
            recipient=instance.comment.user,
            sender=instance.user,
            notification_type='comment_like',
            title='留言被按讚',
            message=f'{instance.user.username} 讚了您的留言',
            post=instance.comment.post,
            comment=instance.comment
        )


@receiver(post_save, sender=VetAppointment)
def create_appointment_notification(sender, instance, created, **kwargs):
    """當預約狀態改變時發送通知"""
    if created:
        # 新預約建立 - 只通知獸醫端，不通知飼主
        try:
            # 通知獸醫師
            if instance.slot and instance.slot.doctor:
                Notification.objects.create(
                    recipient=instance.slot.doctor.user,
                    sender=instance.owner,
                    notification_type='appointment_created',
                    title='新預約',
                    message=f'{instance.owner.username} 預約了 {instance.pet.name} - {instance.slot.date.strftime("%Y/%m/%d")} {instance.slot.start_time}'
                )

            # 通知診所管理員（如果存在且不是同一人）
            if instance.slot and instance.slot.doctor and instance.slot.doctor.clinic:
                clinic = instance.slot.doctor.clinic
                # 找到診所管理員
                if clinic.clinic_admin and clinic.clinic_admin != instance.slot.doctor.user:
                    Notification.objects.create(
                        recipient=clinic.clinic_admin,
                        sender=instance.owner,
                        notification_type='appointment_created',
                        title='新預約',
                        message=f'{instance.owner.username} 預約了 {instance.pet.name} - {instance.slot.date.strftime("%Y/%m/%d")} {instance.slot.start_time}'
                    )

            # 自動新增至飼主的 Google Calendar
            if hasattr(instance.owner, 'profile') and instance.owner.profile.google_calendar_enabled:
                try:
                    event_id = GoogleCalendarService.create_appointment_event(instance.owner, instance)
                    if event_id:
                        instance.google_calendar_event_id = event_id
                        instance.save(update_fields=['google_calendar_event_id'])
                        logger.info(f"已將預約新增至 Google Calendar: {event_id}")
                except Exception as e:
                    logger.error(f"新增預約至 Google Calendar 失敗: {e}")

        except Exception as e:
            print(f"預約通知創建錯誤: {e}")
    else:
        # 預約狀態更新
        try:
            if instance.status == 'confirmed':
                Notification.objects.create(
                    recipient=instance.owner,
                    notification_type='appointment_confirmed',
                    title='預約已確認',
                    message=f'您的預約已被確認：{instance.pet.name} - {instance.slot.date.strftime("%Y/%m/%d")} {instance.slot.start_time}'
                )
            elif instance.status == 'cancelled':
                Notification.objects.create(
                    recipient=instance.owner,
                    notification_type='appointment_cancelled',
                    title='預約已取消',
                    message=f'您的預約已被取消：{instance.pet.name} - {instance.slot.date.strftime("%Y/%m/%d")} {instance.slot.start_time}'
                )

                # 如果預約取消，也刪除 Google Calendar 事件
                if instance.google_calendar_event_id and hasattr(instance.owner, 'profile'):
                    try:
                        service = GoogleCalendarService(instance.owner)
                        service.delete_event(instance.google_calendar_event_id)
                        logger.info(f"已從 Google Calendar 刪除預約事件: {instance.google_calendar_event_id}")
                    except Exception as e:
                        logger.error(f"刪除 Google Calendar 事件失敗: {e}")

            elif instance.status == 'completed':
                Notification.objects.create(
                    recipient=instance.owner,
                    notification_type='appointment_completed',
                    title='預約已完成',
                    message=f'您的預約已完成：{instance.pet.name} - {instance.slot.date.strftime("%Y/%m/%d")} {instance.slot.start_time}'
                )
        except Exception as e:
            print(f"預約狀態更新通知錯誤: {e}")


@receiver(post_save, sender=VaccineRecord)
def create_vaccine_calendar_event(sender, instance, created, **kwargs):
    """當疫苗記錄建立時，自動新增至 Google Calendar"""
    if created:
        try:
            # 取得寵物飼主
            owner = instance.pet.owner

            # 檢查飼主是否啟用 Google Calendar 同步
            if hasattr(owner, 'profile') and owner.profile.google_calendar_enabled:
                event_id = GoogleCalendarService.create_vaccine_event(owner, instance)
                if event_id:
                    instance.google_calendar_event_id = event_id
                    instance.save(update_fields=['google_calendar_event_id'])
                    logger.info(f"已將疫苗記錄新增至 Google Calendar: {event_id}")
        except Exception as e:
            logger.error(f"新增疫苗記錄至 Google Calendar 失敗: {e}")


@receiver(post_save, sender=DewormRecord)
def create_deworm_calendar_event(sender, instance, created, **kwargs):
    """當驅蟲記錄建立時，自動新增至 Google Calendar"""
    if created:
        try:
            # 取得寵物飼主
            owner = instance.pet.owner

            # 檢查飼主是否啟用 Google Calendar 同步
            if hasattr(owner, 'profile') and owner.profile.google_calendar_enabled:
                event_id = GoogleCalendarService.create_deworm_event(owner, instance)
                if event_id:
                    instance.google_calendar_event_id = event_id
                    instance.save(update_fields=['google_calendar_event_id'])
                    logger.info(f"已將驅蟲記錄新增至 Google Calendar: {event_id}")
        except Exception as e:
            logger.error(f"新增驅蟲記錄至 Google Calendar 失敗: {e}")