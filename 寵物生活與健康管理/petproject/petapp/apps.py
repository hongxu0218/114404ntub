# petapp/apps.py
from django.apps import AppConfig
from django.dispatch import receiver
from allauth.account.signals import email_confirmed

class PetappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'petapp'

    def ready(self):
        # 現有的 admin
        from django.contrib import admin
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken

        for model in [EmailAddress, SocialAccount, SocialApp, SocialToken]:
            if model in admin.site._registry:
                admin.site.unregister(model)

        # 載入信號處理器
        import petapp.signals

@receiver(email_confirmed)
def email_confirmed_handler(request, email_address, **kwargs):
    """確保郵件確認後狀態正確更新"""
    try:
        # 強制設定為已驗證
        email_address.verified = True
        email_address.save()
        
        # 如果是用戶唯一的郵件，設為主要郵件
        user_emails = EmailAddress.objects.filter(user=email_address.user)
        if user_emails.count() == 1 or not user_emails.filter(primary=True).exists():
            email_address.primary = True
            email_address.save()
            
            # 同步更新 User 模型
            user = email_address.user
            user.email = email_address.email
            user.save()
        
        print(f"SUCCESS 信號處理：郵件 {email_address.email} 已驗證")
        
    except Exception as e:
        print(f"ERROR 信號處理錯誤: {e}")