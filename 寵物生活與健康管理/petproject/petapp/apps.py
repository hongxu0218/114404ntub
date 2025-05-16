# petapp/apps.py
from django.apps import AppConfig

class PetappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'petapp'

    def ready(self):

        # 延遲取消註冊 Allauth 模型（等所有 admin 註冊完成後再處理）
        from django.contrib import admin
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken

        for model in [EmailAddress, SocialAccount, SocialApp, SocialToken]:
            if model in admin.site._registry:
                admin.site.unregister(model)
