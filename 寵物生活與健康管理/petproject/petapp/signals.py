# petapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


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