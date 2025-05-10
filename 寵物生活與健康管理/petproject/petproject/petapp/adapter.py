# petapp/adapter.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from allauth.exceptions import ImmediateHttpResponse

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if request.user.is_authenticated or sociallogin.is_existing:
            return

        # 確認是不是從註冊來的流程
        if request.session.pop('from_signup', False):
            request.session['socialaccount_sociallogin'] = sociallogin.serialize()
            raise ImmediateHttpResponse(redirect('/accounts/social/signup/extra/'))

        # 錯誤的直接登入行為
        request.session['signup_redirect_message'] = "您尚未註冊帳號，請先註冊後再使用 Google 登入。"
        raise ImmediateHttpResponse(redirect('/accounts/signup/'))
