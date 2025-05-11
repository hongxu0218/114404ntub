# petapp/adapter.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if request.user.is_authenticated or sociallogin.is_existing:
            return

        user_model = get_user_model()
        email = sociallogin.user.email

        try:
            existing_user = user_model.objects.get(email=email)
            # 帳號存在但尚未綁定社群帳號 → 綁定
            sociallogin.connect(request, existing_user)
            return
        except user_model.DoesNotExist:
            pass

        # 若來自註冊流程，則進入補資料頁面（不顯示警告）
        if request.session.pop('from_signup', False):
            request.session['socialaccount_sociallogin'] = sociallogin.serialize()
            raise ImmediateHttpResponse(redirect('/accounts/social/signup/extra/'))

        # 否則是從登入頁來但帳號不存在 → 跳回註冊並提示
        request.session['signup_redirect_message'] = "您尚未註冊帳號，請先註冊後再使用 Google 登入。"
        raise ImmediateHttpResponse(redirect('/accounts/signup/'))
