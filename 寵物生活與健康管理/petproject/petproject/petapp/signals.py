# signals.py
from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from .models import Profile

@receiver(user_signed_up)
def social_user_signed_up(request, user, **kwargs):
    account_type = request.session.pop('pending_account_type', None)
    # 只有非管理員帳號才建立 profile，避免工程師預設變飼主
    if not hasattr(user, 'profile') and not user.is_staff:
        # 先建立 profile，但不設定帳號類型，登入後由使用者補選
        Profile.objects.create(user=user, account_type=account_type)