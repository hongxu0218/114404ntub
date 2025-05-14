# # signals.py
# from allauth.account.signals import user_signed_up
# from django.dispatch import receiver
# from .models import Profile
# from django.core.mail import send_mail
# from django.conf import settings

# @receiver(user_signed_up)
# def social_user_signed_up(request, user, **kwargs):
#     print("🐾 [Signal] user_signed_up triggered.")

#     account_type = request.session.pop('pending_account_type', None)
#     print(f"🐾 [Debug] account_type = {account_type}")

#     if not hasattr(user, 'profile') and not user.is_staff:
#         profile = Profile.objects.create(user=user, account_type=account_type)
#         print("✅ [Signal] Profile created for user:", user.username)