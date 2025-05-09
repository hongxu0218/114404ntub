# petapp/adapter.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.contrib import messages

from allauth.exceptions import ImmediateHttpResponse


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # 如果使用者已登入或這個社群帳號已經綁定過，就讓它通過
        if request.user.is_authenticated or sociallogin.is_existing:
            return

         # 使用者來自註冊流程的話就放行
        if sociallogin.state.get('next') and 'signup' in sociallogin.state.get('next'):
            return 
        
        if 'signup' in sociallogin.state.get('next', ''):
            return  # 放行

        # 沒有帳號 → 提示訊息並導向註冊頁
        request.session['signup_redirect_message'] = "您尚未註冊帳號，請先註冊後再使用 Google 登入。"
        raise ImmediateHttpResponse(redirect('account_signup'))