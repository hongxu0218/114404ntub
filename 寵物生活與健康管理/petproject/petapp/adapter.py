# petapp/adapter.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        """簡化的社交登入處理"""
        logger.info(f"pre_social_login called - user: {request.user.is_authenticated}, existing: {sociallogin.is_existing}")

        # 如果用戶已登入或社交帳號已存在，直接返回
        if request.user.is_authenticated or sociallogin.is_existing:
            logger.info("User already authenticated or sociallogin existing, returning")
            return

        # 檢查是否有相同 email 的現有用戶
        user_model = get_user_model()
        email = sociallogin.user.email

        try:
            existing_user = user_model.objects.get(email=email)
            logger.info(f"Found existing user for {email}, connecting")
            sociallogin.connect(request, existing_user)
            return
        except user_model.DoesNotExist:
            logger.info(f"No existing user found for {email}")
            pass

        # 統一設置需要補充資料的標記
        logger.info("Setting google_needs_profile for new Google user")
        request.session['google_needs_profile'] = True
        request.session.pop('from_signup', None)  # 清除可能存在的舊標記
        return
    
    def get_login_redirect_url(self, request, sociallogin):
        """決定登入後的重定向 URL"""
        needs_profile = request.session.get('google_needs_profile', False)
        logger.info(f"get_login_redirect_url called - needs_profile: {needs_profile}")
        logger.info(f"sociallogin.is_existing: {sociallogin.is_existing}")
        logger.info(f"Session contents: {dict(request.session)}")

        # 如果需要補充個人資料，重定向到補充資料頁
        if needs_profile:
            logger.info("Redirecting to extra signup page from get_login_redirect_url")
            return '/accounts/social/signup/extra/'

        # 使用智能重導向邏輯
        logger.info("Using smart login redirect")
        return '/login-redirect/'
    
    def save_user(self, request, sociallogin, form=None):
        """保存用戶後的處理"""
        logger.info(f"save_user called for {sociallogin.user.email}")
        user = super().save_user(request, sociallogin, form)

        # 如果需要補充資料，暫時不創建 Profile（在補充資料頁面處理）
        needs_profile = request.session.get('google_needs_profile', False)
        logger.info(f"save_user - google_needs_profile: {needs_profile}")

        if not needs_profile:
            logger.info("Creating basic profile for existing user login")
            # 一般的社交登入，創建基本 Profile
            from .models import Profile
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'account_type': 'owner',
                    'phone_number': ''
                }
            )
            if created:
                logger.info(f"Created basic profile for user: {user.email}")
        else:
            # 保持session標記，讓後續重定向邏輯能正確處理
            logger.info(f"Keeping google_needs_profile session for user: {user.email}")

        return user
    
    def get_signup_redirect_url(self, request, user):
        """註冊完成後的重定向 URL"""
        needs_profile = request.session.get('google_needs_profile', False)
        logger.info(f"get_signup_redirect_url called for {user.email}")
        logger.info(f"google_needs_profile: {needs_profile}")
        logger.info(f"Session contents: {dict(request.session)}")

        # 如果需要補充個人資料，重定向到補充資料頁
        if needs_profile:
            logger.info("Redirecting to extra signup page via get_signup_redirect_url")
            return '/accounts/social/signup/extra/'

        # 使用預設重定向
        logger.info("Using default signup redirect")
        return super().get_signup_redirect_url(request, user)
    
    def populate_user(self, request, sociallogin, data):
        """填充用戶數據 - 智能生成不衝突的用戶名"""
        user = super().populate_user(request, sociallogin, data)

        # 智能生成用戶名策略
        if not user.username:
            base_username = user.email.split('@')[0]
            username = self._generate_unique_username(base_username, sociallogin.account.uid)
            user.username = username
            logger.info(f"Generated unique username: {username}")

            # 保存建議的基礎用戶名供後續使用
            if request.session.get('google_needs_profile'):
                request.session['suggested_username'] = base_username
                request.session['generated_username'] = username

        return user
    
    def _generate_unique_username(self, base_username, uid):
        """生成唯一的用戶名"""
        user_model = get_user_model()
        
        # 首先嘗試基礎用戶名
        if not user_model.objects.filter(username=base_username).exists():
            return base_username
            
        # 嘗試加數字後綴
        for i in range(1, 100):
            candidate = f"{base_username}{i}"
            if not user_model.objects.filter(username=candidate).exists():
                return candidate
        
        # 最後使用 UID 後綴確保唯一性
        return f"{base_username}_{uid[-6:]}"
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """決定是否允許自動註冊"""
        # 始終允許Google自動註冊（簡化邏輯）
        logger.info("Auto signup allowed for Google login")
        return True
