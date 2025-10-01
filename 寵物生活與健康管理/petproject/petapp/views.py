# petapp/views.py
# Django 寵物管理系統的視圖函數

from collections import defaultdict
from functools import wraps
from datetime import date, datetime, timedelta, time
from calendar import monthrange
import calendar
import json
import logging
import traceback

# Django 核心導入
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Min, Max, Count, Sum, Avg, Q, F
from django.http import HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timezone import localtime
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.contrib.auth import logout
from django.contrib.auth.models import User

# 第三方導入
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.account.views import SignupView ,ConfirmEmailView
from allauth.socialaccount.views import SignupView as SocialSignupView
from dateutil.relativedelta import relativedelta

import requests
import logging

# Python 版本相容性處理
try:
    from typing import Dict, List, Optional, Tuple, Union
except ImportError:
    # Python 3.8 以下版本的相容性
    Dict = dict
    List = list
    Optional = lambda x: x
    Tuple = tuple
    Union = lambda *args: args[0]

# 本地導入
from .models import (
    Profile, Pet, VetClinic, VetDoctor, VetSchedule, VetAppointment,
    AppointmentSlot, VaccineRecord, DewormRecord, Report, MedicalRecord,
    PetType, DailyRecord, PetLocation, ClinicBusinessHoursRecord, ServiceType, VetAvailableTime,
    VetScheduleException, WEEKDAYS, TIME_SLOTS, AdoptionPet, TransferRequest, AdoptionTransferRequest, REGION_CHOICES,
    # 進階排班管理模型
    ScheduleTemplate, EnhancedVetSchedule, ScheduleChangeRequest, ClinicScheduleRule,
    # 通知系統
    Notification
)
from .forms import (
    VetClinicRegistrationForm, VetDoctorForm, VetProfileEditForm, AppointmentBookingForm,
    VetScheduleForm, EditProfileForm, PetForm, EditDoctorForm,
    SocialSignupExtraForm, MedicalRecordForm, VaccineRecordForm, 
    DewormRecordForm, ReportForm, LicenseVerificationForm,
    TemperatureEditForm, WeightEditForm, VetAppointmentForm, VetScheduleExceptionForm,
    AdoptionForm, TransferRequestForm,
    VetAvailableTimeForm, DailyRecordForm, ClinicSettingsForm,
    ClinicSearchForm
)
from .choices import (
    FEATURE_CHOICES, PHYSICAL_CHOICES, ADOPTCONDITION_CHOICES,
    DOG_CHOICES, CAT_CHOICES, OTHER_CHOICES, DOGVACCINE_CHOICES, CATVACCINE_CHOICES
)

from .utils import (
    process_expired_appointments, get_expired_appointments_summary,
    get_temperature_data,
    get_weight_data,
    time_overlap, 
    detect_schedule_conflicts_for_clinic,
    calculate_schedule_coverage,
    optimize_schedule_suggestions
)

logger = logging.getLogger(__name__)

# ============ 輔助函數 ============

def safe_json_loads(json_string):
    """安全地載入JSON字串，如果失敗則回傳預設值"""
    try:
        data = json.loads(json_string)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def check_time_period_conflicts(periods):
    """
    檢查時間段是否有衝突
    """
    conflicts = []
    
    for i, period1 in enumerate(periods):
        for j, period2 in enumerate(periods[i+1:], i+1):
            start1 = datetime.strptime(period1.get('startTime', '00:00'), '%H:%M').time()
            end1 = datetime.strptime(period1.get('endTime', '00:00'), '%H:%M').time()
            start2 = datetime.strptime(period2.get('startTime', '00:00'), '%H:%M').time()
            end2 = datetime.strptime(period2.get('endTime', '00:00'), '%H:%M').time()
            
            # 檢查重疊
            if start1 < end2 and start2 < end1:
                conflicts.append(f"時段 {i+1} 與時段 {j+1} 重疊")
    
    return conflicts

# ============ 自定義裝飾器定義 ============

def require_clinic_management(view_func):
    """
    自定義裝飾器:要求用戶具有診所管理權限
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 檢查用戶是否已登入
        if not request.user.is_authenticated:
            messages.error(request, '請先登入')
            return redirect('account_login')
        
        try:
            # 檢查是否有 vet_profile
            vet_profile = getattr(request.user, 'vet_profile', None)
            if not vet_profile:
                messages.error(request, '您不是診所成員')
                return redirect('home')

            # 檢查是否為診所管理員或有管理權限
            if not vet_profile.is_clinic_admin and not hasattr(vet_profile, 'can_manage_doctors'):
                messages.error(request, '您沒有診所管理權限')
                return redirect('home')

            if not vet_profile.is_clinic_admin and hasattr(vet_profile, 'can_manage_doctors') and not vet_profile.can_manage_doctors:
                messages.error(request, '您沒有診所管理權限')
                return redirect('home')

            # 檢查是否有關聯的診所
            if not vet_profile.clinic:
                messages.error(request, '找不到與您關聯的診所')
                return redirect('clinic_registration')

            return view_func(request, *args, **kwargs)

        except AttributeError:
            # 沒有 vet_profile 或其他屬性錯誤
            messages.error(request, '您不是診所成員')
            return redirect('home')
        except Exception as e:
            messages.error(request, f'權限檢查失敗:{str(e)}')
            return redirect('home')
    
    return _wrapped_view

def require_verified_vet(view_func=None, *, optional=False):
    """
    要求用戶是已驗證的獸醫師 - 支援雙重身份
    
    Args:
        optional (bool): 如果為 True，未驗證的獸醫師可以繼續使用，但會收到提醒訊息
    """
    def decorator(func):
        @wraps(func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, '請先登入')
                return redirect('account_login')
            
            try:
                # 首先檢查是否有一般 profile
                profile = request.user.profile
                
                # 如果是診所管理員，直接允許
                if profile.account_type == 'clinic_admin':
                    return func(request, *args, **kwargs)
                
                # 檢查是否有 vet_profile（獸醫師身份）
                try:
                    vet_profile = request.user.vet_profile
                    
                    # 檢查帳號是否啟用
                    if not vet_profile.is_active:
                        messages.error(request, '您的獸醫師帳號已被停用')
                        return redirect('home')
                    
                    # 檢查獸醫師身份是否啟用
                    if not vet_profile.is_active_veterinarian:
                        messages.error(request, '您的獸醫師權限尚未啟用，請聯繫診所管理員')
                        return redirect('home')
                    
                    # 修改驗證邏輯：有啟用獸醫師權限即可，不需要 MOA 執照驗證
                    print(f"*** DECORATOR CHECK: is_active_veterinarian = {vet_profile.is_active_veterinarian}, optional = {optional}")
                    # 如果已經通過前面的 is_active_veterinarian 檢查，就可以繼續使用功能
                    print(f"*** Active veterinarian permissions confirmed, allowing access")
                    
                    return func(request, *args, **kwargs)
                except AttributeError:
                    messages.error(request, '您不是獸醫師')
                    return redirect('home')
                
            except AttributeError:
                messages.error(request, '請先完成帳號設定')
                return redirect('home')
        
        return _wrapped_view
    
    if view_func is None:
        # 被當作 @require_verified_vet(optional=True) 使用
        return decorator
    else:
        # 被當作 @require_verified_vet 使用（無參數）
        return decorator(view_func)

def require_owner_or_vet(view_func):
    """
    自定義裝飾器:要求用戶是寵物飼主或獸醫師
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '請先登入')
            return redirect('account_login')
        
        try:
            profile = request.user.profile
            
            # 檢查是否為飼主或獸醫師
            if profile.account_type not in ['owner', 'veterinarian', 'clinic_admin']:
                messages.error(request, '您沒有權限存取此頁面')
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
            
        except AttributeError:
            messages.error(request, '請完成帳號設定')
            return redirect('home')
    
    return _wrapped_view

def require_owner(view_func):
    """
    自定義裝飾器:要求用戶是寵物飼主
    防止獸醫師訪問飼主專用功能
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '請先登入')
            return redirect('account_login')

        try:
            profile = request.user.profile

            # 檢查是否為飼主
            if profile.account_type != 'owner':
                messages.error(request, '此功能僅限寵物飼主使用，獸醫師請使用獸醫工作台')
                return redirect('home')

            return view_func(request, *args, **kwargs)

        except AttributeError:
            messages.error(request, '請完成帳號設定')
            return redirect('edit_profile')

    return _wrapped_view

def check_pet_ownership(view_func):
    """
    自定義裝飾器:檢查寵物所有權（用於保護寵物相關頁面）
    """
    @wraps(view_func)
    def _wrapped_view(request, pet_id, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '請先登入')
            return redirect('account_login')
        
        if pet_id:
            try:
                pet = Pet.objects.get(id=pet_id)
                
                # 檢查是否為寵物飼主
                if pet.owner != request.user:
                    # 如果是獸醫師，檢查是否有看診記錄
                    try:
                        vet_profile = request.user.vet_profile
                        if not VetAppointment.objects.filter(
                            pet=pet, 
                            doctor=vet_profile
                        ).exists():
                            messages.error(request, '您沒有權限查看此寵物資料')
                            return redirect('home')
                    except AttributeError:
                        messages.error(request, '您沒有權限查看此寵物資料')
                        return redirect('home')
                
            except Pet.DoesNotExist:
                messages.error(request, '找不到該寵物')
                return redirect('pet_list')
        
        return view_func(request, pet_id, *args, **kwargs)
    
    return _wrapped_view


def require_clinic_management_api(view_func):
    """
    API專用:要求用戶具有診所管理權限的裝飾器（返回JSON錯誤而非重定向）
    """
    def wrapper(request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': '用戶未登錄',
                    'status': 401
                }, status=401)
            
            vet_profile = getattr(request.user, 'vet_profile', None)
            if not vet_profile:
                return JsonResponse({
                    'success': False,
                    'error': '您沒有獸醫師權限',
                    'status': 403
                }, status=403)

            if not vet_profile.is_clinic_admin and not vet_profile.is_veterinarian:
                return JsonResponse({
                    'success': False,
                    'error': '您沒有診所管理權限',
                    'status': 403
                }, status=403)
                
            return view_func(request, *args, **kwargs)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'權限檢查失敗:{str(e)}',
                'status': 500
            }, status=500)
    
    return wrapper


# ============ 基本頁面視圖 ============

def test_theme(request):
    """主題測試頁面"""
    return render(request, 'test_theme.html')

def home(request):
    """首頁"""
    import logging
    logger = logging.getLogger(__name__)
    
    # 檢查用戶是否需要補充 Google 註冊資料
    if request.user.is_authenticated and request.session.get('google_needs_profile'):
        logger.info("User authenticated with google_needs_profile flag, redirecting to extra signup")
        return redirect('/accounts/social/signup/extra/')
    
    # 檢查已登入用戶是否沒有 Profile
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            logger.info(f"User has profile: {profile.account_type}")
        except:
            logger.info("User has no profile, this might be a Google signup user")
            # 如果用戶沒有 Profile，可能是 Google 註冊用戶，重定向到補充資料頁面
            request.session['google_needs_profile'] = True
            return redirect('/accounts/social/signup/extra/')
    
    return render(request, 'pages/index.html')

def dashboard(request):
    """儀表板（通用）"""
    if not request.user.is_authenticated:
        return redirect('account_login')
    
    try:
        profile = request.user.profile
        if profile.account_type == 'owner':
            return redirect('pet_list')
        elif profile.account_type in ['veterinarian', 'clinic_admin']:
            if hasattr(request.user, 'vet_profile') and request.user.vet_profile.clinic:
                return redirect('clinic_dashboard')
            else:
                return redirect('clinic_registration')
    except:
        pass
    
    return redirect('home')

# ============ 註冊相關視圖 ============

class CustomSignupView(SignupView):
    """使用者一般註冊流程覆寫"""
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        return redirect('/')  # 註冊成功導向首頁

class CustomSocialSignupView(SocialSignupView):
    """Google 社群註冊流程（含 session 取資料）"""
    
    def dispatch(self, request, *args, **kwargs):
        # 如果是 Google 註冊流程且需要補充資料，讓 allauth 處理用戶創建
        if request.session.get('google_needs_profile'):
            logger.info("CustomSocialSignupView detected google_needs_profile, processing signup")
            # 如果用戶已經登入，直接重定向到補充資料頁面
            if request.user.is_authenticated:
                logger.info("User already authenticated in dispatch, redirecting to extra signup")
                return redirect('/accounts/social/signup/extra/')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        """處理 GET 請求"""
        logger.info(f"CustomSocialSignupView GET - user authenticated: {request.user.is_authenticated}")
        logger.info(f"google_needs_profile: {request.session.get('google_needs_profile')}")
        
        # 如果到達這裡，說明自動註冊沒有被觸發
        # 正常顯示註冊表單
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        # 如果是來自 Google 註冊且需要補充資料，先完成用戶註冊再重定向
        if self.request.session.get('google_needs_profile'):
            logger.info("Google signup needs profile, completing signup and redirecting")
            response = super().form_valid(form)
            # 用戶現在已經被創建和登入，重定向到補充資料頁面
            return redirect('/accounts/social/signup/extra/')
        
        response = super().form_valid(form)
        user = form.user

        # 取出註冊階段儲存的 session 資料
        account_type = self.request.session.pop('account_type', None)
        phone_number = self.request.session.pop('phone_number', None)
        vet_license_city = self.request.session.pop('vet_license_city', '')
        vet_license_name = self.request.session.pop('vet_license_name', None)
        vet_license_content = self.request.session.pop('vet_license_content', None)

        # 建立或更新 Profile 資料
        profile, created = Profile.objects.update_or_create(
            user=user,
            defaults={
                'account_type': account_type,
                'phone_number': phone_number,
                'vet_license_city': vet_license_city,
            }
        )

        # 如果有獸醫執照相關資料，進一步處理
        if vet_license_name and vet_license_content:
            profile.vet_license_name = vet_license_name
            profile.vet_license_content = vet_license_content
            profile.save()

        messages.success(self.request, '註冊成功！歡迎加入我們的服務。')
        return redirect('home')

@login_required
def select_account_type(request):
    """選擇帳號類型"""
    if request.method == 'POST':
        account_type = request.POST.get('account_type')
        if account_type in ['owner', 'veterinarian']:
            # 存儲到 session 中，在社群註冊時使用
            request.session['account_type'] = account_type
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': '無效的帳號類型'})
    
    return render(request, 'pages/select_account_type.html')

@login_required
def edit_profile(request):
    """編輯個人資料"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '個人資料更新成功！')
            return redirect('edit_profile')
    else:
        form = EditProfileForm(instance=profile, user=request.user)
    
    return render(request, 'account/edit.html', {'form': form})

def mark_from_signup_and_redirect(request):
    """標記來自註冊並重定向到適當頁面"""
    import logging
    logger = logging.getLogger(__name__)
    
    # 如果是 POST 請求（來自註冊頁面的 Google 按鈕）
    if request.method == 'POST':
        logger.info("Setting from_signup flag via POST request")
        request.session['from_signup'] = True
        logger.info(f"Session after setting from_signup: {dict(request.session)}")
        return JsonResponse({'status': 'success'})
    
    # GET 請求的原始邏輯
    logger.info("Setting from_signup flag via GET request")
    request.session['from_signup'] = True
    
    # 檢查用戶是否已登入
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            # 根據帳號類型導向不同頁面
            if profile.account_type == 'owner':
                messages.info(request, '歡迎！請先為您的寵物建立檔案。')
                return redirect('add_pet')
            elif profile.account_type in ['veterinarian', 'clinic_admin']:
                messages.info(request, '歡迎！請先完成診所註冊。')
                return redirect('clinic_registration')
        except Profile.DoesNotExist:
            # 如果沒有 profile，導向個人資料編輯頁面
            messages.info(request, '請先完成個人資料設定。')
            return redirect('edit_profile')
    
    # 預設導向首頁
    return redirect('home')



def clear_signup_message(request):
    """清除註冊訊息（AJAX）"""
    if 'signup_redirect_message' in request.session:
        del request.session['signup_redirect_message']
    if 'from_signup' in request.session:
        del request.session['from_signup']
    
    return JsonResponse({'status': 'success', 'message': '訊息已清除'})


# ============ 認證相關 函數 ============

def logout_success(request):
    """登出成功頁面"""
    return render(request, 'account/logout_success.html', {
        'title': '登出成功',
        'message': '您已成功登出，謝謝使用我們的服務！'
    })

def select_type_then_social_login(request):
    """選擇帳號類型後進行社群登入"""
    if request.method == 'POST':
        account_type = request.POST.get('account_type')
        
        # 驗證帳號類型
        if account_type in ['owner', 'veterinarian', 'clinic_admin']:
            # 將帳號類型存儲到 session
            request.session['selected_account_type'] = account_type
            request.session['from_signup'] = True
            
            # 根據不同帳號類型導向不同頁面
            if account_type == 'owner':
                # 飼主直接進行 Google 登入
                return redirect('/accounts/google/login/')
            elif account_type in ['veterinarian', 'clinic_admin']:
                # 獸醫師或診所管理員導向診所註冊
                return redirect('/accounts/google/login/')
            
        else:
            messages.error(request, '請選擇有效的帳號類型')
    
    # GET 請求顯示選擇頁面
    return render(request, 'pages/select_account_type.html', {
        'account_types': [
            {
                'value': 'owner', 
                'label': '寵物飼主', 
                'description': '管理寵物健康記錄、預約看診',
                'icon': 'fas fa-heart'
            },
            {
                'value': 'veterinarian', 
                'label': '獸醫師', 
                'description': '提供專業醫療服務',
                'icon': 'fas fa-user-md'
            },
            {
                'value': 'clinic_admin', 
                'label': '診所管理員', 
                'description': '管理診所營運和醫師排班',
                'icon': 'fas fa-hospital'
            },
        ]
    })

def social_signup_extra(request):
    """Google 註冊後補資料頁面"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"=== social_signup_extra called ===")
    logger.info(f"User authenticated: {request.user.is_authenticated}")
    logger.info(f"User: {request.user}")
    logger.info(f"User ID: {getattr(request.user, 'id', 'None')}")
    logger.info(f"google_needs_profile: {request.session.get('google_needs_profile')}")
    logger.info(f"Session contents: {dict(request.session)}")
    
    # 檢查用戶是否已登入
    if not request.user.is_authenticated:
        logger.warning("User not authenticated, redirecting to login")
        messages.error(request, '請先完成 Google 登入')
        return redirect('account_login')
    
    # 檢查是否需要補充資料
    if not request.session.get('google_needs_profile'):
        # 檢查是否是社交帳號用戶但沒有Profile
        from allauth.socialaccount.models import SocialAccount
        social_accounts = SocialAccount.objects.filter(user=request.user)

        if social_accounts.exists():
            try:
                profile = request.user.profile
                # 如果有Profile就完成了，導向首頁
                logger.info("Social account user has profile, redirecting to home")
                messages.info(request, '您已完成註冊流程')
                return redirect('home')
            except:
                # 沒有Profile，重新設置標記繼續處理
                logger.info("Social account user missing profile, setting flag and continuing")
                request.session['google_needs_profile'] = True
        else:
            logger.info("No google_needs_profile flag, redirecting to home")
            messages.info(request, '您已完成註冊流程')
            return redirect('home')
    
    if request.method == 'POST':
        form = SocialSignupExtraForm(request.POST, current_user=request.user)
        if form.is_valid():
            try:
                account_type = 'owner'  # 預設為飼主
                
                # 用戶已經登入，直接更新資料
                user = request.user
                new_username = form.cleaned_data['username']
                
                # 檢查是否為當前用戶修改自己的用戶名（允許）
                if user.username != new_username:
                    # 如果用戶名改變了，確保新用戶名不衝突（排除當前用戶）
                    if User.objects.exclude(id=user.id).filter(username=new_username).exists():
                        messages.error(request, '此使用者名稱已被使用，請選擇其他名稱')
                        form.add_error('username', '此使用者名稱已被使用')
                        return render(request, 'account/social_signup_extra.html', {
                            'form': form,
                            'account_type': '飼主'
                        })
                
                # 更新用戶資料
                user.username = new_username

                # 設定密碼（如果有提供）
                password = form.cleaned_data.get('password1')
                if password:
                    user.set_password(password)
                    logger.info(f"Password set for user {user.username}")
                else:
                    logger.info(f"No password provided for user {user.username}, keeping social login only")

                user.save()

                # 創建或更新 Profile
                profile, created = Profile.objects.update_or_create(
                    user=user,
                    defaults={
                        'account_type': account_type,
                        'phone_number': form.cleaned_data['phone_number']
                    }
                )

                # 如果設定了密碼，需要重新登入用戶以保持 session 有效
                if password:
                    from django.contrib.auth import login
                    # 指定使用 ModelBackend 進行登入
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    logger.info(f"User {user.username} re-logged in after password setting")

                # 清理 session
                if 'google_needs_profile' in request.session:
                    del request.session['google_needs_profile']

                if password:
                    messages.success(request, '帳號設定完成！密碼已設定，您現在可以使用帳號密碼或 Google 登入。')
                else:
                    messages.success(request, '帳號設定完成！您可以使用 Google 登入。')
                
                # 根據帳號類型導向適當頁面
                if account_type == 'owner':
                    return redirect('pet_list')
                elif account_type in ['veterinarian', 'clinic_admin']:
                    return redirect('clinic_registration')
                else:
                    return redirect('home')
                    
            except Exception as e:
                messages.error(request, f'設定過程發生錯誤:{str(e)}')
                
    else:
        # 智能預填：使用已生成的用戶名，但提供原始建議
        initial_data = {}
        if request.user.is_authenticated:
            # 優先使用生成的用戶名
            initial_data['username'] = request.user.username
            
        form = SocialSignupExtraForm(initial=initial_data, current_user=request.user)
    
    return render(request, 'account/social_signup_extra.html', {
        'form': form,
        'account_type': '飼主',  # 固定為飼主
        'suggested_username': request.session.get('suggested_username'),
        'generated_username': request.session.get('generated_username'),
    })



# ============ 自定義郵件確認 view ============
class CustomConfirmEmailView(ConfirmEmailView):
    """自定義郵件確認 view"""
    
    def get(self, *args, **kwargs):
        try:
            response = super().get(*args, **kwargs)
            
            # 確認成功後的額外處理
            if hasattr(self, 'object') and self.object:
                messages.success(
                    self.request, 
                    '電子郵件驗證成功！您的帳號已啟用。'
                )
            
            return response
            
        except Exception as e:
            messages.error(
                self.request, 
                f'郵件驗證過程發生錯誤:{str(e)}'
            )
            return redirect('account_login')
    
    def post(self, *args, **kwargs):
        try:
            response = super().post(*args, **kwargs)
            
            # POST 確認成功後導向適當頁面
            if self.request.user.is_authenticated:
                try:
                    profile = self.request.user.profile
                    if profile.account_type == 'owner':
                        return redirect('pet_list')
                    elif profile.account_type in ['veterinarian', 'clinic_admin']:
                        return redirect('clinic_dashboard')
                except Profile.DoesNotExist:
                    return redirect('edit_profile')
            
            return response
            
        except Exception as e:
            messages.error(
                self.request, 
                f'確認過程發生錯誤:{str(e)}'
            )
            return redirect('account_login')


# ============ 寵物管理視圖 ============

@login_required
@require_owner
def pet_list(request):
    """寵物列表 - 僅限飼主"""
    
    pets = Pet.objects.filter(owner=request.user).order_by('-id')
    
    # 為每隻寵物添加健康洞察
    from .utils import get_health_insights
    pets_with_health = []
    for pet in pets:
        health_insights = get_health_insights(pet)
        pets_with_health.append({
            'pet': pet,
            'health_insights': health_insights
        })
    
    # 取得所有待領養 / 已送養的原始寵物 id
    adopting_pet_ids = AdoptionPet.objects.filter(
        is_adopted=False
    ).values_list('original_pet_id', flat=True)

    adopted_pet_ids = AdoptionPet.objects.filter(
        is_adopted=True
    ).values_list('original_pet_id', flat=True)

    adopting_set = set(adopting_pet_ids)
    adopted_set = set(adopted_pet_ids)
    
    # 更新 pets_with_health 的領養狀態
    for item in pets_with_health:
        pet = item['pet']
        pet.is_adoption_only = pet.id in adopting_set   # 待領養
        pet.is_adopted = pet.id in adopted_set        # 已送養
    
    # 分頁處理 - 使用 pets_with_health
    paginator = Paginator(pets_with_health, 6)  # 每頁顯示6隻寵物
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 送養狀態
    adopting_pet_ids = AdoptionPet.objects.filter(
        owner=request.user,
        is_adopted=False
    ).values_list('name', 'chip')

    adopted_pet_ids = AdoptionPet.objects.filter(
        owner=request.user,
        is_adopted=True
    ).values_list('name', 'chip')
    
    # 計算整體健康統計
    total_urgent_alerts = sum(1 for item in pets_with_health 
                             if item['health_insights']['urgent_alerts_count'] > 0)
    total_warning_alerts = sum(1 for item in pets_with_health 
                              if item['health_insights']['warning_alerts_count'] > 0)
    
    return render(request, 'pet_info/pet_list.html', {
        'page_obj': page_obj,
        'pets': page_obj,
        'adopting_pet_ids': adopting_pet_ids,
        'adopted_pet_ids': adopted_pet_ids,
        'total_urgent_alerts': total_urgent_alerts,
        'total_warning_alerts': total_warning_alerts,
        'total_pets': len(pets_with_health),
    })

def get_breed_choices(request):
    """AJAX API: 根據種類取得品種選項"""
    from django.http import JsonResponse
    from .choices import DOG_CHOICES, CAT_CHOICES, OTHER_CHOICES
    
    species = request.GET.get('species', 'dog')
    
    if species == 'dog':
        choices = DOG_CHOICES
    elif species == 'cat':
        choices = CAT_CHOICES
    elif species == 'other':
        choices = OTHER_CHOICES
    else:
        choices = DOG_CHOICES  # 預設
    
    return JsonResponse({
        'breeds': [{'value': choice[0], 'text': choice[1]} for choice in choices]
    })

@login_required
@require_owner
def add_pet(request):
    """新增寵物 - 僅限飼主"""
    
    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.owner = request.user
            pet.save()
            messages.success(request, f'成功新增寵物 {pet.name}！')
            return redirect('pet_list')
    else:
        form = PetForm(owner=request.user)
    
    return render(request, 'pet_info/add_pet.html', {'form': form})

@login_required
@require_owner
def edit_pet(request, pet_id):
    """編輯寵物資料"""
    pet = get_object_or_404(Pet, id=pet_id)
    
    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES, instance=pet, owner=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'成功更新 {pet.name} 的資料！')
            return redirect('pet_list')
    else:
        form = PetForm(instance=pet, owner=request.user)
    
    return render(request, 'pet_info/edit_pet.html', {
        'form': form,
        'pet': pet
    })

@login_required
@require_owner
def delete_pet(request, pet_id):
    """刪除寵物"""
    pet = get_object_or_404(Pet, id=pet_id)
    
    if request.method == 'POST':
        pet_name = pet.name
        pet.delete()
        messages.success(request, f'已刪除寵物 {pet_name}')
        return redirect('pet_list')
    
    return render(request, 'pet_info/delete_pet.html', {'pet': pet})

@login_required
def profile_view(request):
    """個人資料檢視"""
    try:
        profile = request.user.profile
        return render(request, 'registration/profile.html', {
            'profile': profile
        })
    except Profile.DoesNotExist:
        return redirect('edit_profile')

@login_required  
def pet_profile(request, pet_id):
    """寵物檔案"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    
    # 獲取最近的健康記錄
    recent_records = DailyRecord.objects.filter(
        pet=pet
    ).order_by('-date')[:10]
    
    # 獲取疫苗記錄
    vaccines = VaccineRecord.objects.filter(pet=pet).order_by('-date')
    
    # 獲取驅蟲記錄  
    deworming = DewormRecord.objects.filter(pet=pet).order_by('-date')
    
    return render(request, 'pet_info/pet_profile.html', {
        'pet': pet,
        'recent_records': recent_records,
        'vaccines': vaccines,
        'deworming': deworming
    })

# ============ 健康記錄管理 ============

@login_required
@require_owner
def health_rec(request):
    """健康記錄總覽 - 僅限飼主"""
    pets = Pet.objects.filter(owner=request.user)

    # 獲取當前標籤參數
    current_tab = request.GET.get('tab', 'medical')

    # 獲取寵物篩選參數
    selected_pet_id = request.GET.get('pet')
    selected_pet = None

    if selected_pet_id:
        try:
            selected_pet = pets.get(id=selected_pet_id)
            # 只顯示選定寵物的記錄
            pets = pets.filter(id=selected_pet_id)
        except Pet.DoesNotExist:
            # 如果寵物不存在或不屬於當前用戶，忽略篩選
            selected_pet_id = None
    
    # 收集各類型記錄的數量
    medical_records = []
    vaccine_records = []
    deworm_records = []
    report_records = []
    daily_records = []
    
    for pet in pets:
        # 收集並增強醫療記錄 - 按照訪問日期倒序排列（最新的在前）
        pet_medical_records = pet.medicalrecord_set.select_related('attending_vet__user').order_by('-visit_date', '-created_at')
        for record in pet_medical_records:
            # medical_details 現在是 @property，自動解析
            record.has_detailed_info = bool(record.medical_details and
                                           (record.medical_details.get('prescriptions') or
                                            record.medical_details.get('symptoms') or
                                            record.medical_details.get('weight') or
                                            record.medical_details.get('temperature')))

        medical_records.extend(pet_medical_records)
        vaccine_records.extend(pet.vaccine_records.order_by('-date'))
        deworm_records.extend(pet.deworm_records.order_by('-date'))
        if hasattr(pet, 'reports'):
            report_records.extend(pet.reports.order_by('-date_uploaded'))
        # 獲取生活記錄 (通過 DailyRecord 的 pet 外鍵反向查詢)
        daily_records.extend(pet.dailyrecord_set.all())
    
    # 將生活記錄按照日期和建立時間倒序排列（最新的在前）
    daily_records.sort(key=lambda record: (record.date, record.created_at), reverse=True)
    
    # 獲取所有寵物用於篩選器顯示
    all_user_pets = Pet.objects.filter(owner=request.user)

    context = {
        'pets': pets,
        'all_pets': all_user_pets,
        'selected_pet': selected_pet,
        'selected_pet_id': selected_pet_id,
        'current_tab': current_tab,
        'medical_records': medical_records,
        'vaccine_records': vaccine_records,
        'deworm_records': deworm_records,
        'report_records': report_records,
        'daily_records': daily_records,
    }
    
    return render(request, 'health_records/health_rec.html', context)

@login_required
@check_pet_ownership
def add_daily_record(request, pet_id):
    """新增每日記錄"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    # 獲取用戶的所有寵物，用於切換功能
    user_pets = Pet.objects.filter(owner=request.user).order_by('name')

    if request.method == 'POST':
        form = DailyRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.pet = pet
            record.save()
            messages.success(request, f'成功為 {pet.name} 新增記錄！')
            return redirect('health_rec')
        else:
            # 添加錯誤信息
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = DailyRecordForm()

    return render(request, 'health_records/add_daily_record.html', {
        'form': form,
        'pet': pet,
        'user_pets': user_pets,
        'current_pet_id': pet.id
    })

@login_required
@require_http_methods(["GET"])
def daily_record_chart_data(request):
    """提供生活記錄圖表數據API"""
    pets = Pet.objects.filter(owner=request.user)
    pet_id = request.GET.get('pet_id')
    category = request.GET.get('category', 'temperature')
    days = int(request.GET.get('days', 30))
    
    if pet_id:
        pets = pets.filter(id=pet_id)
    
    # 計算日期範圍
    from datetime import datetime, timedelta
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    chart_data = {
        'labels': [],
        'datasets': []
    }
    
    if category in ['temperature', 'weight']:
        # 數值型數據
        for pet in pets:
            records = DailyRecord.objects.filter(
                pet=pet,
                category=category,
                date__gte=start_date,
                date__lte=end_date
            ).exclude(
                **{f'{category}__isnull': True}
            ).order_by('date')
            
            pet_data = {
                'label': pet.name,
                'data': [],
                'borderColor': _get_pet_color(pet.id),
                'backgroundColor': _get_pet_color(pet.id) + '20',
                'fill': False,
                'tension': 0.2
            }
            
            for record in records:
                value = getattr(record, category)
                if value:
                    pet_data['data'].append({
                        'x': record.date.strftime('%Y-%m-%d'),
                        'y': float(value)
                    })
            
            if pet_data['data']:
                chart_data['datasets'].append(pet_data)
        
        # 生成日期標籤
        current_date = start_date
        while current_date <= end_date:
            chart_data['labels'].append(current_date.strftime('%m-%d'))
            current_date += timedelta(days=1)
            
    elif category == 'exercise':
        # 運動時長統計
        for pet in pets:
            records = DailyRecord.objects.filter(
                pet=pet,
                category='exercise',
                date__gte=start_date,
                date__lte=end_date
            ).exclude(exercise_duration__isnull=True).order_by('date')
            
            pet_data = {
                'label': f'{pet.name} 運動時長',
                'data': [],
                'borderColor': _get_pet_color(pet.id),
                'backgroundColor': _get_pet_color(pet.id) + '20',
                'fill': False,
                'tension': 0.2
            }
            
            for record in records:
                if record.exercise_duration:
                    pet_data['data'].append({
                        'x': record.date.strftime('%Y-%m-%d'),
                        'y': record.exercise_duration
                    })
            
            if pet_data['data']:
                chart_data['datasets'].append(pet_data)
    
    return JsonResponse(chart_data)

def _get_pet_color(pet_id):
    """根據寵物ID生成固定顏色"""
    colors = [
        '#FF6B35', '#6C5CE7', '#00B894', '#E17055', 
        '#FDCB6E', '#74B9FF', '#FD79A8', '#55A3FF'
    ]
    return colors[pet_id % len(colors)]

@require_POST
@login_required
def save_daily_record(request):
    """保存每日記錄（AJAX）"""
    try:
        pet_id = request.POST.get('pet_id')
        pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
        
        form = DailyRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.pet = pet
            record.save()
            return JsonResponse({
                'status': 'success',
                'message': '記錄保存成功！'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'errors': form.errors
            })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@require_POST
@login_required
def delete_daily_record(request, pet_id):
    """刪除每日記錄"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        record_id = request.POST.get('record_id')
        logger.info(f"嘗試刪除生活記錄 - pet_id: {pet_id}, record_id: {record_id}, user: {request.user}")

        if not record_id:
            return JsonResponse({
                'status': 'error',
                'message': '缺少記錄ID'
            })

        # 檢查寵物是否存在且屬於當前用戶
        try:
            pet = Pet.objects.get(id=pet_id, owner=request.user)
        except Pet.DoesNotExist:
            logger.error(f"寵物不存在或不屬於用戶 - pet_id: {pet_id}, user: {request.user}")
            return JsonResponse({
                'status': 'error',
                'message': '寵物不存在或您沒有權限'
            })

        # 檢查記錄是否存在
        try:
            record = DailyRecord.objects.get(id=record_id, pet=pet)
        except DailyRecord.DoesNotExist:
            logger.error(f"生活記錄不存在 - record_id: {record_id}, pet_id: {pet_id}")
            # 查看是否存在該記錄但不屬於該寵物
            try:
                wrong_record = DailyRecord.objects.get(id=record_id)
                logger.error(f"記錄存在但屬於其他寵物 - record_id: {record_id}, actual_pet_id: {wrong_record.pet.id}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'記錄不屬於指定寵物 (記錄屬於寵物ID: {wrong_record.pet.id})'
                })
            except DailyRecord.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': f'生活記錄不存在 (ID: {record_id})'
                })

        record.delete()
        logger.info(f"成功刪除生活記錄 - record_id: {record_id}")
        return JsonResponse({
            'status': 'success',
            'message': '記錄刪除成功！'
        })

    except Exception as e:
        logger.error(f"刪除生活記錄時發生錯誤: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'刪除失敗: {str(e)}'
        })

@require_POST
@login_required
def update_daily_record(request, record_id):
    """更新每日記錄"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"嘗試更新生活記錄 ID: {record_id}, 用戶: {request.user}")

        record = get_object_or_404(DailyRecord, id=record_id)

        # 檢查權限
        if record.pet.owner != request.user:
            logger.warning(f"用戶 {request.user} 嘗試編輯非自己的生活記錄 {record_id}")
            return JsonResponse({
                'status': 'error',
                'message': '無權限修改此記錄'
            })

        logger.info(f"請求方法: {request.method}, Content-Type: {request.content_type}")
        logger.info(f"REQUEST BODY: {request.body.decode('utf-8') if request.body else 'Empty'}")

        # 處理JSON數據或表單數據
        if request.content_type == 'application/json' or 'application/json' in request.META.get('CONTENT_TYPE', ''):
            import json
            try:
                data = json.loads(request.body)
                logger.info(f"解析的JSON數據: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析錯誤: {e}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'JSON 格式錯誤'
                })

            # 更新不同類型的數據
            updated_fields = []

            # 更新文字內容
            if 'content' in data:
                new_content = data['content'].strip()
                logger.info(f"準備更新內容: '{new_content}'")

                if new_content:  # 確保內容不為空
                    old_content = record.content
                    record.content = new_content
                    updated_fields.append(f"內容: '{old_content}' -> '{new_content}'")
                else:
                    logger.warning("嘗試設置空內容")
                    return JsonResponse({
                        'status': 'error',
                        'message': '記錄內容不能為空'
                    })

            # 更新體溫
            if 'temperature' in data:
                try:
                    temperature = float(data['temperature'])
                    if 35.0 <= temperature <= 42.0:  # 合理的體溫範圍
                        old_temp = record.temperature
                        record.temperature = temperature
                        updated_fields.append(f"體溫: {old_temp}°C -> {temperature}°C")
                        logger.info(f"更新體溫: {old_temp} -> {temperature}")
                    else:
                        return JsonResponse({
                            'status': 'error',
                            'message': '體溫值超出正常範圍 (35.0-42.0°C)'
                        })
                except (ValueError, TypeError):
                    return JsonResponse({
                        'status': 'error',
                        'message': '體溫值格式錯誤'
                    })

            # 更新體重
            if 'weight' in data:
                try:
                    weight = float(data['weight'])
                    if 0.1 <= weight <= 100.0:  # 合理的體重範圍
                        old_weight = record.weight
                        record.weight = weight
                        updated_fields.append(f"體重: {old_weight}kg -> {weight}kg")
                        logger.info(f"更新體重: {old_weight} -> {weight}")
                    else:
                        return JsonResponse({
                            'status': 'error',
                            'message': '體重值超出正常範圍 (0.1-100.0kg)'
                        })
                except (ValueError, TypeError):
                    return JsonResponse({
                        'status': 'error',
                        'message': '體重值格式錯誤'
                    })

            # 更新運動時長
            if 'exercise' in data:
                try:
                    exercise_duration = int(data['exercise'])
                    if 1 <= exercise_duration <= 480:  # 合理的運動時長範圍（1分鐘-8小時）
                        old_exercise = record.exercise_duration
                        record.exercise_duration = exercise_duration
                        updated_fields.append(f"運動時長: {old_exercise}分鐘 -> {exercise_duration}分鐘")
                        logger.info(f"更新運動時長: {old_exercise} -> {exercise_duration}")
                    else:
                        return JsonResponse({
                            'status': 'error',
                            'message': '運動時長超出正常範圍 (1-480分鐘)'
                        })
                except (ValueError, TypeError):
                    return JsonResponse({
                        'status': 'error',
                        'message': '運動時長格式錯誤'
                    })

            if updated_fields:
                record.save()
                logger.info(f"成功更新生活記錄 {record_id}: {'; '.join(updated_fields)}")
                return JsonResponse({
                    'status': 'success',
                    'message': '記錄更新成功！'
                })
            else:
                logger.error("JSON數據中缺少可更新的字段")
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少要更新的內容'
                })
        else:
            logger.info("使用表單數據更新")
            # 處理表單數據（完整編輯）
            form = DailyRecordForm(request.POST, instance=record)
            if form.is_valid():
                form.save()
                logger.info(f"通過表單成功更新生活記錄 {record_id}")
                return JsonResponse({
                    'status': 'success',
                    'message': '記錄更新成功！'
                })
            else:
                logger.error(f"表單驗證錯誤: {form.errors}")
                return JsonResponse({
                    'status': 'error',
                    'errors': form.errors
                })

    except Exception as e:
        logger.error(f"更新生活記錄時發生異常: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


# ============ CSRF Token 獲取 ============
@ensure_csrf_cookie
def get_csrf_token(request):
    """專門用於獲取CSRF token的視圖 - 適用於AJAX請求"""
    from django.middleware.csrf import get_token
    return JsonResponse({
        'csrfToken': get_token(request)
    })


# ============ 疫苗記錄管理 ============

@login_required
@require_owner
def add_vaccine(request, pet_id):
    """新增疫苗記錄"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    
    if request.method == 'POST':
        form = VaccineRecordForm(request.POST)
        if form.is_valid():
            vaccine = form.save(commit=False)
            vaccine.pet = pet
            vaccine.save()
            messages.success(request, '疫苗記錄新增成功！')
            return redirect('health_rec')
    else:
        form = VaccineRecordForm()
    
    return render(request, 'vaccine&deworm/add_vaccine.html', {
        'form': form,
        'pet': pet
    })

@login_required
@require_owner
def edit_vaccine(request, pet_id, vaccine_id):
    """編輯疫苗記錄"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    vaccine = get_object_or_404(VaccineRecord, id=vaccine_id, pet=pet)
    
    if request.method == 'POST':
        form = VaccineRecordForm(request.POST, instance=vaccine)
        if form.is_valid():
            form.save()
            messages.success(request, '疫苗記錄更新成功！')
            return redirect('health_rec')
    else:
        form = VaccineRecordForm(instance=vaccine)
    
    return render(request, 'vaccine&deworm/edit_vaccine.html', {
        'form': form,
        'pet': pet,
        'vaccine': vaccine
    })

@login_required
@require_owner
def delete_vaccine(request, vaccine_id):
    """刪除疫苗記錄"""
    vaccine = get_object_or_404(VaccineRecord, id=vaccine_id)
    
    # 檢查權限
    if vaccine.pet.owner != request.user:
        messages.error(request, '無權限刪除此記錄')
        return redirect('health_rec')
    
    if request.method == 'POST':
        vaccine.delete()
        messages.success(request, '疫苗記錄刪除成功！')
    
    return redirect('health_rec')

# ============ 驅蟲記錄管理 ============

@login_required
@require_owner
def add_deworm(request, pet_id):
    """新增驅蟲記錄"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    
    if request.method == 'POST':
        form = DewormRecordForm(request.POST)
        if form.is_valid():
            deworm = form.save(commit=False)
            deworm.pet = pet
            deworm.save()
            messages.success(request, '驅蟲記錄新增成功！')
            return redirect('health_rec')
    else:
        form = DewormRecordForm()
    
    return render(request, 'vaccine&deworm/add_deworm.html', {
        'form': form,
        'pet': pet
    })

@login_required
@require_owner
def edit_deworm(request, pet_id, deworm_id):
    """編輯驅蟲記錄"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    deworm = get_object_or_404(DewormRecord, id=deworm_id, pet=pet)
    
    if request.method == 'POST':
        form = DewormRecordForm(request.POST, instance=deworm)
        if form.is_valid():
            form.save()
            messages.success(request, '驅蟲記錄更新成功！')
            return redirect('health_rec')
    else:
        form = DewormRecordForm(instance=deworm)
    
    return render(request, 'vaccine&deworm/edit_deworm.html', {
        'form': form,
        'pet': pet,
        'deworm': deworm
    })

@login_required
@require_owner
def delete_deworm(request, deworm_id):
    """刪除驅蟲記錄"""
    deworm = get_object_or_404(DewormRecord, id=deworm_id)
    
    # 檢查權限
    if deworm.pet.owner != request.user:
        messages.error(request, '無權限刪除此記錄')
        return redirect('health_rec')
    
    if request.method == 'POST':
        deworm.delete()
        messages.success(request, '驅蟲記錄刪除成功！')
    
    return redirect('health_rec')

# ============ 獸醫師疫苗和驅蟲記錄管理 ============
@login_required
@require_verified_vet(optional=True)
def vet_add_vaccine(request, pet_id):
    """獸醫師新增疫苗記錄"""
    try:
        vet_profile = request.user.vet_profile
    except:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')

    pet = get_object_or_404(Pet, id=pet_id)

    # 檢查獸醫師是否有權限為此寵物建立記錄（通過預約關聯）
    if not VetAppointment.objects.filter(
        slot__doctor=vet_profile,
        pet=pet
    ).exists():
        messages.error(request, '您沒有權限為此寵物新增記錄')
        return redirect('vet_home')

    if request.method == 'POST':
        form = VaccineRecordForm(request.POST)
        if form.is_valid():
            vaccine = form.save(commit=False)
            vaccine.pet = pet
            vaccine.vet = vet_profile
            vaccine.save()
            messages.success(request, '疫苗記錄新增成功！')
            return redirect('pet_detail', pet_id=pet.id)
    else:
        # 設定預設值 - 施打地點預設為獸醫師的診所名稱
        initial_data = {}
        if hasattr(vet_profile, 'clinic') and vet_profile.clinic:
            initial_data['location'] = vet_profile.clinic.clinic_name
        elif hasattr(vet_profile, 'clinic_name') and vet_profile.clinic_name:
            initial_data['location'] = vet_profile.clinic_name

        form = VaccineRecordForm(initial=initial_data)

    return render(request, 'vet_pages/add_vaccine_record.html', {
        'form': form,
        'pet': pet,
        'vet_profile': vet_profile
    })

@login_required
@require_verified_vet(optional=True)
def vet_add_deworm(request, pet_id):
    """獸醫師新增驅蟲記錄"""
    try:
        vet_profile = request.user.vet_profile
    except:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')

    pet = get_object_or_404(Pet, id=pet_id)

    # 檢查獸醫師是否有權限為此寵物建立記錄（通過預約關聯）
    if not VetAppointment.objects.filter(
        slot__doctor=vet_profile,
        pet=pet
    ).exists():
        messages.error(request, '您沒有權限為此寵物新增記錄')
        return redirect('vet_home')

    if request.method == 'POST':
        form = DewormRecordForm(request.POST)
        if form.is_valid():
            deworm = form.save(commit=False)
            deworm.pet = pet
            deworm.vet = vet_profile
            deworm.save()
            messages.success(request, '驅蟲記錄新增成功！')
            return redirect('pet_detail', pet_id=pet.id)
    else:
        # 設定預設值 - 施打地點預設為獸醫師的診所名稱
        initial_data = {}
        if hasattr(vet_profile, 'clinic') and vet_profile.clinic:
            initial_data['location'] = vet_profile.clinic.clinic_name
        elif hasattr(vet_profile, 'clinic_name') and vet_profile.clinic_name:
            initial_data['location'] = vet_profile.clinic_name

        form = DewormRecordForm(initial=initial_data)

    return render(request, 'vet_pages/add_deworm_record.html', {
        'form': form,
        'pet': pet,
        'vet_profile': vet_profile
    })

# ============ 報告管理 ============

@login_required
@require_owner
def add_report(request, pet_id):
    """新增報告"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.pet = pet
            report.save()
            messages.success(request, '報告上傳成功！')
            return redirect('health_rec')
    else:
        form = ReportForm()
    
    return render(request, 'vaccine&deworm/add_report.html', {
        'form': form,
        'pet': pet
    })

@login_required
@check_pet_ownership
def delete_report(request, report_id):
    """刪除報告"""
    report = get_object_or_404(Report, id=report_id)
    
    # 檢查權限
    if report.pet.owner != request.user:
        messages.error(request, '無權限刪除此報告')
        return redirect('health_rec')
    
    if request.method == 'POST':
        report.delete()
        messages.success(request, '報告刪除成功！')
    
    return redirect('health_rec')

# ============ 獸醫師報告管理 ============

@login_required
def upload_report(request, pet_id):
    """獸醫師上傳報告"""
    # 檢測是否為 AJAX 請求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        vet_profile = request.user.vet_profile
    except:
        error_msg = '只有獸醫師可以上傳報告'
        messages.error(request, error_msg)
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg})
        return redirect('vet_home')

    pet = get_object_or_404(Pet, id=pet_id)

    # 檢查獸醫師權限 - 是否曾經看過這隻寵物
    if not VetAppointment.objects.filter(
        slot__doctor=vet_profile,
        pet=pet
    ).exists():
        error_msg = '您沒有權限為此寵物上傳報告'
        messages.error(request, error_msg)
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg})
        return redirect('vet_home')

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                # 處理Profile關係 - 每個user只能有一個Profile
                vet_profile_obj = None
                try:
                    # 首先試著找account_type='vet'的Profile
                    vet_profile_obj = Profile.objects.get(user=vet_profile.user, account_type='vet')
                except Profile.DoesNotExist:
                    # 如果沒有找到vet類型的Profile，看看是否有其他類型的Profile
                    try:
                        existing_profile = Profile.objects.get(user=vet_profile.user)
                        # 直接使用現有的Profile，不管account_type是什麼
                        # 因為Report模型雖然有limit_choices_to，但實際上可以接受任何Profile
                        vet_profile_obj = existing_profile
                    except Profile.DoesNotExist:
                        # 如果完全沒有Profile，創建一個新的
                        vet_profile_obj = Profile.objects.create(
                            user=vet_profile.user,
                            account_type='vet',
                            phone_number=''
                        )

                # 取得獸醫師的診所資訊作為檢驗地點
                clinic = None
                try:
                    clinic = vet_profile.clinic
                except:
                    pass

                # 建立報告，包含檢驗地點
                report = Report.objects.create(
                    pet=pet,
                    vet=vet_profile_obj,
                    clinic=clinic,
                    title=form.cleaned_data['title'],
                    pdf=form.cleaned_data['pdf']
                )

                messages.success(request, f'報告「{form.cleaned_data["title"]}」上傳成功！')

                # 檢查是否為 AJAX 請求
                if is_ajax:
                    return JsonResponse({'success': True, 'message': f'報告「{form.cleaned_data["title"]}」上傳成功！'})

                return redirect('pet_detail', pet_id=pet_id)

            except Exception as e:
                error_message = f'報告上傳失敗：{str(e)}'
                messages.error(request, error_message)

                # 檢查是否為 AJAX 請求
                if is_ajax:
                    return JsonResponse({'success': False, 'error': error_message})

        else:
            error_message = '表單有誤，請檢查輸入內容'
            messages.error(request, error_message)

            # 檢查是否為 AJAX 請求
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_message})
    else:
        form = ReportForm()

    # GET 請求或POST有錯誤時顯示上傳表單
    context = {
        'form': form,
        'pet': pet,
    }
    return render(request, 'vaccine&deworm/add_report.html', context)

@login_required
def delete_vet_report(request, report_id):
    """獸醫師刪除報告"""
    try:
        vet_profile = request.user.vet_profile
    except:
        messages.error(request, '只有獸醫師可以刪除報告')
        return redirect('vet_home')

    report = get_object_or_404(Report, id=report_id)
    pet_id = report.pet.id

    # 檢查權限 - 只有上傳該報告的獸醫師或有權限看這隻寵物的獸醫師可以刪除
    if (report.vet.user != request.user and
        not VetAppointment.objects.filter(slot__doctor=vet_profile, pet=report.pet).exists()):
        messages.error(request, '您沒有權限刪除此報告')
        return redirect('pet_detail', pet_id=pet_id)

    try:
        report_title = report.title
        report.delete()
        messages.success(request, f'報告「{report_title}」刪除成功！')
    except Exception as e:
        messages.error(request, f'刪除報告失敗：{str(e)}')

    return redirect('pet_detail', pet_id=pet_id)

# ============ 地圖功能 ============

def map_home(request):
    """地圖首頁"""
    return render(request, 'petmap/map.html')

def api_locations(request):
    """API:獲取位置資料"""
    try:
        locations = PetLocation.objects.all()
        data = []
        for location in locations:
            data.append({
                'id': location.id,
                'name': location.name,
                'lat': float(location.latitude),
                'lng': float(location.longitude),
                'type': location.location_type,
                'address': location.address,
                'phone': location.phone,
            })
        return JsonResponse({'locations': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def emergency_map_home(request):
    """緊急地圖首頁"""
    return render(request, 'petmap/emergency_map.html')

def api_emergency_locations(request):
    """API:獲取緊急位置資料"""
    try:
        locations = PetLocation.objects.filter(is_emergency=True)
        data = []
        for location in locations:
            data.append({
                'id': location.id,
                'name': location.name,
                'lat': float(location.latitude),
                'lng': float(location.longitude),
                'type': location.location_type,
                'address': location.address,
                'phone': location.phone,
                'is_24h': location.is_24_hour,
            })
        return JsonResponse({'locations': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


    """獲取通知數量"""
    # 實際實作時計算未讀通知數量
    count = 0
    return JsonResponse({'count': count})

# ============ 預約系統（基本實作） ============

@login_required
@require_owner
def create_appointment(request, pet_id):
    """建立預約 - 新版簡化流程"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 獲取表單數據
                clinic_id = request.POST.get('selected_clinic')
                doctor_id = request.POST.get('selected_doctor')
                slot_id = request.POST.get('selected_slot')
                reason = request.POST.get('reason', '')
                notes = request.POST.get('notes', '')
                contact_phone = request.POST.get('contact_phone', '')
                appointment_date = request.POST.get('appointment_date')
                
                # 驗證必要欄位
                if not clinic_id:
                    messages.error(request, '請選擇診所')
                    # 獲取用戶電話號碼用於錯誤時重新顯示表單
                    user_phone = getattr(request.user.profile, 'phone_number', '') if hasattr(request.user, 'profile') else ''
                    return render(request, 'appointments/create_appointment.html', {'pet': pet, 'user_phone': user_phone})
                    
                if not contact_phone:
                    messages.error(request, '請輸入聯絡電話')
                    user_phone = getattr(request.user.profile, 'phone_number', '') if hasattr(request.user, 'profile') else ''
                    return render(request, 'appointments/create_appointment.html', {'pet': pet, 'user_phone': user_phone})
                    
                if not appointment_date:
                    messages.error(request, '請選擇預約日期')
                    user_phone = getattr(request.user.profile, 'phone_number', '') if hasattr(request.user, 'profile') else ''
                    return render(request, 'appointments/create_appointment.html', {'pet': pet, 'user_phone': user_phone})
                    
                if not slot_id:
                    messages.error(request, '請選擇預約時段')
                    user_phone = getattr(request.user.profile, 'phone_number', '') if hasattr(request.user, 'profile') else ''
                    return render(request, 'appointments/create_appointment.html', {'pet': pet, 'user_phone': user_phone})
                
                # 獲取診所
                clinic = get_object_or_404(VetClinic, id=clinic_id, is_verified=True)
                
                # 解析日期和時間（提前解析，用於醫師分配）
                from datetime import datetime, date
                appointment_date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
                slot_time = parse_slot_id(slot_id)

                # 獲取醫師（如果指定）
                doctor = None
                if doctor_id and doctor_id != 'null':
                    doctor = get_object_or_404(VetDoctor, id=doctor_id, clinic=clinic, is_active=True, is_active_veterinarian=True)
                else:
                    # 如果沒有指定醫師，根據時段智能分配醫師
                    doctor = find_best_doctor_for_slot(clinic, appointment_date_obj, slot_time)
                    if not doctor:
                        messages.error(request, '該診所在此時段沒有可用的醫師，請選擇其他時段')
                        user_phone = getattr(request.user.profile, 'phone_number', '') if hasattr(request.user, 'profile') else ''
                        return render(request, 'appointments/create_appointment.html', {'pet': pet, 'user_phone': user_phone})
                
                # 創建或獲取對應的時段
                appointment_slot, created = AppointmentSlot.objects.get_or_create(
                    clinic=clinic,
                    doctor=doctor,
                    date=appointment_date_obj,
                    start_time=slot_time,
                    defaults={
                        'end_time': add_minutes_to_time(slot_time, 30),  # 預設30分鐘
                        'max_bookings': 1,
                        'current_bookings': 0,
                        'is_available': True,
                        'source': 'online'
                    }
                )
                
                # 創建預約記錄
                appointment = VetAppointment.objects.create(
                    pet=pet,
                    owner=request.user,
                    slot=appointment_slot,
                    reason=reason,
                    notes=notes,
                    contact_phone=contact_phone,
                    status='pending'  # 新預約預設為待確認
                )
                
                messages.success(request, f'預約申請已送出！診所將盡快與您聯絡確認。預約編號:{appointment.id}')
                return redirect('my_appointments')
                
        except Exception as e:
            print(f"預約建立錯誤: {e}")
            import traceback
            traceback.print_exc()
            
            # 提供更具體的錯誤信息
            error_message = '預約建立失敗，請稍後再試'
            if 'AppointmentSlot' in str(e):
                error_message = '時段創建失敗，請選擇其他時段'
            elif 'VetAppointment' in str(e):
                error_message = '預約記錄創建失敗，請檢查填寫的資料'
            elif 'doctor' in str(e).lower():
                error_message = '醫師資料有問題，請選擇其他診所或醫師'
                
            messages.error(request, error_message)
            user_phone = getattr(request.user.profile, 'phone_number', '') if hasattr(request.user, 'profile') else ''
            return render(request, 'appointments/create_appointment.html', {'pet': pet, 'user_phone': user_phone})
    
    # GET 請求顯示表單
    # 獲取用戶的電話號碼
    user_phone = ''
    try:
        if hasattr(request.user, 'profile') and request.user.profile.phone_number:
            user_phone = request.user.profile.phone_number
    except:
        user_phone = ''
    
    context = {
        'pet': pet,
        'user_phone': user_phone
    }
    return render(request, 'appointments/create_appointment.html', context)

def parse_slot_id(slot_id):
    """解析時段ID為時間物件 - 支援多種格式"""
    import logging
    from datetime import time

    logger = logging.getLogger(__name__)
    logger.info(f"解析時段ID: '{slot_id}' (類型: {type(slot_id)})")

    try:
        # 確保slot_id是字符串
        slot_id = str(slot_id).strip()

        # 嘗試解析 "HH:MM" 格式
        if ':' in slot_id:
            hour, minute = slot_id.split(':')
            result_time = time(int(hour), int(minute))
            logger.info(f"成功解析 HH:MM 格式 -> {result_time}")
            return result_time
        # 嘗試解析 "HH-MM" 格式
        elif '-' in slot_id:
            hour, minute = slot_id.split('-')
            result_time = time(int(hour), int(minute))
            logger.info(f"成功解析 HH-MM 格式 -> {result_time}")
            return result_time
        else:
            # 如果是純數字，假設是小時
            hour = int(slot_id)
            result_time = time(hour, 0)
            logger.info(f"純數字格式解析 -> {result_time}")
            return result_time
    except (ValueError, AttributeError, TypeError) as e:
        logger.error(f"無法解析時段ID '{slot_id}'，錯誤：{e}")
        logger.warning(f"使用預設時間 09:00")
        return time(9, 0)  # 預設上午9點

def find_best_doctor_for_slot(clinic, appointment_date, slot_time):
    """根據時段智能分配最合適的醫師"""
    from datetime import datetime
    try:
        weekday = appointment_date.weekday()

        # 查找在該時段有排班的醫師
        available_doctors = []

        # 查找活躍的排班
        enhanced_schedules = EnhancedVetSchedule.objects.filter(
            doctor__clinic=clinic,
            doctor__is_active=True,
            doctor__is_active_veterinarian=True,
            status='active',
            start_date__lte=appointment_date
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=appointment_date)
        )

        for schedule in enhanced_schedules:
            # 檢查該排班是否包含今天的工作日
            if weekday in schedule.weekdays:
                # 獲取該工作日的時段設定
                day_slots = schedule.daily_time_slots.get(str(weekday), [])

                for time_slot in day_slots:
                    try:
                        start_time = datetime.strptime(time_slot['start'], '%H:%M').time()
                        end_time = datetime.strptime(time_slot['end'], '%H:%M').time()

                        # 檢查請求的時段是否在醫師的工作時間內
                        if start_time <= slot_time < end_time:
                            # 檢查該醫師在此時段是否已有預約
                            existing_appointment = VetAppointment.objects.filter(
                                slot__doctor=schedule.doctor,
                                slot__date=appointment_date,
                                slot__start_time=slot_time,
                                status__in=['confirmed', 'pending']
                            ).exists()

                            if not existing_appointment:
                                available_doctors.append(schedule.doctor)
                                break  # 找到一個可用時段就足夠了
                    except (ValueError, KeyError):
                        continue

        # 如果找到可用醫師，返回第一個（或根據其他邏輯選擇）
        if available_doctors:
            return available_doctors[0]

        return None

    except Exception as e:
        print(f"智能醫師分配錯誤: {e}")
        return None

@login_required
@require_clinic_management
def create_walkin_appointment(request):
    """診所管理員創建現場預約"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
    except:
        messages.error(request, '只有診所管理員可以創建現場預約')
        return redirect('clinic_dashboard')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 獲取表單資料
                owner_name = request.POST.get('owner_name', '').strip()
                owner_phone = request.POST.get('owner_phone', '').strip()
                pet_name = request.POST.get('pet_name', '').strip()
                pet_species = request.POST.get('pet_species', 'dog')
                pet_breed = request.POST.get('pet_breed', '').strip()
                appointment_date = request.POST.get('appointment_date')
                time_slot = request.POST.get('time_slot')
                selected_doctor_id = request.POST.get('selected_doctor')
                reason = request.POST.get('reason', '現場就診').strip()
                notes = request.POST.get('notes', '').strip()
                
                # 驗證必要欄位
                if not all([owner_name, owner_phone, pet_name, appointment_date, time_slot, selected_doctor_id]):
                    messages.error(request, '請填寫所有必要欄位並選擇醫師')
                    return render(request, 'clinic/create_walkin_appointment.html', {
                        'clinic': clinic,
                        'vet_profile': vet_profile
                    })
                
                # 解析時間
                try:
                    appointment_date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
                    start_time_obj = datetime.strptime(time_slot, '%H:%M').time()
                    end_time_obj = add_minutes_to_time(start_time_obj, 30)
                except ValueError:
                    messages.error(request, '日期或時間格式錯誤')
                    return render(request, 'clinic/create_walkin_appointment.html', {
                        'clinic': clinic,
                        'vet_profile': vet_profile
                    })
                
                # 獲取選定的醫師
                try:
                    selected_doctor = VetDoctor.objects.get(
                        id=selected_doctor_id,
                        clinic=clinic,
                        is_active=True,
                        is_active_veterinarian=True  # 確保醫師具有獸醫師身份
                    )
                except VetDoctor.DoesNotExist:
                    messages.error(request, '選定的醫師不存在或不具有獸醫師身份')
                    return render(request, 'clinic/create_walkin_appointment.html', {
                        'clinic': clinic,
                        'vet_profile': vet_profile
                    })
                
                # 檢查時段是否已被預約
                existing_slot = AppointmentSlot.objects.filter(
                    doctor=selected_doctor,
                    clinic=clinic,
                    date=appointment_date_obj,
                    start_time=start_time_obj
                ).first()
                
                if existing_slot and hasattr(existing_slot, 'vetappointment'):
                    messages.error(request, f'醫師 {selected_doctor.user.get_full_name()} 在 {time_slot} 時段已被預約')
                    return render(request, 'clinic/create_walkin_appointment.html', {
                        'clinic': clinic,
                        'vet_profile': vet_profile
                    })
                
                # 尋找或創建飼主用戶
                owner_user = None
                try:
                    # 嘗試用電話號碼找到現有用戶
                    owner_profile = Profile.objects.filter(phone_number=owner_phone).first()
                    if owner_profile:
                        owner_user = owner_profile.user
                    else:
                        # 創建新用戶（臨時）
                        import time as time_module
                        username = f"walkin_{owner_phone}_{int(time_module.time())}"
                        owner_user = User.objects.create_user(
                            username=username,
                            first_name=owner_name.split()[-1] if owner_name.split() else owner_name,
                            last_name=owner_name.split()[0] if len(owner_name.split()) > 1 else '',
                            email=f"{username}@temp.local"
                        )
                        # 創建 Profile
                        Profile.objects.create(
                            user=owner_user,
                            phone_number=owner_phone,
                            account_type='owner'
                        )
                except Exception as e:
                    print(f"創建飼主用戶錯誤: {e}")
                    import traceback
                    traceback.print_exc()
                    print(f"飼主資料: name={owner_name}, phone={owner_phone}")
                    messages.error(request, f'飼主資料處理失敗: {str(e)}')
                    return render(request, 'clinic/create_walkin_appointment.html', {
                        'clinic': clinic,
                        'vet_profile': vet_profile
                    })
                
                # 尋找或創建寵物
                try:
                    pet = Pet.objects.filter(
                        owner=owner_user,
                        name=pet_name
                    ).first()
                    
                    if not pet:
                        pet = Pet.objects.create(
                            owner=owner_user,
                            name=pet_name,
                            species=pet_species,
                            breed=pet_breed if pet_breed else '混種',
                            birth_date=None,  # 現場預約可能不知道生日
                            gender='unknown'  # 預設未知
                        )
                except Exception as e:
                    print(f"創建寵物錯誤: {e}")
                    messages.error(request, '寵物資料處理失敗')
                    return render(request, 'clinic/create_walkin_appointment.html', {
                        'clinic': clinic,
                        'vet_profile': vet_profile
                    })
                
                # 創建或使用現有時段
                if not existing_slot:
                    appointment_slot = AppointmentSlot.objects.create(
                        doctor=selected_doctor,
                        clinic=clinic,
                        date=appointment_date_obj,
                        start_time=start_time_obj,
                        end_time=end_time_obj,
                        is_available=False,  # 立即標記為不可用
                        source='walkin'
                    )
                else:
                    appointment_slot = existing_slot
                    appointment_slot.is_available = False
                    appointment_slot.save()
                
                # 創建預約記錄
                appointment = VetAppointment.objects.create(
                    pet=pet,
                    owner=owner_user,
                    slot=appointment_slot,
                    reason=reason,
                    notes=notes,
                    contact_phone=owner_phone,
                    booking_type='walkin',  # 重要：設定為現場預約
                    status='confirmed'  # 現場預約直接確認
                )
                
                messages.success(request, 
                    f'現場預約已成功創建！<br>'
                    f'飼主：{owner_name}<br>'
                    f'寵物：{pet_name}<br>'
                    f'醫師：{selected_doctor.user.get_full_name()}<br>'
                    f'時間：{appointment_date} {time_slot}<br>'
                    f'預約編號：{appointment.id}'
                )
                return redirect('clinic_appointments')
                
        except Exception as e:
            print(f"現場預約創建錯誤: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, '現場預約創建失敗，請稍後再試')
            return render(request, 'clinic/create_walkin_appointment.html', {
                'clinic': clinic,
                'vet_profile': vet_profile
            })
    
    # GET 請求顯示表單
    # 獲取今天的日期作為預設值
    today = timezone.now().date()
    
    # 獲取診所的醫師列表
    doctors = VetDoctor.objects.filter(
        clinic=clinic,
        is_active=True,
        is_active_veterinarian=True  # 只顯示啟用獸醫師身份的醫師
    ).select_related('user')
    
    context = {
        'clinic': clinic,
        'vet_profile': vet_profile,
        'doctors': doctors,
        'today': today.strftime('%Y-%m-%d')
    }
    return render(request, 'clinic/create_walkin_appointment.html', context)

def add_minutes_to_time(time_obj, minutes):
    """為時間物件增加分鐘數"""
    from datetime import datetime, timedelta, time
    # 轉換為datetime進行計算
    temp_datetime = datetime.combine(datetime.today(), time_obj)
    temp_datetime += timedelta(minutes=minutes)
    return temp_datetime.time()

@login_required
def create_appointment_old(request, pet_id):
    """建立預約 - 舊版本（保留作為備用）"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    
    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 獲取表單數據
                    clinic = form.cleaned_data['clinic']
                    doctor = form.cleaned_data.get('doctor')
                    appointment_date = form.cleaned_data['appointment_date']
                    time_slot = form.cleaned_data['time_slot']
                    reason = form.cleaned_data.get('reason', '')
                    notes = form.cleaned_data.get('notes', '')
                    contact_phone = form.cleaned_data.get('contact_phone', '')
                    
                    # 創建預約記錄
                    appointment = VetAppointment.objects.create(
                        pet=pet,
                        owner=request.user,
                        slot=time_slot,
                        reason=reason,
                        notes=notes,
                        contact_phone=contact_phone,
                        status='confirmed'
                    )
                    
                    messages.success(request, '預約建立成功！')
                    return redirect('appointment_success', appointment_id=appointment.id)
            except Exception as e:
                messages.error(request, f'預約失敗:{str(e)}')
    else:
        form = AppointmentBookingForm()
    
    return render(request, 'appointments/create_appointment.html', {
        'form': form,
        'pet': pet
    })

def search_clinics(request):
    """AJAX搜索診所 - 支援新的預約系統"""
    try:
        
        # 簡化查詢，只取前10個已驗證的診所
        clinics = VetClinic.objects.filter(is_verified=True).order_by('clinic_name')[:10]
        
        clinic_data = []
        for clinic in clinics:
            try:
                # 簡化醫師數量計算
                doctor_count = 0
                try:
                    doctor_count = clinic.vetdoctor_set.filter(is_active=True).count()
                except:
                    doctor_count = 0
                
                clinic_info = {
                    'id': clinic.id,
                    'name': clinic.clinic_name,
                    'address': clinic.clinic_address,
                    'phone': clinic.clinic_phone or '未提供',
                    'rating': 4.5,
                    'doctor_count': doctor_count,
                    'distance': 5.2
                }
                clinic_data.append(clinic_info)
                
            except Exception as clinic_error:
                continue
        
        response_data = {
            'status': 'success', 
            'clinics': clinic_data,
            'total': len(clinic_data)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"搜索診所主要錯誤: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'clinics': []
        })

def test_clinics_api(request):
    """測試診所 API - 簡化版本"""
    return JsonResponse({
        'status': 'success',
        'clinics': [
            {
                'id': 1,
                'name': '測試診所',
                'address': '測試地址',
                'phone': '0900-000-000',
                'rating': 4.5,
                'doctor_count': 2,
                'distance': 1.5
            }
        ],
        'total': 1
    })

@login_required 
def load_doctors(request):
    """AJAX載入診所醫師"""
    clinic_id = request.GET.get('clinic_id')
    if not clinic_id:
        return JsonResponse({
            'status': 'success',
            'doctors': []
        })
    
    try:
        doctors = VetDoctor.objects.filter(
            clinic_id=clinic_id, 
            is_active=True,
            is_active_veterinarian=True  # 只顯示啟用獸醫師身份的醫師
        ).order_by('user__first_name', 'user__last_name')
        
        doctor_data = [
            {
                'id': doctor.id,
                'name': doctor.user.get_full_name() or doctor.user.username,
                'specialty': getattr(doctor, 'specialty', '')
            }
            for doctor in doctors
        ]
        
        return JsonResponse({
            'status': 'success',
            'doctors': doctor_data
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def appointment_success(request, appointment_id):
    """預約成功頁面"""
    appointment = get_object_or_404(VetAppointment, id=appointment_id)
    
    # 檢查權限
    if appointment.owner != request.user:
        messages.error(request, '無權限查看此預約')
        return redirect('home')
    
    return render(request, 'appointments/appointment_success.html', {
        'appointment': appointment
    })

@login_required
@require_owner
def my_appointments(request):
    """我的預約 - 增強版包含醫療記錄詳情"""
    appointments = VetAppointment.objects.filter(
        owner=request.user
    ).select_related(
        'pet', 'slot__doctor__user', 'slot__clinic'
    ).prefetch_related(
        'pet__medicalrecord_set__attending_vet__user'
    )

    # 進階篩選參數
    status_filter = request.GET.get('status', 'all')
    date_range_filter = request.GET.get('date_range', 'all')
    search_query = request.GET.get('search', '').strip()

    today = timezone.now().date()
    now = timezone.now()

    # 狀態篩選
    if status_filter == 'active':
        # 進行中的預約（待確認 + 已確認）
        appointments = appointments.filter(
            status__in=['pending', 'confirmed']
        )
    elif status_filter in ['pending', 'confirmed', 'completed', 'cancelled']:
        # 特定狀態篩選
        appointments = appointments.filter(status=status_filter)
    # status_filter == 'all' 時不做篩選，顯示所有預約

    # 日期範圍篩選
    if date_range_filter != 'all':
        if date_range_filter == 'today':
            appointments = appointments.filter(slot__date=today)
        elif date_range_filter == 'tomorrow':
            tomorrow = today + timezone.timedelta(days=1)
            appointments = appointments.filter(slot__date=tomorrow)
        elif date_range_filter == 'past-week':
            past_week = today - timezone.timedelta(days=7)
            appointments = appointments.filter(slot__date__gte=past_week, slot__date__lt=today)
        elif date_range_filter == 'current-week':
            # 本週：從這週的星期一到星期日
            start_week = today - timezone.timedelta(days=today.weekday())
            end_week = start_week + timezone.timedelta(days=6)
            appointments = appointments.filter(slot__date__gte=start_week, slot__date__lte=end_week)
        elif date_range_filter == 'next-week':
            # 下週：下週一到下週日
            next_week_start = today + timezone.timedelta(days=(7 - today.weekday()))
            next_week_end = next_week_start + timezone.timedelta(days=6)
            appointments = appointments.filter(slot__date__gte=next_week_start, slot__date__lte=next_week_end)
        elif date_range_filter == 'current-month':
            # 本月
            first_day = today.replace(day=1)
            if today.month == 12:
                last_day = today.replace(year=today.year + 1, month=1, day=1) - timezone.timedelta(days=1)
            else:
                last_day = today.replace(month=today.month + 1, day=1) - timezone.timedelta(days=1)
            appointments = appointments.filter(slot__date__gte=first_day, slot__date__lte=last_day)
        elif date_range_filter == 'next-month':
            # 下月
            if today.month == 12:
                first_day = today.replace(year=today.year + 1, month=1, day=1)
                last_day = today.replace(year=today.year + 1, month=2, day=1) - timezone.timedelta(days=1)
            else:
                first_day = today.replace(month=today.month + 1, day=1)
                if today.month == 11:
                    last_day = today.replace(year=today.year + 1, month=1, day=1) - timezone.timedelta(days=1)
                else:
                    last_day = today.replace(month=today.month + 2, day=1) - timezone.timedelta(days=1)
            appointments = appointments.filter(slot__date__gte=first_day, slot__date__lte=last_day)


    # 搜尋篩選
    if search_query:
        from django.db.models import Q
        appointments = appointments.filter(
            Q(pet__name__icontains=search_query) |
            Q(slot__clinic__name__icontains=search_query) |
            Q(slot__doctor__user__first_name__icontains=search_query) |
            Q(slot__doctor__user__last_name__icontains=search_query) |
            Q(reason__icontains=search_query)
        )

    appointments = appointments.order_by('-created_at')

    # 為每個預約添加相關的醫療記錄
    enhanced_appointments = []
    for appointment in appointments:
        # 查找該預約相關的醫療記錄（根據日期和寵物匹配）
        appointment_date = appointment.slot.date
        medical_record = MedicalRecord.objects.filter(
            pet=appointment.pet,
            visit_date=appointment_date
        ).select_related('attending_vet__user').first()

        # medical_details 現在是 @property，自動解析

        enhanced_appointments.append({
            'appointment': appointment,
            'medical_record': medical_record,
            'medical_details': medical_record.medical_details if medical_record else None,
            'has_detailed_record': medical_record is not None
        })

    # 分頁處理
    paginator = Paginator(enhanced_appointments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'appointments/my_appointments.html', {
        'appointments': page_obj,
        'page_obj': page_obj,
        'today': today,
        'status_filter': status_filter,
        'enhanced_view': True
    })

@login_required
def cancel_appointment(request, appointment_id):
    """取消預約"""
    appointment = get_object_or_404(VetAppointment, id=appointment_id, owner=request.user)

    if request.method == 'POST':
        cancel_reason = request.POST.get('cancel_reason', '')
        appointment.status = 'cancelled'
        appointment.cancel_reason = cancel_reason
        appointment.save()

        # 在成功訊息中包含取消原因
        if cancel_reason:
            messages.success(request, f'預約取消成功！取消原因：{cancel_reason}')
        else:
            messages.success(request, '預約取消成功！')

        # 如果是AJAX請求，返回JSON響應
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': '預約取消成功！'})

        return redirect('my_appointments')

    return render(request, 'appointments/cancel_appointment.html', {
        'appointment': appointment
    })

# ============ 診所註冊和管理系統 ============

def clinic_registration(request):
    """診所註冊"""
    # 移除登入檢查，允許未登入用戶註冊診所
    
    if request.method == 'POST':
        form = VetClinicRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 建立診所 - form.save() 會自動創建管理員用戶並設置 clinic_admin
                    clinic = form.save()  # 直接保存，不要 commit=False
                    
                    # 驗證診所執照
                    success, message = clinic.verify_with_moa_api()
                    
                    if success:
                        # 取得表單創建的管理員用戶
                        admin_user = clinic.clinic_admin
                        
                        # 建立或更新獸醫師檔案
                        vet_profile, created = VetDoctor.objects.update_or_create(
                            user=admin_user,
                            defaults={
                                'clinic': clinic,
                                'is_clinic_admin': True,
                                'license_verified_with_moa': True,
                                'verification_date': timezone.now()
                            }
                        )
                        
                        # 安全的自動登入 - 避免 session 衝突
                        from django.contrib.auth import login
                        
                        # 先清理當前 session，確保乾淨的狀態
                        request.session.flush()
                        
                        # 重新生成 session key
                        request.session.create()
                        
                        # 登入新用戶
                        login(request, admin_user, backend='django.contrib.auth.backends.ModelBackend')
                        
                        # 手動保存 session
                        request.session.save()
                        
                        messages.success(request, f'診所註冊成功！{message}')
                        return redirect('clinic_registration_success', clinic_id=clinic.id)
                    else:
                        clinic.delete()  # 回滾診所建立
                        messages.error(request, f'診所驗證失敗:{message}')
                        
            except Exception as e:
                messages.error(request, f'註冊過程發生錯誤:{str(e)}')
    else:
        form = VetClinicRegistrationForm()
    
    return render(request, 'clinic/registration.html', {'form': form})

@login_required
def clinic_registration_success(request, clinic_id):
    """診所註冊成功頁面"""
    clinic = get_object_or_404(VetClinic, id=clinic_id, clinic_admin=request.user)
    
    return render(request, 'clinic/registration_success.html', {
        'clinic': clinic
    })

@login_required
@require_clinic_management
def clinic_dashboard(request):
    """診所儀表板"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 獲取今日統計
        today = timezone.now().date()
        today_appointments = VetAppointment.objects.filter(
            slot__doctor__clinic=clinic,
            slot__date=today
        )
        
        # 獲取本月統計
        month_start = today.replace(day=1)
        month_appointments = VetAppointment.objects.filter(
            slot__doctor__clinic=clinic,
            slot__date__range=[month_start, today]
        )
        
        # 獲取診所醫師
        doctors = VetDoctor.objects.filter(
            clinic=clinic,
            is_active=True
        ).select_related('user')
        
        return render(request, 'clinic/dashboard.html', {
            'vet_profile': vet_profile,
            'clinic': clinic,
            'today_appointments': today_appointments.count(),
            'pending_appointments': today_appointments.filter(status='pending').count(),
            'doctors_count': doctors.count(),
            'total_appointments_this_month': month_appointments.count(),
            'stats': {
                'today_total': today_appointments.count(),
                'today_confirmed': today_appointments.filter(status='confirmed').count(),
                'today_pending': today_appointments.filter(status='pending').count(),
                'today_completed': today_appointments.filter(status='completed').count(),
                'active_doctors': doctors.count(),
                'total_patients': Pet.objects.filter(
                    vetappointment__slot__doctor__clinic=clinic
                ).distinct().count()
            },
            'doctors': doctors,
            'recent_appointments': today_appointments.order_by('slot__start_time')[:5]
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f'載入診所儀表板失敗:{str(e)}')
        return redirect('home')

@login_required
def verify_vet_license(request):
    """獸醫執照驗證"""
    try:
        profile = request.user.profile
        if profile.account_type not in ['veterinarian', 'clinic_admin']:
            messages.error(request, '只有獸醫師可以進行執照驗證')
            return redirect('home')
    except AttributeError:
        messages.error(request, '請先完成個人資料設定')
        return redirect('edit_profile')
    
    if request.method == 'POST':
        form = LicenseVerificationForm,(request.POST, request.FILES)
        if form.is_valid():
            try:
                # 這裡可以加入執照驗證邏輯
                # 例如:向農委會 API 驗證執照
                
                # 暫時直接標記為已驗證（實際應該要有驗證流程）
                vet_profile, created = VetDoctor.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'license_verified_with_moa': True,
                        'verification_date': timezone.now(),
                        'license_number': form.cleaned_data['license_number']
                    }
                )
                
                messages.success(request, '執照驗證提交成功，請等待審核結果')
                return redirect('vet_home')
                
            except Exception as e:
                messages.error(request, f'驗證過程發生錯誤:{str(e)}')
    else:
        form = LicenseVerificationForm,()
    
    return render(request, 'vet/verify_license.html', {'form': form})

@login_required
@require_clinic_management
def switch_clinic_mode(request, clinic_id):
    """切換診所模式"""
    clinic = get_object_or_404(VetClinic, id=clinic_id)
    
    # 檢查權限
    try:
        vet_profile = request.user.vet_profile
        if vet_profile.clinic != clinic or not vet_profile.is_clinic_admin:
            messages.error(request, '您沒有權限變更診所模式')
            return redirect('clinic_dashboard')
    except AttributeError:
        messages.error(request, '您不是診所成員')
        return redirect('home')
    
    if request.method == 'POST':
        import json

        try:
            # 檢查是否為 JSON 請求
            is_json_request = request.content_type == 'application/json' or 'application/json' in request.META.get('HTTP_ACCEPT', '')

            if is_json_request and request.body:
                # 處理 JSON 請求
                data = json.loads(request.body)
                new_mode = data.get('mode')
            else:
                # 處理表單請求
                new_mode = request.POST.get('mode')

            if new_mode in ['single', 'multi']:
                clinic.clinic_mode = new_mode
                clinic.save()

                mode_name = '單一醫師模式' if new_mode == 'single' else '多醫師模式'

                # 根據請求類型返回不同響應
                if is_json_request:
                    return JsonResponse({
                        'status': 'success',
                        'message': f'診所模式已切換為{mode_name}',
                        'new_mode': new_mode
                    })
                else:
                    messages.success(request, f'診所模式已切換為{mode_name}')
                    return redirect('clinic_dashboard')
            else:
                error_msg = '無效的模式選擇'
                if is_json_request:
                    return JsonResponse({
                        'status': 'error',
                        'message': error_msg
                    })
                else:
                    messages.error(request, error_msg)
                    return redirect('clinic_dashboard')
        except json.JSONDecodeError:
            error_msg = '請求格式錯誤'
            if is_json_request:
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg
                })
            else:
                messages.error(request, error_msg)
                return redirect('clinic_dashboard')
        except Exception as e:
            error_msg = f'模式切換時發生錯誤：{str(e)}'
            if is_json_request:
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg
                })
            else:
                messages.error(request, error_msg)
                return redirect('clinic_dashboard')

@login_required
@require_clinic_management
def manage_doctors(request):
    """管理醫師"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        doctors = VetDoctor.objects.filter(clinic=clinic).select_related('user')
        
        return render(request, 'clinic/manage_doctors.html', {
            'clinic': clinic,
            'doctors': doctors
        })
        
    except Exception as e:
        messages.error(request, f'載入醫師管理頁面失敗:{str(e)}')
        return redirect('clinic_dashboard')

# ============ 獸醫師工作台系統 ============

@login_required
@require_verified_vet(optional=True)
def vet_home(request):
    """獸醫師首頁"""
    try:
        # 處理診所管理員或獸醫師身份
        profile = request.user.profile
        
        if profile.account_type == 'clinic_admin':
            # 診所管理員:創建虛擬 vet_profile 或使用診所資料
            try:
                vet_profile = request.user.vet_profile
            except AttributeError:
                # 如果診所管理員沒有 vet_profile，創建虛擬資料
                class MockVetProfile:
                    def __init__(self, user, clinic):
                        self.id = user.id
                        self.user = user
                        self.clinic = clinic
                        self.speciality = "診所管理"
                        self.years_of_experience = 0
                        self.license_verified = True
                        self.license_verified_with_moa = True
                
                # 獲取診所資料
                clinic = request.user.clinic_profile.clinic
                vet_profile = MockVetProfile(request.user, clinic)
        else:
            vet_profile = request.user.vet_profile
        
        # 檢查獸醫師是否有診所關聯
        if not hasattr(vet_profile, 'clinic') or vet_profile.clinic is None:
            # 如果獸醫師沒有關聯診所，計算個人排班工作時數
            working_hours_no_clinic = 0
            try:
                schedules = VetSchedule.objects.filter(
                    doctor=vet_profile,
                    is_active=True
                )
                for schedule in schedules:
                    if schedule.start_time and schedule.end_time:
                        start_minutes = schedule.start_time.hour * 60 + schedule.start_time.minute
                        end_minutes = schedule.end_time.hour * 60 + schedule.end_time.minute
                        daily_hours = (end_minutes - start_minutes) / 60
                        working_hours_no_clinic += daily_hours
            except Exception:
                working_hours_no_clinic = 0
            
            # 如果獸醫師沒有關聯診所，提供預設的空資料
            return render(request, 'vet_pages/vet_home.html', {
                'vet_profile': vet_profile,
                'today_appointments': [],
                'today_appointments_count': 0,
                'total_patients_count': 0,
                'medical_records_count': 0,
                'today_date': timezone.now().date(),
                'appointments_change': 0,
                'new_patients_this_month': 0,
                'records_this_week': 0,
                'working_hours_this_week': int(working_hours_no_clinic),
                'pending_count': 0,
                'completed_count': 0,
                'statistics': {
                    'today': {'appointments': 0, 'completed': 0, 'pending': 0, 'confirmed': 0, 'records': 0},
                    'yesterday': {'appointments': 0, 'completed': 0, 'records': 0},
                    'week': {'appointments': 0, 'completed': 0, 'records': 0},
                    'month': {'appointments': 0, 'completed': 0, 'records': 0, 'new_patients': 0}
                },
                'changes': {'appointments': 0, 'completed': 0, 'records': 0},
                'appointment_trends': [],
                'appointment_trends_json': '[]',
                'no_clinic_setup': True  # 添加標記表示沒有診所設定
            })
        
        # 獲取今日預約 - 診所管理員看所有預約
        today = timezone.now().date()
        if hasattr(vet_profile, 'clinic') and profile.account_type == 'clinic_admin':
            # 診所管理員看整個診所的預約
            today_appointments = VetAppointment.objects.filter(
                slot__date=today,
                slot__doctor__clinic=vet_profile.clinic
            ).select_related('pet', 'owner', 'slot__doctor').order_by('slot__start_time')
        else:
            # 一般獸醫師只看自己的預約
            today_appointments = VetAppointment.objects.filter(
                slot__doctor=vet_profile,
                slot__date=today
            ).select_related('pet', 'owner').order_by('slot__start_time')
        
        # 獲取統計數據
        if profile.account_type == 'clinic_admin':
            # 診所管理員統計
            today_appointments_count = today_appointments.count()
            total_patients_count = Pet.objects.filter(
                vetappointment__slot__doctor__clinic=vet_profile.clinic
            ).distinct().count()
            medical_records_count = MedicalRecord.objects.filter(
                attending_vet__clinic=vet_profile.clinic
            ).count()
        else:
            # 獸醫師統計
            today_appointments_count = today_appointments.count()
            total_patients_count = Pet.objects.filter(
                vetappointment__slot__doctor=vet_profile
            ).distinct().count()
            medical_records_count = MedicalRecord.objects.filter(
                attending_vet=vet_profile
            ).count()
        
        # 獲取今日日期
        today_date = today
        
        # 詳細統計分析
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        # 時間範圍定義
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
        yesterday = today - timedelta(days=1)
        
        # 獲取對應的預約查詢集
        if profile.account_type == 'clinic_admin':
            all_appointments = VetAppointment.objects.filter(
                slot__doctor__clinic=vet_profile.clinic
            )
            all_records = MedicalRecord.objects.filter(
                attending_vet__clinic=vet_profile.clinic
            )
        else:
            all_appointments = VetAppointment.objects.filter(
                slot__doctor=vet_profile
            )
            all_records = MedicalRecord.objects.filter(
                attending_vet=vet_profile
            )
        
        # 統計數據
        today_completed = today_appointments.filter(status='completed').count()
        today_pending = today_appointments.filter(status='pending').count()
        today_confirmed = max(0, today_appointments_count - today_completed - today_pending)
        
        statistics = {
            'today': {
                'appointments': today_appointments_count,
                'completed': today_completed,
                'pending': today_pending,
                'confirmed': today_confirmed,
                'records': all_records.filter(visit_date=today).count(),
            },
            'yesterday': {
                'appointments': all_appointments.filter(slot__date=yesterday).count(),
                'completed': all_appointments.filter(slot__date=yesterday, status='completed').count(),
                'records': all_records.filter(visit_date=yesterday).count(),
            },
            'week': {
                'appointments': all_appointments.filter(slot__date__range=[week_start, week_end]).count(),
                'completed': all_appointments.filter(
                    slot__date__range=[week_start, week_end], 
                    status='completed'
                ).count(),
                'records': all_records.filter(visit_date__range=[week_start, week_end]).count(),
            },
            'month': {
                'appointments': all_appointments.filter(slot__date__range=[month_start, month_end]).count(),
                'completed': all_appointments.filter(
                    slot__date__range=[month_start, month_end], 
                    status='completed'
                ).count(),
                'records': all_records.filter(visit_date__range=[month_start, month_end]).count(),
                'new_patients': 0  # 暫時設為0，避免查詢錯誤
            }
        }
        
        # 計算變化
        changes = {
            'appointments': statistics['today']['appointments'] - statistics['yesterday']['appointments'],
            'completed': statistics['today']['completed'] - statistics['yesterday']['completed'],
            'records': statistics['today']['records'] - statistics['yesterday']['records'],
        }
        
        # 近7天趨勢
        appointment_trends = []
        for i in range(7):
            trend_date = today - timedelta(days=6-i)
            count = all_appointments.filter(slot__date=trend_date).count()
            appointment_trends.append({
                'date': trend_date.strftime('%m/%d'),
                'count': count,
                'day': trend_date.strftime('%a')
            })

        # 計算本週工作時數
        working_hours_this_week = 0
        try:
            if profile.account_type == 'clinic_admin':
                # 診所管理員計算整個診所的工作時數
                schedules = VetSchedule.objects.filter(
                    doctor__clinic=vet_profile.clinic,
                    is_active=True
                )
            else:
                # 獸醫師計算自己的工作時數
                schedules = VetSchedule.objects.filter(
                    doctor=vet_profile,
                    is_active=True
                )
            
            for schedule in schedules:
                if schedule.start_time and schedule.end_time:
                    # 計算每日工作時數
                    start_minutes = schedule.start_time.hour * 60 + schedule.start_time.minute
                    end_minutes = schedule.end_time.hour * 60 + schedule.end_time.minute
                    daily_hours = (end_minutes - start_minutes) / 60
                    working_hours_this_week += daily_hours
                    
        except Exception as e:
            print(f"計算工作時數時發生錯誤: {e}")
            working_hours_this_week = 0
        
        # 獲取最近病患數據 (限制5個)
        recent_patients_data = []
        try:
            if profile.account_type == 'clinic_admin':
                # 診所管理員查看整個診所的病患
                recent_patients = Pet.objects.filter(
                    vetappointment__slot__doctor__clinic=vet_profile.clinic
                ).distinct().select_related('owner')[:5]
            else:
                # 獸醫師只看自己的病患
                recent_patients = Pet.objects.filter(
                    vetappointment__slot__doctor=vet_profile
                ).distinct().select_related('owner')[:5]

            for pet in recent_patients:
                # 獲取最後就診日期
                last_appointment = VetAppointment.objects.filter(
                    pet=pet,
                    slot__doctor=vet_profile if profile.account_type != 'clinic_admin' else None,
                    status='completed'
                ).order_by('-slot__date').first()

                # 檢查今日是否有預約
                today_appointment = VetAppointment.objects.filter(
                    pet=pet,
                    slot__date=today,
                    slot__doctor=vet_profile if profile.account_type != 'clinic_admin' else None
                ).exists()

                # 判斷是否需要追蹤
                needs_followup = False
                if last_appointment:
                    days_since_visit = (today - last_appointment.slot.date).days
                    # 獲取最後一次的醫療記錄
                    last_record = None
                    try:
                        if profile.account_type == 'clinic_admin':
                            last_record = MedicalRecord.objects.filter(
                                pet=pet,
                                attending_vet__clinic=vet_profile.clinic
                            ).order_by('-visit_date').first()
                        else:
                            last_record = MedicalRecord.objects.filter(
                                pet=pet,
                                attending_vet=vet_profile
                            ).order_by('-visit_date').first()
                    except:
                        pass

                    # 需要追蹤的條件：
                    # 1. 最後就診超過30天且有醫療記錄建議追蹤
                    # 2. 有處方用藥且用藥期間已結束
                    # 3. 有慢性疾病需要定期回診
                    if days_since_visit > 30:
                        needs_followup = True
                    elif last_record:
                        # 檢查是否有需要追蹤的診斷關鍵字
                        followup_keywords = ['慢性', '定期', '追蹤', '複診', '監控', '持續', '回診']
                        if last_record.diagnosis:
                            for keyword in followup_keywords:
                                if keyword in last_record.diagnosis:
                                    needs_followup = True
                                    break
                        if last_record.treatment and not needs_followup:
                            for keyword in followup_keywords:
                                if keyword in last_record.treatment:
                                    needs_followup = True
                                    break

                recent_patients_data.append({
                    'pet': pet,
                    'last_visit': last_appointment.slot.date if last_appointment else None,
                    'today_appointment': today_appointment,
                    'needs_followup': needs_followup,
                    'days_since_visit': (today - last_appointment.slot.date).days if last_appointment else None
                })
        except Exception as e:
            print(f"獲取病患數據錯誤: {e}")
            recent_patients_data = []

        # 為JavaScript準備JSON安全的數據
        appointment_trends_json = json.dumps(appointment_trends)

        return render(request, 'vet_pages/vet_home.html', {
            'vet_profile': vet_profile,
            'today_appointments': today_appointments,
            'today_appointments_count': today_appointments_count,
            'total_patients_count': total_patients_count,
            'medical_records_count': medical_records_count,
            'today_date': today_date,
            'appointments_change': changes['appointments'],
            'new_patients_this_month': statistics['month']['new_patients'],
            'records_this_week': statistics['week']['records'],
            'working_hours_this_week': int(working_hours_this_week),
            'pending_count': statistics['today']['pending'],
            'completed_count': statistics['today']['completed'],
            'statistics': statistics,
            'changes': changes,
            'appointment_trends': appointment_trends,
            'appointment_trends_json': appointment_trends_json,
            'recent_patients_data': recent_patients_data,
        })
        
    except Exception as e:
        messages.error(request, f'載入獸醫師首頁失敗:{str(e)}')
        return redirect('home')
        
@login_required
@require_verified_vet(optional=True)
def my_patients_enhanced(request):
    """我的病患 - 強化版本"""
    try:
        # 獲取獸醫師身份 - 支援診所管理員
        try:
            profile = request.user.profile
            if profile.account_type == 'clinic_admin':
                # 診所管理員可以查看所有醫師的病患
                vet_profile = request.user.vet_profile
            else:
                vet_profile = request.user.vet_profile
        except AttributeError:
            messages.error(request, '您沒有獸醫師權限')
            return redirect('home')

        # 基本病患查詢 - 優化版
        patients_query = Pet.objects.filter(
            vetappointment__slot__doctor=vet_profile
        ).distinct().select_related(
            'owner'
        ).prefetch_related(
            'vaccine_records',
            'deworm_records',
            'medicalrecord_set',
            'vetappointment_set'
        )

        # 搜尋功能
        search_query = request.GET.get('search', '').strip()
        if search_query:
            patients_query = patients_query.filter(
                Q(name__icontains=search_query) |
                Q(owner__username__icontains=search_query) |
                Q(owner__first_name__icontains=search_query) |
                Q(owner__last_name__icontains=search_query) |
                Q(breed__icontains=search_query) |
                Q(chip__icontains=search_query)
            )

        # 狀態篩選
        status_filter = request.GET.get('status', '')
        if status_filter == 'recent':
            # 最近30天有預約的
            thirty_days_ago = timezone.now().date() - timezone.timedelta(days=30)
            patients_query = patients_query.filter(
                vetappointment__slot__date__gte=thirty_days_ago
            )
        elif status_filter == 'frequent':
            # 常客（超過3次預約）
            from django.db import models
            patients_query = patients_query.annotate(
                appointment_count=models.Count('vetappointment')
            ).filter(appointment_count__gte=3)

        # 取得病患列表
        patients = list(patients_query)

        # 為每個病患計算統計資訊
        patients_data = []
        today = timezone.now().date()

        for pet in patients:
            # 基本統計
            total_appointments = pet.vetappointment_set.filter(slot__doctor=vet_profile).count()
            total_medical_records = pet.medicalrecord_set.filter(attending_vet=vet_profile).count()
            total_vaccines = pet.vaccine_records.count()
            total_deworms = pet.deworm_records.count()

            # 最後就診日期
            last_appointment = pet.vetappointment_set.filter(
                slot__doctor=vet_profile,
                status='completed'
            ).order_by('-slot__date').first()

            # 今日是否有預約
            today_appointment = pet.vetappointment_set.filter(
                slot__doctor=vet_profile,
                slot__date=today,
                status__in=['confirmed', 'pending']
            ).exists()

            # 健康狀態評估
            health_status = 'good'
            if last_appointment:
                days_since_last = (today - last_appointment.slot.date).days
                if days_since_last > 365:
                    health_status = 'needs_checkup'
                elif days_since_last > 180:
                    health_status = 'attention'
            else:
                health_status = 'new_patient'

            patients_data.append({
                'pet': pet,
                'stats': {
                    'total_appointments': total_appointments,
                    'total_medical_records': total_medical_records,
                    'total_vaccines': total_vaccines,
                    'total_deworms': total_deworms,
                    'last_visit': last_appointment.slot.date if last_appointment else None,
                    'today_appointment': today_appointment,
                    'health_status': health_status,
                    'days_since_last_visit': (today - last_appointment.slot.date).days if last_appointment else None
                }
            })

        # 排序
        sort_by = request.GET.get('sort', 'name')
        if sort_by == 'last_visit':
            patients_data.sort(key=lambda x: x['stats']['last_visit'] or timezone.datetime.min.date(), reverse=True)
        elif sort_by == 'appointments':
            patients_data.sort(key=lambda x: x['stats']['total_appointments'], reverse=True)
        else:  # 預設按名稱排序
            patients_data.sort(key=lambda x: x['pet'].name)

        # 分頁
        paginator = Paginator(patients_data, 12)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # 統計摘要
        total_patients = len(patients_data)
        recent_patients = len([p for p in patients_data if p['stats']['today_appointment']])

        context = {
            'vet_profile': vet_profile,
            'patients_data': page_obj,
            'page_obj': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'total_patients': total_patients,
            'recent_patients': recent_patients,
            'has_data': total_patients > 0
        }

        return render(request, 'vet_pages/my_patients.html', context)

    except Exception as e:
        import traceback
        print(f"my_patients_enhanced error: {str(e)}")
        print(traceback.format_exc())
        messages.error(request, f'載入病患列表失敗: {str(e)}')
        return redirect('vet_home')


@login_required
@require_verified_vet(optional=True)
def vet_appointments(request):
    """獸醫師預約管理"""
    try:
        vet_profile = request.user.vet_profile
        
        # 注意:在顯示預約前，系統會自動過濾已過期的預約
        
        # 日期篩選 - 使用台灣時區
        import pytz
        taiwan_tz = pytz.timezone('Asia/Taipei')
        today = timezone.now().astimezone(taiwan_tz).date()
        date_filter = request.GET.get('date', 'week')
        
        if date_filter == 'today':
            start_date = end_date = today
        elif date_filter == 'week':
            start_date = today - timedelta(days=7)  # 包含過去一週
            end_date = today + timedelta(days=6)  # 未來一週
        elif date_filter == 'month':
            start_date = today.replace(day=1)
            from dateutil.relativedelta import relativedelta
            end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        else:
            start_date = end_date = today
        
        # 獲取預約
        now = timezone.now()
        appointments = VetAppointment.objects.filter(
            slot__doctor=vet_profile,
            slot__date__range=[start_date, end_date]
        ).select_related('pet', 'owner', 'slot').order_by('-slot__date', 'slot__start_time')
        
        # 過濾過期預約 (可選)
        show_expired = request.GET.get('show_expired', 'false') == 'true'
        
        if not show_expired:
            # 過濾條件:只顯示未來預約、今日所有預約、或已完成/已取消的預約
            filtered_appointments = []
            for appointment in appointments:
                appointment_datetime = timezone.datetime.combine(
                    appointment.slot.date,
                    appointment.slot.end_time
                )
                appointment_datetime = timezone.make_aware(appointment_datetime)

                # 顯示條件：
                # 1. 未來預約（未來日期或今日未結束的預約）
                # 2. 今日的所有預約（不論時間是否過期）
                # 3. 已完成/已取消/未到診的預約
                if (appointment_datetime > now or
                    appointment.slot.date == today or  # 今日所有預約都顯示
                    appointment.status in ['completed', 'cancelled', 'no_show']):
                    filtered_appointments.append(appointment)

            appointments = filtered_appointments
        
        # 狀態篩選
        status_filter = request.GET.get('status', '')
        if status_filter:
            appointments = [apt for apt in appointments if apt.status == status_filter]

        # 為完成的預約添加醫療記錄信息
        enhanced_appointments = []
        for appointment in appointments:
            medical_record = None

            # 只為已完成的預約查找醫療記錄
            if appointment.status == 'completed':
                medical_record = MedicalRecord.objects.filter(
                    pet=appointment.pet,
                    visit_date=appointment.slot.date,
                    attending_vet=vet_profile
                ).select_related('attending_vet__user').first()

            # 將原始預約和醫療記錄組合
            appointment.medical_record = medical_record
            # medical_details 現在是 @property，不需要手動設置
            appointment.has_medical_record = medical_record is not None
            enhanced_appointments.append(appointment)

        # 計算統計數據（因為 appointments 現在是 list）
        today_appointments_count = len([apt for apt in enhanced_appointments if apt.slot.date == today])
        pending_count = len([apt for apt in enhanced_appointments if apt.status == 'pending'])
        completed_count = len([apt for apt in enhanced_appointments if apt.status == 'completed'])
        
        return render(request, 'vet_pages/vet_appointments.html', {
            'vet_profile': vet_profile,
            'appointments': enhanced_appointments,
            'date_filter': date_filter,
            'status_filter': status_filter,
            'start_date': start_date,
            'end_date': end_date,
            'today': today,  # 加入今天的日期供模板使用
            'today_appointments_count': today_appointments_count,
            'pending_count': pending_count,
            'completed_count': completed_count,
            'show_history': request.GET.get('history', False),
            'show_expired': show_expired
        })
        
    except Exception as e:
        messages.error(request, f'載入預約管理失敗:{str(e)}')
        return redirect('vet_home')

@login_required
@require_verified_vet
def vet_cancel_appointment(request, appointment_id):
    """獸醫師取消預約"""
    try:
        vet_profile = request.user.vet_profile
        appointment = get_object_or_404(
            VetAppointment,
            id=appointment_id,
            slot__doctor=vet_profile
        )

        # 預定義的取消原因選項
        cancel_reasons = [
            ('patient_no_show', '病患未到診'),
            ('veterinarian_emergency', '獸醫師緊急事件'),
            ('equipment_failure', '設備故障'),
            ('schedule_conflict', '時程衝突'),
            ('patient_health_improve', '病患健康狀況改善'),
            ('weather_conditions', '天氣狀況不佳'),
            ('clinic_closure', '診所臨時關閉'),
            ('other', '其他原因'),
        ]

        if request.method == 'POST':
            # 處理來自前端表單的取消原因（可能是自由文字或代碼）
            cancel_reason_input = request.POST.get('cancel_reason', '')
            custom_reason = request.POST.get('custom_reason', '')

            # 確定最終取消原因
            if custom_reason:
                # 如果有自定義原因，使用自定義原因
                final_reason = custom_reason
            elif cancel_reason_input:
                # 檢查是否是預定義的代碼
                reason_dict = dict(cancel_reasons)
                final_reason = reason_dict.get(cancel_reason_input, cancel_reason_input)
            else:
                final_reason = "未提供取消原因"

            appointment.status = 'cancelled'
            appointment.cancel_reason = final_reason
            appointment.save()

            messages.success(request, f'預約已取消：{appointment.pet.name} - {final_reason}')

            # 如果是AJAX請求，返回JSON響應
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': '預約取消成功'})

            return redirect('vet_appointments')

        # GET請求顯示取消確認頁面
        return render(request, 'vet_pages/cancel_appointment.html', {
            'appointment': appointment,
            'cancel_reasons': cancel_reasons
        })

    except Exception as e:
        messages.error(request, f'取消預約失敗:{str(e)}')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': str(e)})
        return redirect('vet_appointments')

@login_required
@require_verified_vet
@require_http_methods(["POST"])
def vet_batch_appointment_operation(request):
    """獸醫師批量預約操作API"""
    try:
        vet_profile = request.user.vet_profile
        data = json.loads(request.body)
        
        action = data.get('action')
        appointment_ids = data.get('appointment_ids', [])
        reason = data.get('reason', '')
        
        if not action or not appointment_ids:
            return JsonResponse({
                'success': False,
                'message': '缺少必要參數'
            })
        
        # 驗證預約是否屬於該獸醫師
        appointments = VetAppointment.objects.filter(
            id__in=appointment_ids,
            slot__doctor=vet_profile
        )
        
        if appointments.count() != len(appointment_ids):
            return JsonResponse({
                'success': False,
                'message': '部分預約不屬於您或不存在'
            })
        
        updated_count = 0
        
        with transaction.atomic():
            for appointment in appointments:
                if action == 'confirm':
                    if appointment.status == 'pending':
                        appointment.status = 'confirmed'
                        appointment.save()
                        updated_count += 1
                        
                # elif action == 'complete':  # REMOVED: Appointments auto-complete when medical records are created
                #     if appointment.status in ['pending', 'confirmed']:
                #         appointment.status = 'completed'
                #         appointment.save()
                #         updated_count += 1

                elif action == 'cancel':
                    if appointment.status in ['pending', 'confirmed']:
                        appointment.status = 'cancelled'
                        if reason:
                            appointment.notes = f"{appointment.notes or ''}\n取消原因:{reason}".strip()
                        appointment.save()
                        updated_count += 1
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'成功處理了 {updated_count} 個預約'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '請求數據格式錯誤'
        })
    except Exception as e:
        logger.error(f'批量預約操作錯誤:{str(e)}')
        return JsonResponse({
            'success': False,
            'message': '操作失敗，請稍後再試'
        })

@login_required
@require_verified_vet(optional=True)
def pet_detail(request, pet_id):
    """寵物詳情（獸醫師視角）"""
    try:
        from datetime import datetime, timedelta
        vet_profile = request.user.vet_profile

        # 獲取寵物資料
        pet = get_object_or_404(Pet, id=pet_id)

        # 檢查權限:這位獸醫師是否曾經看過這隻寵物
        if not VetAppointment.objects.filter(
            slot__doctor=vet_profile,
            pet=pet
        ).exists():
            messages.error(request, '您沒有權限查看此寵物的資料')
            return redirect('vet_home')

        # 獲取醫療記錄並解析詳細資訊
        medical_records = MedicalRecord.objects.filter(
            pet=pet
        ).select_related('attending_vet', 'attending_vet__user').order_by('-visit_date')

        # 獲取疫苗記錄
        vaccine_records = VaccineRecord.objects.filter(
            pet=pet
        ).order_by('-date')

        # 獲取驅蟲記錄
        deworm_records = DewormRecord.objects.filter(
            pet=pet
        ).order_by('-date')

        # 獲取報告記錄
        reports = Report.objects.filter(
            pet=pet
        ).order_by('-date_uploaded')

        # 為每筆醫療記錄設置詳細資訊標記
        for record in medical_records:
            # medical_details 現在是 @property，自動解析
            record.has_detailed_info = bool(record.medical_details and
                                           (record.medical_details.get('prescriptions') or
                                            record.medical_details.get('symptoms') or
                                            record.medical_details.get('weight') or
                                            record.medical_details.get('temperature')))

        # 獲取預約歷史
        appointment_history = VetAppointment.objects.filter(
            pet=pet,
            slot__doctor=vet_profile
        ).select_related('slot').order_by('-slot__date')

        # 計算統計數據
        total_records = medical_records.count() + vaccine_records.count() + deworm_records.count()

        # 計算最近30天的記錄數
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_medical = medical_records.filter(visit_date__gte=thirty_days_ago).count()
        recent_vaccine = vaccine_records.filter(date__gte=thirty_days_ago).count()
        recent_deworm = deworm_records.filter(date__gte=thirty_days_ago).count()
        recent_activity = recent_medical + recent_vaccine + recent_deworm

        # 計算健康狀態
        last_medical = medical_records.first()
        health_status = "良好"
        if last_medical:
            days_since_last = (timezone.now().date() - last_medical.visit_date).days
            if days_since_last > 365:
                health_status = "需檢查"
            elif last_medical.diagnosis and any(word in last_medical.diagnosis.lower() for word in ['感染', '發炎', '異常', '疾病']):
                health_status = "需關注"

        # 疫苗狀態檢查
        vaccine_status = "最新"
        if vaccine_records.exists():
            last_vaccine = vaccine_records.first()
            days_since_vaccine = (timezone.now().date() - last_vaccine.date).days
            if days_since_vaccine > 365:
                vaccine_status = "需更新"
        else:
            vaccine_status = "無記錄"

        return render(request, 'vet_pages/pet_detail.html', {
            'vet_profile': vet_profile,
            'pet': pet,
            'medical_records': medical_records,
            'vaccine_records': vaccine_records,
            'deworm_records': deworm_records,
            'reports': reports,
            'appointment_history': appointment_history,
            # 統計數據
            'total_records': total_records,
            'recent_activity': recent_activity,
            'health_status': health_status,
            'vaccine_status': vaccine_status,
            'total_medical_records': medical_records.count(),
            'total_vaccine_records': vaccine_records.count(),
            'total_deworm_records': deworm_records.count(),
            'total_reports': reports.count(),
        })
        
    except Exception as e:
        import traceback
        print(f"Error in pet_detail view: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        messages.error(request, f'載入寵物詳情失敗:{str(e)}')
        return redirect('vet_home')
    
# ============ 醫療記錄管理 ============

@login_required
@require_verified_vet(optional=True)
def create_medical_record(request, pet_id=None):
    """建立醫療記錄"""
    print(f"*** MEDICAL RECORD FUNCTION CALLED: {request.method} ***")
    print(f"\n{'='*50}")
    print(f"create_medical_record被調用: method={request.method}, pet_id={pet_id}, user={request.user}")
    print(f"{'='*50}\n")
    try:
        vet_profile = request.user.vet_profile
        # 使用台灣時區的當地日期
        import pytz
        taiwan_tz = pytz.timezone('Asia/Taipei')
        today = timezone.now().astimezone(taiwan_tz).date()
        
        # 必須指定寵物ID - 不允許直接選擇寵物
        if not pet_id:
            # 檢查請求來源，決定重定向位置
            referer = request.META.get('HTTP_REFERER', '')
            if 'patients' in referer:
                redirect_url = 'my_patients'
            else:
                redirect_url = 'vet_appointments'

            messages.error(request, '請從今日預約清單中選擇要建立醫療記錄的寵物')
            return redirect(redirect_url)
            
        pet = get_object_or_404(Pet, id=pet_id)
        
        # 檢查今日是否有預約且預約狀態為已確認或已完成
        today_appointments = VetAppointment.objects.filter(
            slot__doctor=vet_profile,
            pet=pet,
            slot__date=today,  # 只允許今日的預約
            status__in=['confirmed', 'completed']  # 預約必須已確認或已完成
        )

        if not today_appointments.exists():
            # 檢查請求來源，決定重定向位置
            referer = request.META.get('HTTP_REFERER', '')
            if 'patients' in referer:
                redirect_url = 'my_patients'
            else:
                redirect_url = 'vet_appointments'

            messages.error(request, f'只能為今日({today.strftime("%Y年%m月%d日")})已確認預約的寵物建立醫療記錄！無法為未來日期的預約建立病歷。')
            return redirect(redirect_url)
        
        if request.method == 'POST':
            print(f"=== 醫療記錄 POST 請求開始 ===")
            print(f"User: {request.user}")
            print(f"Pet ID: {pet_id}")
            print(f"Today: {today}")
            print(f"=== 這是最新的代碼版本 ===")
            try:
                print(f"原始表單數據鍵值: {list(request.POST.keys())}")
                print(f"原始表單數據長度: {len(request.POST)}")
            except Exception as e:
                print(f"讀取表單數據錯誤: {e}")

            print(f"即將開始處理表單...")

            try:
                # 只構建表單需要的數據，不使用copy()
                print(f"開始構建表單數據...")

                # 合併主要診斷和次要診斷到diagnosis欄位
                primary_diagnosis = request.POST.get('primary_diagnosis', '')
                secondary_diagnosis = request.POST.get('secondary_diagnosis', '')
                print(f"primary_diagnosis: '{primary_diagnosis}'")
                print(f"secondary_diagnosis: '{secondary_diagnosis}'")

                diagnosis = primary_diagnosis
                if secondary_diagnosis:
                    diagnosis += f"\n\n次要診斷: {secondary_diagnosis}"
                print(f"mapped diagnosis: '{diagnosis}'")

                # 映射治療計畫到treatment欄位
                treatment_plan = request.POST.get('treatment_plan', '')
                print(f"treatment_plan: '{treatment_plan}'")

                # 先提取生理數據變數
                current_weight = request.POST.get('weight', '')
                temperature = request.POST.get('temperature', '')
                heart_rate = request.POST.get('heart_rate', '')
                respiratory_rate = request.POST.get('respiratory_rate', '')
                print(f"生理數據: weight={current_weight}, temp={temperature}, hr={heart_rate}, rr={respiratory_rate}")

                # 只構建表單需要的欄位，包含生理數據
                mapped_data = {
                    'pet': pet.id,
                    'diagnosis': diagnosis,
                    'treatment_plan': treatment_plan,  # 修正字段名稱
                    'clinic_location': vet_profile.clinic.clinic_name if vet_profile.clinic else '',
                    'weight': current_weight,
                    'temperature': temperature,
                    'heart_rate': heart_rate,
                    'respiratory_rate': respiratory_rate,
                    'chief_complaint': request.POST.get('chief_complaint', ''),
                    'physical_examination': request.POST.get('physical_examination', ''),
                    'diagnosis_confidence': request.POST.get('diagnosis_confidence', ''),
                    'follow_up_required': request.POST.get('follow_up_required', ''),
                    'follow_up_date': request.POST.get('follow_up_date', ''),
                    'total_cost': request.POST.get('total_cost', ''),
                    'notes': ''  # 先設為空字符串
                }

                print(f"基本表單數據構建完成: {mapped_data}")
                print(f"檢查生理數據變數:")
                print(f"  current_weight: {current_weight}")
                print(f"  temperature: {temperature}")
                print(f"  heart_rate: {heart_rate}")
                print(f"  respiratory_rate: {respiratory_rate}")

                # 合併備註欄位 - 包含所有詳細醫療信息
                notes_parts = []

                # 主訴與病史
                chief_complaint = request.POST.get('chief_complaint', '')
                if chief_complaint:
                    notes_parts.append(f"📋 主訴 (飼主描述):\n{chief_complaint}")

                # 理學檢查
                physical_examination = request.POST.get('physical_examination', '')
                if physical_examination:
                    notes_parts.append(f"🔍 理學檢查結果:\n{physical_examination}")

                # 基本生理數據 (已在上面定義)

                if current_weight:
                    notes_parts.append(f"📊 體重: {current_weight}kg")
                if temperature:
                    notes_parts.append(f"🌡️ 體溫: {temperature}°C")
                if heart_rate:
                    notes_parts.append(f"💓 心率: {heart_rate}次/分")
                if respiratory_rate:
                    notes_parts.append(f"🫁 呼吸: {respiratory_rate}次/分")

                # 症狀信息
                symptoms_data = request.POST.get('symptoms_data', '')
                if symptoms_data and symptoms_data != '[]':
                    try:
                        import json
                        symptoms = json.loads(symptoms_data)
                        if symptoms:
                            notes_parts.append("🏥 症狀:")
                            for symptom in symptoms:
                                severity_map = {1: "輕微", 2: "中等", 3: "嚴重", 4: "危急", 5: "緊急"}
                                severity = severity_map.get(symptom.get('severity', 1), "輕微")
                                notes_parts.append(f"  • {symptom['name']} (嚴重程度: {severity})")
                    except:
                        pass

                # 處方信息
                prescriptions_data = request.POST.get('prescriptions_data', '')
                if prescriptions_data and prescriptions_data != '[]':
                    try:
                        prescriptions = json.loads(prescriptions_data)
                        if prescriptions:
                            notes_parts.append("💊 處方藥品:")
                            for i, prescription in enumerate(prescriptions):
                                # 正確獲取藥品名稱 - 前端發送的結構是 drug.chinese_name
                                drug_info = prescription.get('drug', {})
                                chinese_name = drug_info.get('chinese_name', '')
                                english_name = drug_info.get('english_name', '')

                                # 組合中英文藥名
                                drug_name = chinese_name
                                if english_name and english_name != chinese_name:
                                    drug_name += f" ({english_name})"

                                dosage = prescription.get('dosage', '')
                                frequency = prescription.get('frequency', '')
                                route = prescription.get('route', '')
                                duration = prescription.get('duration', '')
                                instructions = prescription.get('instructions', '')

                                notes_parts.append(f"  • {drug_name}")
                                if dosage:
                                    notes_parts.append(f"    劑量: {dosage}")
                                if frequency:
                                    notes_parts.append(f"    頻率: {frequency}")
                                if route:
                                    notes_parts.append(f"    給藥方式: {route}")
                                if duration:
                                    notes_parts.append(f"    療程: {duration}")
                                if instructions:
                                    notes_parts.append(f"    用藥指示: {instructions}")
                    except Exception as e:
                        print(f"處方資料處理錯誤: {e}")
                        pass

                # 診斷信心度和嚴重程度
                diagnosis_confidence = request.POST.get('diagnosis_confidence', '')
                severity = request.POST.get('severity', '')
                if diagnosis_confidence or severity:
                    confidence_severity_info = []
                    if diagnosis_confidence:
                        confidence_severity_info.append(f"診斷信心度: {diagnosis_confidence}")
                    if severity:
                        severity_map = {"1": "輕微", "2": "中等", "3": "嚴重", "4": "危急", "5": "緊急"}
                        severity_text = severity_map.get(severity, severity)
                        confidence_severity_info.append(f"嚴重程度: {severity_text}")
                    notes_parts.append(f"⚕️ 診斷評估:\n{' | '.join(confidence_severity_info)}")

                # 追蹤計畫
                follow_up_required = request.POST.get('follow_up_required', '')
                follow_up_date = request.POST.get('follow_up_date', '')
                if follow_up_required or follow_up_date:
                    follow_up_info = []
                    if follow_up_required:
                        follow_up_info.append("需要後續追蹤")
                    if follow_up_date:
                        follow_up_info.append(f"預約回診日期: {follow_up_date}")
                    notes_parts.append(f"📅 追蹤計畫:\n{' | '.join(follow_up_info)}")

                # 其他備註
                additional_notes = request.POST.get('additional_notes', '')
                if additional_notes:
                    notes_parts.append(f"📝 其他備註:\n{additional_notes}")

                # 組織notes內容，加入分隔線讓各區塊更清晰
                if notes_parts:
                    mapped_data['notes'] = '\n\n'.join(notes_parts)
                else:
                    mapped_data['notes'] = ''

                print(f"chief_complaint: '{chief_complaint}'")
                print(f"physical_examination: '{physical_examination}'")
                print(f"weight: '{current_weight}'")
                print(f"temperature: '{temperature}'")
                print(f"symptoms_data: '{symptoms_data}'")
                print(f"prescriptions_data: '{prescriptions_data}'")
                print(f"final mapped notes: '{mapped_data['notes']}'")

                print(f"映射後的表單數據: {mapped_data}")
                print(f"=== 數據處理完成，開始建立表單 ===")

            except Exception as e:
                print(f"❌ 表單數據處理時發生錯誤: {str(e)}")
                print(f"錯誤類型: {type(e)}")
                import traceback
                print(f"錯誤堆疊: {traceback.format_exc()}")
                # 檢查請求來源，決定重定向位置
                referer = request.META.get('HTTP_REFERER', '')
                if 'patients' in referer:
                    redirect_url = 'my_patients'
                else:
                    redirect_url = 'vet_appointments'

                messages.error(request, f'處理表單數據時發生錯誤: {str(e)}')
                return redirect(redirect_url)

            # 使用處理過的數據創建表單，確保生理數據被正確處理
            form = MedicalRecordForm(mapped_data)
            print(f"表單驗證結果: {form.is_valid()}")
            if not form.is_valid():
                print(f"表單錯誤: {form.errors}")
                for field, errors in form.errors.items():
                    print(f"欄位 {field} 錯誤: {errors}")

            if form.is_valid():
                print(f"=== 表單驗證通過，開始儲存 ===")
                print(f"form.cleaned_data keys: {list(form.cleaned_data.keys())}")
                print(f"form.cleaned_data: {form.cleaned_data}")

                # 移除日期驗證，因為 visit_date 使用 auto_now_add=True
                print(f"跳過日期驗證，使用 auto_now_add")

                medical_record = form.save(commit=False)
                print(f"建立醫療記錄物件: {medical_record}")
                medical_record.attending_vet = vet_profile
                medical_record.recorded_by = request.user  # 設定記錄者為當前用戶
                medical_record.pet = pet  # 確保設定正確的寵物

                # visit_date 會自動設定為今天 (auto_now_add=True)
                latest_appointment = today_appointments.first()

                # 如果有診所資訊，自動填入
                if vet_profile.clinic:
                    medical_record.clinic_location = vet_profile.clinic.clinic_name

                try:
                    print(f"=== 準備保存醫療記錄 ===")
                    print(f"medical_record.pet: {medical_record.pet}")
                    print(f"medical_record.attending_vet: {medical_record.attending_vet}")
                    print(f"medical_record.diagnosis: {medical_record.diagnosis}")
                    print(f"醫療記錄物件所有屬性:")
                    for field in medical_record._meta.fields:
                        value = getattr(medical_record, field.name, 'N/A')
                        print(f"  {field.name}: {value}")

                    # 使用原子事務防止重複記錄
                    with transaction.atomic():
                        # 嘗試獲取或創建醫療記錄 - 基於關鍵欄位防重複
                        existing_record = MedicalRecord.objects.filter(
                            pet=pet,
                            attending_vet=vet_profile,
                            visit_date=today,
                            diagnosis=medical_record.diagnosis
                        ).first()

                        if existing_record:
                            print(f"⚠️ 發現重複醫療記錄 (ID: {existing_record.id})，跳過保存")
                            medical_record = existing_record  # 使用現有記錄
                            print(f"✅ 使用現有醫療記錄！ID: {medical_record.id}")
                        else:
                            medical_record.save()
                    print(f"✅ 醫療記錄保存成功！ID: {medical_record.id}")
                    print(f"保存後 visit_date: {medical_record.visit_date}")

                    # 驗證是否真的保存到資料庫
                    saved_record = MedicalRecord.objects.get(id=medical_record.id)
                    print(f"從資料庫讀取的記錄 visit_date: {saved_record.visit_date}")
                    print(f"從資料庫讀取的記錄 diagnosis: {saved_record.diagnosis}")

                    # 更新寵物的最後就診日期
                    pet.last_visit_date = medical_record.visit_date
                    pet.save()

                    # 將對應的預約標記為已完成
                    today_appointments.update(status='completed')

                    messages.success(request, f'已為 {pet.name} 建立醫療記錄並完成就診！')

                    # 檢測AJAX請求 - 更準確的檢測邏輯
                    is_ajax = (
                        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                        request.headers.get('Content-Type', '').startswith('multipart/form-data') or
                        'fetch' in request.META.get('HTTP_USER_AGENT', '').lower() or
                        request.headers.get('Accept', '').startswith('application/json')
                    )
                    print(f"AJAX檢測結果: {is_ajax}")
                    print(f"Headers: X-Requested-With={request.headers.get('X-Requested-With')}")
                    print(f"Headers: Content-Type={request.headers.get('Content-Type')}")
                    print(f"Headers: Accept={request.headers.get('Accept')}")

                    if is_ajax:
                        from django.http import JsonResponse
                        # 檢查請求來源，決定重定向位置
                        referer = request.META.get('HTTP_REFERER', '')
                        if 'patients' in referer:
                            redirect_path = '/vet/patients/'
                        else:
                            redirect_path = '/vet/appointments/'

                        return JsonResponse({
                            'success': True,
                            'message': f'已為 {pet.name} 建立醫療記錄並完成就診！',
                            'redirect': redirect_path
                        })

                    # 檢查請求來源，決定重定向位置
                    referer = request.META.get('HTTP_REFERER', '')
                    if 'patients' in referer:
                        redirect_url = 'my_patients'
                    else:
                        redirect_url = 'vet_appointments'

                    return redirect(redirect_url)
                except Exception as e:
                    print(f"保存醫療記錄失敗: {str(e)}")
                    messages.error(request, f'保存醫療記錄時發生錯誤: {str(e)}')

                    # 如果是AJAX請求，返回JSON錯誤響應
                    is_ajax = (
                        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                        request.headers.get('Content-Type', '').startswith('multipart/form-data') or
                        'fetch' in request.META.get('HTTP_USER_AGENT', '').lower() or
                        request.headers.get('Accept', '').startswith('application/json')
                    )
                    if is_ajax:
                        from django.http import JsonResponse
                        return JsonResponse({
                            'success': False,
                            'message': f'保存醫療記錄時發生錯誤: {str(e)}'
                        })
            else:
                print(f"=== 表單驗證失敗 ===")
                print(f"Form errors: {form.errors}")
                print(f"Form non-field errors: {form.non_field_errors()}")
                print(f"Form data: {form.data}")
                messages.error(request, '表單驗證失敗，請檢查輸入資料')

                # 如果是AJAX請求，返回JSON錯誤響應
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'fetch' in request.META.get('HTTP_USER_AGENT', '').lower():
                    from django.http import JsonResponse
                    return JsonResponse({
                        'success': False,
                        'message': '表單驗證失敗，請檢查輸入資料',
                        'errors': form.errors if 'form' in locals() else {}
                    })
        else:
            # 預填表單資料
            initial_data = {
                'pet': pet,
            }
            if vet_profile.clinic:
                initial_data['clinic_location'] = vet_profile.clinic.clinic_name

            form = MedicalRecordForm(initial=initial_data)

        # 獲取當前預約資訊供顯示
        current_appointment = today_appointments.first()
        
        return render(request, 'vet_pages/create_medical_record.html', {
            'vet_profile': vet_profile,
            'form': form,
            'pet': pet,
            'current_appointment': current_appointment,
            'is_pet_selection': False,  # 不再顯示寵物選擇介面
            'today': today
        })
        
    except Exception as e:
        messages.error(request, f'建立醫療記錄失敗:{str(e)}')
        return redirect('vet_home')


@login_required
@require_verified_vet
def vet_medical_history(request):
    """獸醫師診療歷史頁面 - 優化版"""
    try:
        vet_profile = request.user.vet_profile

        # 優化：使用 select_related 和 only 減少資料庫查詢
        base_queryset = MedicalRecord.objects.filter(
            attending_vet=vet_profile
        ).select_related(
            'pet__owner',
            'attending_vet__user',
            'attending_vet__clinic'
        ).only(
            'id', 'visit_date', 'diagnosis', 'treatment', 'notes',
            'pet__id', 'pet__name', 'pet__owner__id',
            'pet__owner__first_name', 'pet__owner__last_name',
            'pet__owner__username',
            'attending_vet__id'
        )

        # 處理搜尋篩選
        search_query = request.GET.get('q', '').strip()
        if search_query:
            base_queryset = base_queryset.filter(
                Q(pet__name__icontains=search_query) |
                Q(pet__owner__first_name__icontains=search_query) |
                Q(pet__owner__last_name__icontains=search_query) |
                Q(diagnosis__icontains=search_query)
            )

        # 處理日期篩選
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                base_queryset = base_queryset.filter(visit_date__gte=date_from_obj)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                base_queryset = base_queryset.filter(visit_date__lte=date_to_obj)
            except ValueError:
                pass

        # 排序
        medical_records = base_queryset.order_by('-visit_date')

        # 優化：使用 aggregate 進行統計查詢
        from django.db.models import Count
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        thirty_days_ago = today - timedelta(days=30)

        # 一次性獲取統計數據
        stats = MedicalRecord.objects.filter(
            attending_vet=vet_profile
        ).aggregate(
            total=Count('id'),
            this_month=Count('id', filter=Q(visit_date__gte=first_day_of_month)),
            recent_30_days=Count('id', filter=Q(visit_date__gte=thirty_days_ago)),
            unique_pets=Count('pet', distinct=True)
        )

        total_records = stats['total']
        this_month_records = stats['this_month']
        unique_pets = stats['unique_pets']
        avg_records_per_day = stats['recent_30_days'] / 30 if stats['recent_30_days'] > 0 else 0

        # 分頁處理 - 每頁增加到 20 筆減少翻頁次數
        paginator = Paginator(medical_records, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'vet_pages/medical_history.html', {
            'medical_records': page_obj,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'total_records': total_records,
            'this_month_records': this_month_records,
            'unique_pets': unique_pets,
            'avg_records_per_day': avg_records_per_day,
            'search_query': search_query,
            'date_from': request.GET.get('date_from', ''),
            'date_to': request.GET.get('date_to', ''),
        })

    except Exception as e:
        messages.error(request, f'載入診療歷史失敗:{str(e)}')
        return redirect('vet_home')


@login_required
@require_verified_vet
def edit_medical_record(request, pet_id, record_id):
    """編輯醫療記錄"""
    try:
        vet_profile = request.user.vet_profile
        pet = get_object_or_404(Pet, id=pet_id)
        medical_record = get_object_or_404(MedicalRecord, id=record_id, pet=pet)
        
        # 檢查權限:只能編輯自己建立的記錄
        if medical_record.attending_vet != vet_profile:
            messages.error(request, '您只能編輯自己建立的醫療記錄')
            return redirect('pet_detail', pet_id=pet_id)
        
        if request.method == 'POST':
            form = MedicalRecordForm(request.POST, instance=medical_record)
            if form.is_valid():
                form.save()
                messages.success(request, '醫療記錄更新成功！')
                return redirect('pet_detail', pet_id=pet_id)
        else:
            form = MedicalRecordForm(instance=medical_record)
        
        return render(request, 'vet/edit_medical_record.html', {
            'vet_profile': vet_profile,  # 添加這一行
            'form': form,
            'pet': pet,
            'medical_record': medical_record
        })
        
    except Exception as e:
        messages.error(request, f'編輯醫療記錄失敗:{str(e)}')
        return redirect('vet_home')


@login_required
@require_verified_vet
def delete_medical_record(request, record_id):
    """刪除醫療記錄"""
    try:
        vet_profile = request.user.vet_profile
        medical_record = get_object_or_404(MedicalRecord, id=record_id)
        
        # 檢查權限:只能刪除自己建立的記錄
        if medical_record.attending_vet != vet_profile:
            messages.error(request, '您只能刪除自己建立的醫療記錄')
            return redirect('vet_home')
        
        if request.method == 'POST':
            pet_id = medical_record.pet.id
            medical_record.delete()
            messages.success(request, '醫療記錄刪除成功！')
            return redirect('pet_detail', pet_id=pet_id)
        
        return render(request, 'vet/delete_medical_record.html', {
            'medical_record': medical_record
        })
        
    except Exception as e:
        messages.error(request, f'刪除醫療記錄失敗:{str(e)}')
        return redirect('vet_home')

@login_required
@require_verified_vet
def edit_vet_profile(request):
    """獸醫師檔案編輯重定向 - 統一由診所管理員管理"""
    try:
        profile = request.user.profile
        
        if profile.account_type == 'clinic_admin':
            # 診所管理員:重定向到診所管理頁面
            messages.info(request, '請透過診所管理頁面編輯獸醫師資料。')
            return redirect('manage_doctors')
        else:
            # 一般獸醫師:顯示說明訊息
            messages.info(request, '獸醫師檔案需由診所管理員進行管理。如需更新專業資料，請聯絡您的診所管理員。')
            return redirect('vet_home')
            
    except Exception as e:
        messages.error(request, '系統錯誤，請稍後再試。')
        return redirect('vet_home')

# ============ 預約管理系統（診所端） ============

@login_required
@require_clinic_management
def clinic_appointments(request):
    """診所預約管理"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 獲取日期範圍
        date_filter = request.GET.get('date', 'week')
        today = timezone.now().date()
        
        if date_filter == 'today':
            start_date = end_date = today
        elif date_filter == 'tomorrow': 
            start_date = end_date = today + timedelta(days=1)
        elif date_filter == 'week':
            start_date = today - timedelta(days=7)  # 包含過去一週
            end_date = today + timedelta(days=6)  # 未來一週
        elif date_filter == 'month':
            start_date = today.replace(day=1)
            end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        elif date_filter == 'all':  # 新增全部選項
            start_date = today - timedelta(days=365)  # 過去一年
            end_date = today + timedelta(days=365)    # 未來一年
        else:
            start_date = end_date = today
        
        # 獲取診所所有預約
        appointments = VetAppointment.objects.filter(
            slot__doctor__clinic=clinic,
            slot__date__range=[start_date, end_date]
        ).select_related('pet', 'owner', 'slot', 'slot__doctor__user').order_by(
            'slot__date', 'slot__start_time'
        )
        
        # 醫師過濾
        doctor_filter = request.GET.get('doctor', 'all')
        if doctor_filter and doctor_filter != 'all':
            appointments = appointments.filter(slot__doctor_id=doctor_filter)
        
        # 狀態過濾
        status_filter = request.GET.get('status', 'all')
        if status_filter and status_filter != 'all':
            appointments = appointments.filter(status=status_filter)
        
        # 獲取診所醫師列表
        doctors = VetDoctor.objects.filter(
            clinic=clinic,
            is_active=True
        ).select_related('user')

        total_appointments = appointments.count()
        today_appointments = appointments.filter(slot__date=today).count()
        pending_appointments = appointments.filter(status='pending').count()
        confirmed_appointments = appointments.filter(status='confirmed').count()
 
        
        return render(request, 'clinic/appointments.html', {
            'clinic': clinic,
            'appointments': appointments,
            'doctors': doctors,
            'date_filter': date_filter,
            'doctor_filter': doctor_filter,
            'status_filter': status_filter,
            'start_date': start_date,
            'end_date': end_date,
            'total_appointments': total_appointments,
            'today_appointments': today_appointments,
            'pending_appointments': pending_appointments,
            'confirmed_appointments': confirmed_appointments,
        })
        
    except Exception as e:
        messages.error(request, f'載入預約管理失敗:{str(e)}')
        return redirect('clinic_dashboard')

@login_required
@require_clinic_management
def view_appointment_detail(request, appointment_id):
    """查看預約詳情"""
    try:
        vet_profile = request.user.vet_profile
        appointment = get_object_or_404(
            VetAppointment,
            id=appointment_id,
            slot__doctor__clinic=vet_profile.clinic
        )
        
        return render(request, 'clinic/appointment_detail.html', {
            'appointment': appointment
        })
        
    except Exception as e:
        messages.error(request, f'載入預約詳情失敗:{str(e)}')
        return redirect('clinic_appointments')

@login_required
@require_clinic_management
def confirm_appointment(request, appointment_id):
    """確認預約"""
    try:
        vet_profile = request.user.vet_profile
        appointment = get_object_or_404(
            VetAppointment,
            id=appointment_id,
            slot__doctor__clinic=vet_profile.clinic
        )
        
        if request.method == 'POST':
            appointment.status = 'confirmed'
            appointment.save()
            
            # 發送確認通知（可選）
            messages.success(request, f'預約 {appointment.id} 已確認')
            
        return redirect('clinic_appointments')
        
    except Exception as e:
        messages.error(request, f'確認預約失敗:{str(e)}')
        return redirect('clinic_appointments')

@login_required
@require_clinic_management
def clinic_cancel_appointment(request, appointment_id):
    """診所取消預約"""
    try:
        vet_profile = request.user.vet_profile
        appointment = get_object_or_404(
            VetAppointment,
            id=appointment_id,
            slot__doctor__clinic=vet_profile.clinic
        )

        # 預定義的取消原因選項（診所視角）
        cancel_reasons = [
            ('patient_no_show', '病患未到診'),
            ('doctor_unavailable', '醫師臨時無法看診'),
            ('equipment_failure', '設備故障'),
            ('emergency_closure', '診所緊急關閉'),
            ('schedule_conflict', '時程衝突'),
            ('patient_cancellation', '病患主動取消'),
            ('weather_emergency', '天氣緊急狀況'),
            ('system_overbook', '系統重複預約'),
            ('other', '其他原因'),
        ]

        if request.method == 'POST':
            cancel_reason_code = request.POST.get('cancel_reason', '')
            custom_reason = request.POST.get('custom_reason', '')

            # 如果選擇其他原因，使用自定義原因
            if cancel_reason_code == 'other' and custom_reason:
                final_reason = f"其他原因：{custom_reason}"
            else:
                # 根據代碼找到對應的中文說明
                reason_dict = dict(cancel_reasons)
                final_reason = reason_dict.get(cancel_reason_code, cancel_reason_code)

            appointment.status = 'cancelled'
            appointment.cancel_reason = final_reason
            appointment.save()

            messages.success(request, f'預約 {appointment.id} 已取消 - {final_reason}')

            # 如果是AJAX請求，返回JSON響應
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': '預約取消成功'})

            return redirect('clinic_appointments')

        # GET請求顯示取消確認頁面
        return render(request, 'clinic/cancel_appointment.html', {
            'appointment': appointment,
            'cancel_reasons': cancel_reasons
        })

    except Exception as e:
        messages.error(request, f'取消預約失敗:{str(e)}')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': str(e)})
        return redirect('clinic_appointments')

# @login_required
# @require_clinic_management
# def complete_appointment(request, appointment_id):
#     """完成預約 - REMOVED: Appointments are now auto-completed when medical records are created"""
#     try:
#         vet_profile = request.user.vet_profile
#         appointment = get_object_or_404(
#             VetAppointment,
#             id=appointment_id,
#             slot__doctor__clinic=vet_profile.clinic
#         )
#
#         if request.method == 'POST':
#             appointment.status = 'completed'
#             appointment.save()
#
#             messages.success(request, f'預約 {appointment.id} 已標記為完成')
#
#         return redirect('clinic_appointments')
#
#     except Exception as e:
#         messages.error(request, f'完成預約失敗:{str(e)}')
#         return redirect('clinic_appointments')

# ============ API 端點實作 ============

@login_required
@require_clinic_management
def api_dashboard_stats(request):
    """API:診所儀表板統計"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        today = timezone.now().date()
        
        # 今日統計
        today_appointments = VetAppointment.objects.filter(
            slot__doctor__clinic=clinic,
            slot__date=today
        )
        
        # 本週統計
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_appointments = VetAppointment.objects.filter(
            slot__doctor__clinic=clinic,
            slot__date__range=[week_start, week_end]
        )
        
        # 本月統計
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
        month_appointments = VetAppointment.objects.filter(
            slot__doctor__clinic=clinic,
            slot__date__range=[month_start, month_end]
        )
        
        stats = {
            'today': {
                'total': today_appointments.count(),
                'confirmed': today_appointments.filter(status='confirmed').count(),
                'pending': today_appointments.filter(status='pending').count(),
                'completed': today_appointments.filter(status='completed').count(),
                'cancelled': today_appointments.filter(status='cancelled').count(),
            },
            'week': {
                'total': week_appointments.count(),
                'completed': week_appointments.filter(status='completed').count(),
            },
            'month': {
                'total': month_appointments.count(),
                'completed': month_appointments.filter(status='completed').count(),
            }
        }
        
        return JsonResponse({'status': 'success', 'data': stats})
        
    except Exception as e:
     return JsonResponse({'success': False, 'message': str(e)})
# Missing functions extracted from views_with_schedule.py

@login_required
@require_owner
def add_adoption(request):
    """新增送養貼文"""
    other_pet_names = list(
        AdoptionPet.objects.filter(owner=request.user).values_list("name", flat=True)
    )

    # 獲取用戶的寵物資料用於快速帶入（排除已刊登且仍在發布的寵物）
    published_pet_ids = AdoptionPet.objects.filter(
        owner=request.user,
        is_publish=True,
        original_pet__isnull=False
    ).values_list('original_pet_id', flat=True)

    my_pets = Pet.objects.filter(owner=request.user).exclude(
        id__in=published_pet_ids
    ).values(
        'id', 'name', 'species', 'breed', 'gender', 'birth_date',
        'weight', 'sterilization_status', 'chip'
    )

    if request.method == 'POST':
        form = AdoptionForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            adoption = form.save(commit=False)
            adoption.owner = request.user

            # 如果是從"我的寵物"帶入，設置original_pet關聯
            my_pet_id = request.POST.get('my_pet_id')
            if my_pet_id:
                try:
                    original_pet = Pet.objects.get(id=my_pet_id, owner=request.user)

                    # 檢查這個寵物是否已經被刊登且仍在發布
                    existing_adoption = AdoptionPet.objects.filter(
                        owner=request.user,
                        original_pet=original_pet,
                        is_publish=True
                    ).first()

                    if existing_adoption:
                        messages.error(request, f"寵物「{original_pet.name}」已經在領養列表中，不能重複刊登")
                        form.add_error(None, f"寵物「{original_pet.name}」已經在領養列表中")
                        return render(request, 'adoptions/add_adoption.html', {
                            'adoption_form': form,
                            'other_pet_names': other_pet_names,
                            'my_pets': list(my_pets),
                            'feature_choices': FEATURE_CHOICES,
                            'physical_choices': PHYSICAL_CHOICES,
                            'adoptcondition_choices': ADOPTCONDITION_CHOICES,
                            'dog_choices': DOG_CHOICES,
                            'cat_choices': CAT_CHOICES,
                            'dogvaccine_choices': DOGVACCINE_CHOICES,
                            'catvaccine_choices': CATVACCINE_CHOICES,
                        })

                    adoption.original_pet = original_pet
                except Pet.DoesNotExist:
                    pass  # 如果寵物不存在或不屬於用戶，忽略

            # 如果沒有設置 original_pet，嘗試自動匹配現有寵物
            if not adoption.original_pet:
                try:
                    # 優先使用晶片號碼匹配
                    if adoption.chip:
                        matching_pet = Pet.objects.filter(
                            chip=adoption.chip,
                            owner=request.user
                        ).first()
                        if matching_pet:
                            adoption.original_pet = matching_pet
                            print(f"通過晶片號碼自動匹配寵物: {matching_pet.name}")

                    # 如果晶片匹配失敗，嘗試精確匹配
                    if not adoption.original_pet:
                        matching_pet = Pet.objects.filter(
                            name=adoption.name,
                            species=adoption.species,
                            breed=adoption.breed,
                            owner=request.user
                        ).first()
                        if matching_pet:
                            adoption.original_pet = matching_pet
                            print(f"通過名字+物種+品種自動匹配寵物: {matching_pet.name}")

                    # 最後嘗試只用名字匹配（如果只有一個匹配結果）
                    if not adoption.original_pet:
                        potential_pets = Pet.objects.filter(
                            name=adoption.name,
                            owner=request.user
                        )
                        if potential_pets.count() == 1:
                            adoption.original_pet = potential_pets.first()
                            print(f"通過名字自動匹配寵物: {adoption.original_pet.name}")

                except Exception as e:
                    print(f"自動匹配寵物時發生錯誤: {e}")

            adoption.save()
            messages.success(request, "刊登成功")
            return redirect('adoption')
        else:
            messages.error(request, "表單驗證失敗，請檢查輸入內容")
    else:
        form = AdoptionForm(owner=request.user)

    return render(request, 'adoptions/add_adoption.html', {
        'adoption_form': form,
        'other_pet_names': other_pet_names,
        'my_pets': list(my_pets),
        'feature_choices': FEATURE_CHOICES,
        'physical_choices': PHYSICAL_CHOICES,
        'adoptcondition_choices': ADOPTCONDITION_CHOICES,
        'dog_choices': DOG_CHOICES,
        'cat_choices': CAT_CHOICES,
        'other_choices': OTHER_CHOICES,
        'dogvaccine_choices': DOGVACCINE_CHOICES,
        'catvaccine_choices': CATVACCINE_CHOICES,
    })


# Function: add_adoptpet (originally at line 8769)
def add_adoptpet(request):
    """新增送養寵物資料"""
    other_pet_names = list(
        AdoptionPet.objects.filter(owner=request.user).values_list("name", flat=True)
    )
    
    if request.method == 'POST':
        form = AdoptionForm(request.POST, request.FILES, owner=request.user)
        
        if form.is_valid():
            adoption = form.save(commit=False)
            adoption.owner = request.user
            adoption.save()
            return redirect('adoption')
        else:
            print(form.errors.as_json())
    else:
        form = AdoptionForm(owner=request.user)

    return render(request, 'adoptions/add_adoptpet.html', {
        'adoption_form': form,
        'other_pet_names': other_pet_names,
        'feature_choices': FEATURE_CHOICES,
        'physical_choices': PHYSICAL_CHOICES,
        'adoptcondition_choices': ADOPTCONDITION_CHOICES,
        'dog_choices': DOG_CHOICES,
        'cat_choices': CAT_CHOICES,
        'dogvaccine_choices': DOGVACCINE_CHOICES,
        'catvaccine_choices': CATVACCINE_CHOICES,
    })


# Function: add_doctor (originally at line 5249)
def add_doctor(request):
    """新增醫師"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        if request.method == 'POST':
            form = VetDoctorForm(request.POST)
            
            # 檢查是否為 AJAX 請求
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            if form.is_valid():
                try:
                    # 創建新醫師的邏輯
                    from django.contrib.auth.models import User
                    from django.db import transaction
                    
                    with transaction.atomic():
                        # 創建新用戶
                        user = User.objects.create_user(
                            username=form.cleaned_data['username'],
                            email=form.cleaned_data['email'],
                            password=form.cleaned_data['password'],
                            first_name=form.cleaned_data['first_name']
                        )
                        
                        # 創建醫師檔案
                        vet_doctor = VetDoctor.objects.create(
                            user=user,
                            clinic=clinic,
                            is_active=True,
                            vet_license_number=form.cleaned_data.get('vet_license_number', ''),
                            years_of_experience=form.cleaned_data.get('years_of_experience', 0),
                            specialization=form.cleaned_data.get('specialization', ''),
                            bio=form.cleaned_data.get('bio', ''),
                        )
                        
                        # 處理權限設定
                        vet_doctor.is_active_veterinarian = form.cleaned_data.get('is_active_veterinarian', False)
                        vet_doctor.is_clinic_admin = form.cleaned_data.get('is_clinic_admin', False)
                        vet_doctor.save()

                        # 創建或更新 Profile，根據權限設置正確的 account_type
                        # 優先級：clinic_admin > veterinarian
                        if vet_doctor.is_clinic_admin:
                            account_type = 'clinic_admin'
                        elif vet_doctor.is_active_veterinarian:
                            account_type = 'veterinarian'
                        else:
                            account_type = 'veterinarian'  # 預設

                        profile, created = Profile.objects.get_or_create(
                            user=user,
                            defaults={
                                'account_type': account_type,
                                'phone_number': ''
                            }
                        )
                        if not created and profile.account_type != account_type:
                            profile.account_type = account_type
                            profile.save()

                        # 發送歡迎郵件
                        try:
                            from django.core.mail import send_mail
                            from django.template.loader import render_to_string
                            from django.conf import settings

                            # 準備郵件內容
                            email_subject = f'歡迎加入 {clinic.clinic_name} - 獸醫師帳號已建立'
                            email_context = {
                                'doctor_name': user.first_name,
                                'clinic_name': clinic.clinic_name,
                                'username': user.username,
                                'email': user.email,
                                'admin_name': request.user.get_full_name() or request.user.username,
                                'login_url': request.build_absolute_uri('/accounts/login/'),
                                'is_admin': vet_doctor.is_clinic_admin,
                                'is_veterinarian': vet_doctor.is_active_veterinarian,
                            }

                            # 發送純文字郵件（簡化版本）
                            email_message = f"""
親愛的 {user.first_name} 醫師，您好：

歡迎加入 {clinic.clinic_name} 的醫療團隊！

您的帳號資訊如下：
- 使用者名稱：{user.username}
- 電子信箱：{user.email}
- 權限設定：{'診所管理員' if vet_doctor.is_clinic_admin else '獸醫師'}

您可以使用以下連結登入系統：
{request.build_absolute_uri('/accounts/login/')}

首次登入後，建議您：
1. 更改密碼
2. 完善個人資料
3. 熟悉系統功能

如有任何問題，請聯繫診所管理員 {request.user.get_full_name() or request.user.username}。

祝工作愉快！

{clinic.clinic_name} 管理系統
"""

                            send_mail(
                                subject=email_subject,
                                message=email_message,
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[user.email],
                                fail_silently=False,
                            )

                            email_sent = True
                            print(f"✅ 歡迎郵件已發送至 {user.email}")

                        except Exception as email_error:
                            email_sent = False
                            print(f"❌ 郵件發送失敗: {email_error}")
                            # 不影響醫師建立，只記錄錯誤

                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': f'醫師 {user.first_name} 建立成功！',
                            'redirect': '/clinic/doctors/'
                        })
                    else:
                        messages.success(request, f'醫師 {user.first_name} 建立成功！')
                        return redirect('manage_doctors')
                        
                except Exception as e:
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': f'建立醫師時發生錯誤:{str(e)}',
                            'errors': {}
                        })
                    else:
                        messages.error(request, f'建立醫師時發生錯誤:{str(e)}')
            else:
                # 表單驗證失敗
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': '請檢查並修正表單中的錯誤',
                        'errors': form.errors
                    })
                # 對於非 AJAX 請求，繼續原有的處理方式
        else:
            form = VetDoctorForm()
        
        # 渲染表單頁面（非 AJAX 請求）
        return render(request, 'clinic/add_doctor.html', {
            'form': form,
            'clinic': clinic
        })
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'系統錯誤:{str(e)}',
                'errors': {}
            })
        else:
            messages.error(request, f'新增醫師失敗:{str(e)}')
            return redirect('manage_doctors')
        
# Function: adoption (originally at line 8800)
def adoption(request):
    """二手領養頁面"""
    adoptions = AdoptionPet.objects.filter(is_adopted=False, is_publish=True)
    print(f"DEBUG: Adoption list query - Found {adoptions.count()} adoptions:")
    for adoption in adoptions:
        print(f"  ID: {adoption.id}, Name: {adoption.name}, Adopted: {adoption.is_adopted}, Published: {adoption.is_publish}")

    location = request.GET.get('adopt_place')
    species = request.GET.get('species')
    gender = request.GET.get('gender')
    age_group = request.GET.get('age_group')
    keyword = request.GET.get('keyword')

    if location:
        adoptions = adoptions.filter(adopt_place=location)
    if species:
        adoptions = adoptions.filter(species=species)
    if gender:
        adoptions = adoptions.filter(gender=gender)
    if age_group:
        if age_group == "0-1":
            adoptions = adoptions.filter(age__lte=1)
        elif age_group == "1-3":
            adoptions = adoptions.filter(age__gt=1, age__lte=3)
        elif age_group == "3-6":
            adoptions = adoptions.filter(age__gt=3, age__lte=6)
        elif age_group == "6+":
            adoptions = adoptions.filter(age__gt=6)
    if keyword:
        adoptions = adoptions.filter(
            Q(name__icontains=keyword) |
            Q(breed__icontains=keyword) |
            Q(feature__icontains=keyword)
        )

    order = request.GET.get('order', 'newest')
    if order == 'oldest':
        adoptions = adoptions.order_by('posted_date')
    else:
        adoptions = adoptions.order_by('-posted_date')

    # 解析 JSON 欄位
    for adoption in adoptions:
        adoption.parsed_feature = safe_json_loads(adoption.feature)

    return render(request, 'adoptions/adoption.html', {
        'adoptions': adoptions,
    })

@login_required

# Function: adoption_petDetail (originally at line 8914)
def adoption_petDetail(request, adoption_id):
    """寵物的詳細資料頁面"""
    adoption = get_object_or_404(AdoptionPet, id=adoption_id)
    image_urls = []

    for i in range(1, 5):
        image_field = getattr(adoption, f'adopt_picture{i}', None)
        if image_field and hasattr(image_field, 'url'):
            image_urls.append(image_field.url)

    is_owner = False
    if request.user.is_authenticated and adoption.owner == request.user:
        is_owner = True

    # 解析 JSON 欄位
    parsed_feature = safe_json_loads(adoption.feature)
    parsed_physical_condition = safe_json_loads(adoption.physical_condition)
    parsed_adoption_condition = safe_json_loads(adoption.adoption_condition)

    return render(request, 'adoptions/adoption_petDetail.html', {
        'adoption': adoption,
        'is_owner': is_owner,
        'image_urls': image_urls,
        'parsed_feature': parsed_feature,
        'parsed_physical_condition': parsed_physical_condition,
        'parsed_adoption_condition': parsed_adoption_condition,
    })

@login_required

# Function: api_appointments_list (originally at line 5114)
def api_appointments_list(request):
    """API:預約列表"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 獲取查詢參數
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        doctor_id = request.GET.get('doctor_id')
        status = request.GET.get('status')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        # 基本查詢
        appointments = VetAppointment.objects.filter(
            slot__doctor__clinic=clinic
        ).select_related(
            'pet', 'owner', 'slot', 'slot__doctor__user'
        ).order_by('-slot__date', '-slot__start_time')
        
        # 日期過濾
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                appointments = appointments.filter(slot__date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                appointments = appointments.filter(slot__date__lte=date_to_obj)
            except ValueError:
                pass
        
        # 醫師過濾
        if doctor_id:
            appointments = appointments.filter(slot__doctor_id=doctor_id)
        
        # 狀態過濾
        if status:
            appointments = appointments.filter(status=status)
        
        # 分頁
        paginator = Paginator(appointments, per_page)
        page_obj = paginator.get_page(page)
        
        # 序列化資料
        appointment_data = []
        for appointment in page_obj:
            appointment_data.append({
                'id': appointment.id,
                'pet_name': appointment.pet.name,
                'pet_species': appointment.pet.get_species_display(),
                'owner_name': appointment.owner.get_full_name() or appointment.owner.username,
                'owner_phone': getattr(appointment.owner.profile, 'phone_number', ''),
                'doctor_name': appointment.slot.doctor.user.get_full_name(),
                'date': appointment.slot.date.isoformat(),
                'start_time': appointment.slot.start_time.strftime('%H:%M'),
                'end_time': appointment.slot.end_time.strftime('%H:%M'),
                'status': appointment.status,
                'status_display': appointment.get_status_display(),
                'notes': appointment.notes,
                'created_at': appointment.created_at.isoformat(),
            })
        
        return JsonResponse({
            'status': 'success',
            'data': appointment_data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_clinic_management

# Function: api_can_switch_mode (originally at line 7113)
def api_can_switch_mode(request):
    """API:檢查是否可以切換模式"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 檢查是否有未來的預約
        future_appointments = VetAppointment.objects.filter(
            slot__doctor__clinic=clinic,
            slot__date__gte=timezone.now().date(),
            status__in=['pending', 'confirmed']
        ).count()
        
        # 檢查是否有多個醫師
        doctor_count = VetDoctor.objects.filter(clinic=clinic, is_active=True).count()
        
        can_switch = future_appointments == 0
        warning_message = None
        
        if not can_switch:
            warning_message = f'無法切換模式:還有 {future_appointments} 個未來的預約'
        elif doctor_count > 1:
            warning_message = '切換到單一醫師模式將會停用其他醫師的排班'
        
        return JsonResponse({
            'status': 'success',
            'can_switch': can_switch,
            'warning_message': warning_message,
            'future_appointments': future_appointments,
            'doctor_count': doctor_count
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_verified_vet 

# Function: api_clinic_business_hours (originally at line 6595)
def api_clinic_business_hours(request):
    """API:診所營業時間管理"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        if request.method == 'GET':
            # 獲取營業時間
            business_hours = {}
            for day in range(7):
                schedules = VetSchedule.objects.filter(
                    doctor__clinic=clinic,
                    weekday=day,
                    is_active=True
                ).aggregate(
                    earliest_start=models.Min('start_time'),
                    latest_end=models.Max('end_time')
                )
                
                if schedules['earliest_start'] and schedules['latest_end']:
                    business_hours[day] = {
                        'day_name': ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][day],
                        'start_time': schedules['earliest_start'].strftime('%H:%M'),
                        'end_time': schedules['latest_end'].strftime('%H:%M'),
                        'is_open': True
                    }
                else:
                    business_hours[day] = {
                        'day_name': ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][day],
                        'is_open': False
                    }
            
            return JsonResponse({
                'status': 'success',
                'business_hours': business_hours
            })
        
        elif request.method == 'POST':
            # 更新營業時間（這裡可以實現批量更新邏輯）
            data = json.loads(request.body)
            # 實現營業時間更新邏輯
            return JsonResponse({
                'status': 'success',
                'message': '營業時間更新成功'
            })
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ============ 通知系統實作 ============

@login_required

# Function: api_clinic_settings (originally at line 5198)
def api_clinic_settings(request):
    """API:診所設定"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        if request.method == 'GET':
            settings_data = {
                'clinic_name': clinic.clinic_name,
                'clinic_phone': clinic.clinic_phone,
                'clinic_email': clinic.clinic_email,
                'clinic_address': clinic.clinic_address,
                'clinic_mode': clinic.clinic_mode,
                'default_appointment_duration': clinic.default_appointment_duration,
                'advance_booking_days': clinic.advance_booking_days,
            }
            
            return JsonResponse({
                'status': 'success',
                'data': settings_data
            })
            
        elif request.method == 'POST':
            data = json.loads(request.body)
            
            # 更新基本資訊
            if 'clinic_phone' in data:
                clinic.clinic_phone = data['clinic_phone']
            if 'clinic_email' in data:
                clinic.clinic_email = data['clinic_email']
            if 'clinic_address' in data:
                clinic.clinic_address = data['clinic_address']
            if 'default_appointment_duration' in data:
                clinic.default_appointment_duration = int(data['default_appointment_duration'])
            if 'advance_booking_days' in data:
                clinic.advance_booking_days = int(data['advance_booking_days'])
            
            clinic.save()
            
            return JsonResponse({
                'status': 'success',
                'message': '診所設定更新成功'
            })
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# ============ 醫師管理功能完善 ============

@login_required
@require_clinic_management

# Function: api_clinic_status (originally at line 7905)
def api_clinic_status(request):
    """API:診所狀態"""
    try:
        # 檢查用戶是否有診所關聯
        vet_profile = getattr(request.user, 'vet_profile', None)
        if not vet_profile or not vet_profile.clinic:
            return JsonResponse({'status': 'no_clinic'})
        
        clinic = vet_profile.clinic
        
        # 獲取診所基本狀態
        status_data = {
            'clinic_name': clinic.clinic_name,
            'is_verified': clinic.is_verified,
            'clinic_mode': clinic.clinic_mode,
            'is_admin': vet_profile.is_clinic_admin,
            'doctor_count': VetDoctor.objects.filter(
                clinic=clinic,
                is_active=True
            ).count()
        }
        
        return JsonResponse({'status': 'success', 'data': status_data})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_verified_vet

# Function: api_doctors_status (originally at line 7150)
def api_doctors_status(request):
    """API:獲取醫師狀態"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        doctors = VetDoctor.objects.filter(clinic=clinic, is_active=True).select_related('user')
        
        doctors_data = []
        for doctor in doctors:
            # 檢查是否今日有排班
            today = timezone.now().date()
            has_schedule_today = VetSchedule.objects.filter(
                doctor=doctor,
                weekday=today.weekday(),
                is_active=True
            ).exists()
            
            # 檢查今日預約數
            today_appointments = VetAppointment.objects.filter(
                slot__doctor=doctor,
                slot__date=today,
                status__in=['confirmed', 'completed']
            ).count()
            
            doctors_data.append({
                'id': doctor.id,
                'name': doctor.user.get_full_name(),
                'is_active': doctor.is_active,
                'has_schedule_today': has_schedule_today,
                'today_appointments': today_appointments,
                'status': 'online' if has_schedule_today else 'offline'
            })
        
        return JsonResponse({
            'success': True,
            'data': doctors_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ============ 統計和報表功能 ============

@login_required
@require_clinic_management

# Function: api_get_business_hours (originally at line 6230)
def api_get_business_hours(request):
    """API:獲取營業時間"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 獲取所有預設營業時間記錄（包括營業和休息）
        business_hours = ClinicBusinessHoursRecord.objects.filter(
            clinic=clinic,
            is_default=True  # 獲取所有預設記錄
        ).order_by('weekday', 'start_time')
        
        # 按天組織數據
        hours_by_day = {}
        for day in range(7):
            hours_by_day[str(day)] = []
        
        for hour in business_hours:
            # 只返回營業日的時段資訊，休息日保持空陣列
            if hour.status == 'open' and hour.start_time and hour.end_time:
                # 過濾掉休息日的特殊時間標記 (00:00-00:01)
                if not (hour.start_time.hour == 0 and hour.start_time.minute == 0 and 
                       hour.end_time.hour == 0 and hour.end_time.minute == 1):
                    hours_by_day[str(hour.weekday)].append({
                        'startTime': hour.start_time.strftime('%H:%M'),
                        'endTime': hour.end_time.strftime('%H:%M'),
                        'id': hour.id,
                        'status': hour.status,
                        'notes': hour.notes or ''
                    })
        
        return JsonResponse({
            'success': True,
            'business_hours': hours_by_day,
            'message': '營業時間載入成功'
        })
        
    except AttributeError as e:
        return JsonResponse({
            'success': False,
            'message': f'模型屬性錯誤: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'載入營業時間失敗: {str(e)}'
        })

@require_clinic_management_api
@require_http_methods(["POST"])

# Function: api_get_clinic_mode (originally at line 7030)
def api_get_clinic_mode(request):
    """API:獲取診所模式或執行模式切換"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        if request.method == 'GET':
            # 獲取診所模式資訊
            doctor_count = VetDoctor.objects.filter(clinic=clinic, is_active=True).count()
            
            if doctor_count <= 1:
                mode = 'single_doctor'
                mode_name = '單一醫師模式'
                description = '適合個人執業或小型診所'
            else:
                mode = 'multi_doctor'
                mode_name = '多醫師模式'
                description = '適合大型診所或動物醫院'
            
            return JsonResponse({
                'status': 'success',
                'mode': {
                    'type': mode,
                    'name': mode_name,
                    'description': description,
                    'doctor_count': doctor_count
                }
            })
            
        elif request.method == 'POST':
            # 執行模式切換
            import json
            data = json.loads(request.body)
            target_mode = data.get('mode', 'single')
            
            # 再次檢查是否可以切換
            future_appointments = VetAppointment.objects.filter(
                slot__doctor__clinic=clinic,
                slot__date__gte=timezone.now().date(),
                status__in=['pending', 'confirmed']
            ).count()
            
            if future_appointments > 0:
                return JsonResponse({
                    'status': 'error',
                    'message': f'無法切換模式:診所有 {future_appointments} 個未來預約待處理'
                })
            
            # 執行模式切換邏輯
            if target_mode == 'single':
                # 切換到單獸醫模式
                clinic.clinic_mode = 'single'
                clinic.save()
                
                # 記錄模式切換
                from django.contrib.admin.models import LogEntry, CHANGE
                from django.contrib.contenttypes.models import ContentType
                LogEntry.objects.log_action(
                    user_id=request.user.pk,
                    content_type_id=ContentType.objects.get_for_model(clinic).pk,
                    object_id=clinic.pk,
                    object_repr=str(clinic),
                    action_flag=CHANGE,
                    change_message='切換到單獸醫模式'
                )
                
                return JsonResponse({
                    'status': 'success',
                    'message': '已成功切換到單獸醫模式',
                    'new_mode': 'single',
                    'redirect_url': '/clinic/dashboard/'  # 改為跳轉到儀表板
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': '不支援的模式切換'
                })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_clinic_management

# Function: api_load_doctors (originally at line 8077)
def api_load_doctors(request):
    """API:載入醫師列表"""
    try:
        clinic_id = request.GET.get('clinic_id')
        if not clinic_id:
            return JsonResponse({'status': 'error', 'message': '缺少診所 ID'})
        
        doctors = VetDoctor.objects.filter(
            clinic_id=clinic_id,
            is_active=True,
            is_active_veterinarian=True  # 只顯示啟用獸醫師身份的醫師
        ).select_related('user')
        
        doctor_data = []
        for doctor in doctors:
            doctor_data.append({
                'id': doctor.id,
                'name': doctor.user.get_full_name() or doctor.user.username,
                'specialization': getattr(doctor, 'specialization', ''),
                'is_available': doctor.is_active
            })
        
        return JsonResponse({'status': 'success', 'doctors': doctor_data})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# Function: api_load_time_slots (originally at line 8103)
def api_load_time_slots(request):
    """API:載入時間段"""
    try:
        doctor_id = request.GET.get('doctor_id')
        clinic_id = request.GET.get('clinic_id')
        date_str = request.GET.get('date')

        if not date_str:
            return JsonResponse({'status': 'error', 'message': '缺少日期參數'})

        if not doctor_id and not clinic_id:
            return JsonResponse({'status': 'error', 'message': '需要醫師ID或診所ID'})

        # 解析日期
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'status': 'error', 'message': '日期格式錯誤'})

        # 獲取該醫師/診所在該日期的可用時段 - 使用新的 EnhancedVetSchedule
        weekday = appointment_date.weekday()

        # 查找活躍的排班
        schedule_filter = Q(status='active', start_date__lte=appointment_date) & (Q(end_date__isnull=True) | Q(end_date__gte=appointment_date))

        if doctor_id:
            # 指定醫師的排班
            enhanced_schedules = EnhancedVetSchedule.objects.filter(doctor_id=doctor_id).filter(schedule_filter)
        else:
            # 診所所有醫師的排班
            enhanced_schedules = EnhancedVetSchedule.objects.filter(doctor__clinic_id=clinic_id).filter(schedule_filter)
        
        # 先生成所有基本時段，包含醫師信息
        basic_slots = []
        doctor_time_mapping = {}  # 記錄每個時段對應的醫師

        for schedule in enhanced_schedules:
            # 檢查該排班是否包含今天的工作日
            if weekday in schedule.weekdays:
                # 獲取該工作日的時段設定
                day_slots = schedule.daily_time_slots.get(str(weekday), [])

                for time_slot in day_slots:
                    try:
                        start_time = datetime.strptime(time_slot['start'], '%H:%M').time()
                        end_time = datetime.strptime(time_slot['end'], '%H:%M').time()

                        # 生成該時段內的所有預約時間點
                        current_time = datetime.combine(appointment_date, start_time)
                        slot_end = datetime.combine(appointment_date, end_time)

                        # 使用排班設定的預約時長，預設30分鐘
                        duration_minutes = getattr(schedule, 'appointment_duration', 30)

                        while current_time.time() < slot_end.time():
                            time_str = current_time.time().strftime('%H:%M')

                            # 為診所模式時，記錄時段對應的醫師
                            if not doctor_id:  # 只有在診所模式時才需要記錄
                                if time_str not in doctor_time_mapping:
                                    doctor_time_mapping[time_str] = schedule.doctor.id

                            # 避免重複時段
                            if not any(slot['time'] == time_str for slot in basic_slots):
                                slot_data = {
                                    'time': time_str,
                                    'value': current_time.time().strftime('%H:%M:%S')
                                }
                                # 如果是診所模式，加入醫師信息
                                if not doctor_id:
                                    slot_data['doctor_id'] = schedule.doctor.id
                                    slot_data['doctor_name'] = schedule.doctor.user.get_full_name()

                                basic_slots.append(slot_data)
                            current_time += timedelta(minutes=duration_minutes)
                    except (ValueError, KeyError) as e:
                        # 處理時間格式錯誤
                        continue
        
        # 獲取已預約的時段（來自VetAppointment而不是AppointmentSlot）
        if doctor_id:
            # 指定醫師的預約
            existing_appointments = VetAppointment.objects.filter(
                slot__doctor_id=doctor_id,
                slot__date=appointment_date,
                status__in=['confirmed', 'pending']
            ).values_list('slot__start_time', flat=True)
        else:
            # 診所所有醫師的預約
            existing_appointments = VetAppointment.objects.filter(
                slot__clinic_id=clinic_id,
                slot__date=appointment_date,
                status__in=['confirmed', 'pending']
            ).values_list('slot__start_time', flat=True)
        
        # 獲取當前時間（用於過濾過去的時間）
        from django.utils import timezone
        now = timezone.now()
        current_time = now.time()
        is_today = appointment_date == now.date()
        
        # 對時段進行排序
        basic_slots.sort(key=lambda x: x['time'])

        # 處理每個時段的可用性
        slot_data = []
        for slot in basic_slots:
            slot_time = datetime.strptime(slot['time'], '%H:%M').time()
            
            # 檢查是否為過去的時間
            is_past = is_today and slot_time < current_time
            
            # 檢查是否已被預約
            is_booked = slot_time in existing_appointments
            
            # 決定時段狀態
            if is_past:
                status = 'past'
                available = False
                css_class = 'time-slot-past'
                title = '已過時間'
            elif is_booked:
                status = 'booked' 
                available = False
                css_class = 'time-slot-booked'
                title = '已預約'
            else:
                status = 'available'
                available = True
                css_class = 'time-slot-available'
                title = '可預約'
            
            result_slot = {
                'time': slot['time'],
                'value': slot['value'],
                'available': available,
                'status': status,
                'css_class': css_class,
                'title': title
            }

            # 如果是診所模式（沒有指定醫師），包含醫師信息
            if not doctor_id and 'doctor_id' in slot:
                result_slot['doctor_id'] = slot['doctor_id']
                result_slot['doctor_name'] = slot['doctor_name']

            slot_data.append(result_slot)
        
        return JsonResponse({'status': 'success', 'slots': slot_data})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# ============ 排班相關缺失的 API 函數 ============

@require_clinic_management_api

# Function: api_process_expired_appointments (originally at line 6745)
def api_process_expired_appointments(request):
    """API: 處理過期預約"""
    try:
        data = json.loads(request.body) if request.body else {}
        days_back = data.get('days_back', 1)
        mark_as = data.get('mark_as', 'cancelled')  # 預設為已取消
        
        # 驗證 mark_as 參數
        if mark_as not in ['cancelled', 'no_show']:
            mark_as = 'cancelled'
        
        # 如果是獸醫師，只處理自己診所的預約
        clinic = None
        if hasattr(request.user, 'vet_profile'):
            clinic = request.user.vet_profile.clinic
        
        # 處理過期預約
        result = process_expired_appointments(days_back=days_back, mark_as=mark_as)
        
        # 如果指定了診所，則篩選結果
        if clinic:
            # 重新篩選結果只包含該診所的預約
            clinic_result = get_expired_appointments_summary(clinic=clinic, days_back=days_back)
            result.update({
                'clinic_name': clinic.clinic_name,
                'clinic_specific': True
            })
        
        status_display = '已取消' if mark_as == 'cancelled' else '未到診'
        return JsonResponse({
            'success': True,
            'message': f'成功處理 {result["processed_count"]} 筆過期預約，狀態標記為:{status_display}',
            'result': result,
            'mark_as': mark_as
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'處理過期預約失敗:{str(e)}'
        })

# ============ 排班 API 功能 ============

@login_required
@require_clinic_management

# Function: api_save_business_hours (originally at line 6280)
def api_save_business_hours(request):
    """API:保存營業時間"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 解析JSON數據
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({
                'success': False,
                'message': f'JSON解析錯誤: {str(e)}'
            })
        
        business_hours_data = data.get('business_hours', {})
        special_dates_data = data.get('special_dates', [])
        
        if not business_hours_data:
            return JsonResponse({
                'success': False,
                'message': '沒有收到營業時間數據'
            })
        
        with transaction.atomic():
            # 清除現有的所有預設營業時間記錄 (包括營業和休息)
            ClinicBusinessHoursRecord.objects.filter(
                clinic=clinic,
                is_default=True
            ).delete()
            
            created_count = 0
            
            # 處理所有7天的設定
            for day in range(7):
                periods = business_hours_data.get(str(day), [])
                
                if periods:
                    # 有時段 = 營業日
                    for order, period in enumerate(periods):
                        # 處理不同的時間格式
                        start_time_str = period.get('start_time') or period.get('startTime')
                        end_time_str = period.get('end_time') or period.get('endTime')
                        
                        if not (start_time_str and end_time_str):
                            continue
                        
                        try:
                            start_time = datetime.strptime(start_time_str, '%H:%M').time()
                            end_time = datetime.strptime(end_time_str, '%H:%M').time()
                            
                            # 驗證時間邏輯
                            if start_time >= end_time:
                                return JsonResponse({
                                    'success': False,
                                    'message': f'星期{day+1}的時間設定錯誤:結束時間必須晚於開始時間'
                                })
                            
                            # 創建營業時間記錄
                            ClinicBusinessHoursRecord.objects.create(
                                clinic=clinic,
                                weekday=day,
                                start_time=start_time,
                                end_time=end_time,
                                status='open',
                                order=order,
                                is_default=True,
                                created_by=request.user
                            )
                            created_count += 1
                            
                        except ValueError as e:
                            return JsonResponse({
                                'success': False,
                                'message': f'時間格式錯誤: {str(e)}'
                            })
                        except Exception as e:
                            return JsonResponse({
                                'success': False,
                                'message': f'創建營業時間記錄失敗: {str(e)}'
                            })
                else:
                    # 沒有時段 = 休息日，創建休息記錄
                    try:
                        ClinicBusinessHoursRecord.objects.create(
                            clinic=clinic,
                            weekday=day,
                            start_time=datetime.strptime('00:00', '%H:%M').time(),
                            end_time=datetime.strptime('00:01', '%H:%M').time(),  # 使用 00:01 避免驗證錯誤
                            status='closed',  # 使用正確的狀態值
                            order=0,
                            is_default=True,
                            created_by=request.user,
                            notes='休息日'
                        )
                        created_count += 1
                    except Exception as e:
                        return JsonResponse({
                            'success': False,
                            'message': f'創建休息日記錄失敗: {str(e)}'
                        })
            
            # 處理特殊日期設定
            special_created_count = 0
            
            # 獲取醫師信息（用於創建排班記錄）
            doctor = VetDoctor.objects.filter(
                clinic=clinic,
                is_clinic_admin=True,
                is_active=True
            ).first() or VetDoctor.objects.filter(clinic=clinic, is_active=True).first()
            
            for special_date in special_dates_data:
                try:
                    date_str = special_date.get('date')
                    date_type = special_date.get('type')
                    start_time_str = special_date.get('startTime', '09:00')
                    end_time_str = special_date.get('endTime', '17:00')
                    
                    if not date_str or not date_type:
                        continue
                    
                    # 解析日期
                    try:
                        specific_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        weekday = specific_date.weekday()  # 0=週一, 6=週日
                    except ValueError:
                        continue
                    
                    # 先刪除該日期的現有特殊設定
                    ClinicBusinessHoursRecord.objects.filter(
                        clinic=clinic,
                        effective_date=specific_date,
                        is_default=False
                    ).delete()
                    
                    # 同時刪除該日期的特殊排班
                    if doctor:
                        VetSchedule.objects.filter(
                            doctor=doctor,
                            valid_from=specific_date,
                            valid_until=specific_date
                        ).delete()
                    
                    if date_type == 'open':
                        # 營業日:創建營業時間記錄和排班
                        try:
                            start_time = datetime.strptime(start_time_str, '%H:%M').time()
                            end_time = datetime.strptime(end_time_str, '%H:%M').time()
                            
                            if start_time >= end_time:
                                continue  # 跳過無效時間
                            
                            # 創建營業時間記錄
                            ClinicBusinessHoursRecord.objects.create(
                                clinic=clinic,
                                weekday=weekday,
                                start_time=start_time,
                                end_time=end_time,
                                status='open',
                                effective_date=specific_date,
                                is_default=False,
                                created_by=request.user,
                                notes=f'特殊日期營業: {date_str}'
                            )
                            
                            # 創建對應的排班記錄
                            if doctor:
                                VetSchedule.objects.create(
                                    doctor=doctor,
                                    weekday=weekday,
                                    start_time=start_time,
                                    end_time=end_time,
                                    appointment_duration=30,
                                    max_appointments_per_slot=1,
                                    schedule_type='clinic',
                                    notes=f'特殊日期排班: {date_str}',
                                    is_active=True,
                                    valid_from=specific_date,
                                    valid_until=specific_date
                                )
                                
                            special_created_count += 1
                        except ValueError:
                            continue  # 跳過無效時間格式
                    else:
                        # 休息日或特殊休假:創建關閉記錄
                        status = 'closed' if date_type == 'closed' else 'holiday'
                        
                        ClinicBusinessHoursRecord.objects.create(
                            clinic=clinic,
                            weekday=weekday,
                            start_time=datetime.strptime('00:00', '%H:%M').time(),
                            end_time=datetime.strptime('00:01', '%H:%M').time(),  # 避免驗證錯誤
                            status=status,
                            effective_date=specific_date,
                            is_default=False,
                            created_by=request.user,
                            notes=f'特殊日期休息: {date_str}'
                        )
                        
                        # 特殊休息日不需要創建排班記錄，保持該天為空
                        special_created_count += 1
                        
                except Exception as e:
                    # 記錄錯誤但不中斷處理
                    continue
        
        total_message = f'營業時間已成功保存，共創建 {created_count} 條週期性記錄'
        if special_created_count > 0:
            total_message += f'，{special_created_count} 條特殊日期記錄'
        
        return JsonResponse({
            'success': True,
            'message': total_message,
            'created_count': created_count,
            'special_created_count': special_created_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'保存營業時間時發生錯誤: {str(e)}'
        })


@login_required
@require_clinic_management  

# Function: api_search_clinics (originally at line 4820)
def api_search_clinics(request):

    """API:搜尋診所"""
    try:
        query = request.GET.get('q', '').strip()
        city = request.GET.get('city', '').strip()
        service_type = request.GET.get('service', '').strip()
        
        clinics = VetClinic.objects.filter(is_verified=True)
        
        if query:
            clinics = clinics.filter(
                Q(clinic_name__icontains=query) |
                Q(clinic_address__icontains=query)
            )
        
        if city:
            clinics = clinics.filter(clinic_address__icontains=city)
        
        # 限制結果數量
        clinics = clinics[:20]
        
        clinic_data = []
        for clinic in clinics:
            # 獲取診所醫師
            doctors = VetDoctor.objects.filter(
                clinic=clinic,
                is_active=True
            ).select_related('user')
            
            doctor_list = []
            for doctor in doctors:
                doctor_list.append({
                    'name': doctor.user.get_full_name() or doctor.user.username,
                    'specialization': getattr(doctor, 'specialization', '')
                })
            
            clinic_data.append({
                'id': clinic.id,
                'name': clinic.clinic_name,
                'address': clinic.clinic_address,
                'phone': clinic.clinic_phone,
                'email': clinic.clinic_email,
                'doctors': doctor_list,
                'mode': clinic.get_clinic_mode_display()
            })
        
        return JsonResponse({
            'status': 'success',
            'clinics': clinic_data,
            'total': len(clinic_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required

# Function: api_vet_patients_overview (originally at line 7934)
def api_vet_patients_overview(request):
    """API:獸醫師患者概覽"""
    try:
        # 處理診所管理員或獸醫師
        profile = request.user.profile
        filter_type = request.GET.get('filter', 'all')

        # 獲取獸醫師profile
        if profile.account_type == 'clinic_admin':
            try:
                vet_profile = request.user.vet_profile
            except AttributeError:
                # 沒有 vet_profile，返回診所的所有患者
                clinic = request.user.clinic_profile.clinic
                patients_qs = Pet.objects.filter(
                    vetappointment__slot__doctor__clinic=clinic
                ).distinct().select_related('owner').prefetch_related(
                    'vetappointment_set', 'medicalrecord_set'
                )
        else:
            vet_profile = request.user.vet_profile
            patients_qs = Pet.objects.filter(
                vetappointment__slot__doctor=vet_profile
            ).distinct().select_related('owner').prefetch_related(
                'vetappointment_set', 'medicalrecord_set'
            )

        # 根據篩選類型過濾
        today = timezone.now().date()
        if filter_type == 'recent':
            # 最近30天有就診的
            recent_date = today - timezone.timedelta(days=30)
            patients_qs = patients_qs.filter(
                vetappointment__slot__date__gte=recent_date
            ).distinct()
        elif filter_type == 'followup':
            # 需要追蹤的病患
            patients_qs = patients_qs.filter(
                Q(medicalrecord__diagnosis__icontains='慢性') |
                Q(medicalrecord__diagnosis__icontains='定期') |
                Q(medicalrecord__diagnosis__icontains='追蹤') |
                Q(medicalrecord__diagnosis__icontains='複診') |
                Q(medicalrecord__treatment__icontains='定期') |
                Q(medicalrecord__treatment__icontains='追蹤')
            ).distinct()
        elif filter_type == 'new':
            # 新病患 (第一次就診在30天內)
            recent_date = today - timezone.timedelta(days=30)
            patients_qs = patients_qs.annotate(
                first_visit=Min('vetappointment__slot__date')
            ).filter(first_visit__gte=recent_date)

        # 限制數量
        patients_qs = patients_qs[:20]

        patients_data = []
        for pet in patients_qs:
            # 計算是否需要追蹤
            needs_followup = False
            last_visit = None

            # 獲取最後就診日期
            last_appointment = pet.vetappointment_set.order_by('-slot__date').first()
            if last_appointment:
                last_visit = last_appointment.slot.date.strftime('%Y-%m-%d')
                days_since_visit = (today - last_appointment.slot.date).days

                # 檢查是否需要追蹤
                if days_since_visit > 30:
                    needs_followup = True

                # 檢查醫療記錄是否有追蹤關鍵字
                last_record = pet.medicalrecord_set.order_by('-visit_date').first()
                if last_record:
                    followup_keywords = ['慢性', '定期', '追蹤', '複診', '監控', '持續', '回診']
                    if last_record.diagnosis:
                        for keyword in followup_keywords:
                            if keyword in last_record.diagnosis:
                                needs_followup = True
                                break
                    if last_record.treatment and not needs_followup:
                        for keyword in followup_keywords:
                            if keyword in last_record.treatment:
                                needs_followup = True
                                break
            else:
                last_visit = '無記錄'

            patients_data.append({
                'id': pet.id,
                'name': pet.name,
                'species': pet.species,
                'breed': pet.breed or '未知',
                'owner_name': pet.owner.get_full_name() or pet.owner.username,
                'picture': pet.picture.url if pet.picture else None,
                'last_visit': last_visit,
                'needs_followup': needs_followup,
                'category': filter_type
            })

        return JsonResponse({'success': True, 'patients': patients_data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_verified_vet

# Function: api_vet_today_schedule (originally at line 8015)
def api_vet_today_schedule(request):
    """API:獸醫師今日排程"""
    try:
        # 處理診所管理員或獸醫師
        profile = request.user.profile
        today = timezone.now().date()
        
        if profile.account_type == 'clinic_admin':
            # 診所管理員:嘗試獲取 vet_profile 或使用診所資料
            try:
                vet_profile = request.user.vet_profile
            except AttributeError:
                # 沒有 vet_profile，返回診所的所有預約
                clinic = request.user.clinic_profile.clinic
                today_appointments = VetAppointment.objects.filter(
                    slot__doctor__clinic=clinic,
                    slot__date=today
                ).select_related('pet', 'owner', 'slot__doctor').order_by('slot__start_time')
                
                schedule_data = []
                for appointment in today_appointments:
                    schedule_data.append({
                        'id': str(appointment.id),
                        'type': 'appointment',
                        'time': appointment.slot.start_time.strftime('%H:%M'),
                        'title': f'預約看診 - Dr. {appointment.slot.doctor.user.get_full_name() or appointment.slot.doctor.user.username}',
                        'status': appointment.status,
                        'patient': {
                            'petName': appointment.pet.name,
                            'ownerName': appointment.owner.get_full_name() or appointment.owner.username
                        }
                    })
                
                return JsonResponse({'success': True, 'schedule': schedule_data})
        else:
            vet_profile = request.user.vet_profile
        
        # 獲取今日預約（不查詢 VetSchedule，因為可能沒有 date 欄位）
        today_appointments = VetAppointment.objects.filter(
            slot__doctor=vet_profile,
            slot__date=today
        ).select_related('pet', 'owner', 'slot').order_by('slot__start_time')
        
        schedule_data = []
        for appointment in today_appointments:
            schedule_data.append({
                'id': str(appointment.id),
                'type': 'appointment', 
                'time': appointment.slot.start_time.strftime('%H:%M'),
                'title': '預約看診',
                'status': appointment.status,
                'patient': {
                    'petName': appointment.pet.name,
                    'ownerName': appointment.owner.get_full_name() or appointment.owner.username
                }
            })
        
        return JsonResponse({'success': True, 'schedule': schedule_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# Function: change_owner (originally at line 9153)
def change_owner(request, pet_id):
    """更改飼主"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    
    if request.method == 'POST':
        form = TransferRequestForm(request.POST)
        if form.is_valid():
            to_email = form.cleaned_data['to_email']
            to_phone = form.cleaned_data['to_phone']
            
            # 檢查不能轉讓給自己
            if to_email == request.user.email:
                messages.error(request, "不能將寵物轉讓給自己")
                return render(request, 'adoptions/change_owner.html', {'form': form, 'pet': pet})

            # 查找目標用戶
            try:
                to_user = User.objects.get(email=to_email)
                to_profile = Profile.objects.get(user=to_user)

                if to_profile.phone_number != to_phone:
                    messages.error(request, "郵箱與手機號碼不匹配。")
                    return render(request, 'adoptions/change_owner.html', {'form': form, 'pet': pet})

            except User.DoesNotExist:
                messages.error(request, f"Email地址 {to_email} 不存在於系統中，請確認對方已註冊帳號。")
                return render(request, 'adoptions/change_owner.html', {'form': form, 'pet': pet})
            except Profile.DoesNotExist:
                messages.error(request, "該用戶尚未完善個人資料，無法進行轉讓。")
                return render(request, 'adoptions/change_owner.html', {'form': form, 'pet': pet})

            # 檢查是否已有相同目標的新請求
            existing_request = TransferRequest.objects.filter(
                pet=pet,
                to_email=to_email,
                status='pending'
            ).first()

            if existing_request:
                messages.warning(request, "已經有針對這個信箱的轉讓請求在處理中。")
            else:
                transfer_request = form.save(commit=False)
                transfer_request.pet = pet
                transfer_request.from_owner = request.user
                transfer_request.to_user = to_user
                transfer_request.save()
                
                messages.success(request, "轉讓請求已送出，等待對方確認。")
            
            return redirect('pet_list')
    else:
        form = TransferRequestForm()

    return render(request, 'adoptions/change_owner.html', {
        'form': form,
        'pet': pet,
    })

@login_required

# Function: check_clinic_mode (originally at line 6003)
def check_clinic_mode(request):
    """檢查診所模式和模式切換可行性"""
    try:
        vet_profile = getattr(request.user, 'vet_profile', None)
        if not vet_profile or not vet_profile.clinic:
            return JsonResponse({
                'has_clinic': False,
                'message': '未關聯到診所'
            })
        
        clinic = vet_profile.clinic
        
        if request.method == 'GET':
            # 返回診所模式資訊
            return JsonResponse({
                'has_clinic': True,
                'clinic_mode': clinic.clinic_mode,
                'clinic_name': clinic.clinic_name,
                'is_admin': vet_profile.is_clinic_admin
            })
            
        elif request.method == 'POST':
            # 檢查是否可以切換模式
            import json
            data = json.loads(request.body)
            target_mode = data.get('mode', 'single')
            
            # 檢查是否有未來的預約
            future_appointments = VetAppointment.objects.filter(
                slot__doctor__clinic=clinic,
                slot__date__gte=timezone.now().date(),
                status__in=['pending', 'confirmed']
            ).count()
            
            # 檢查醫師數量
            doctor_count = VetDoctor.objects.filter(clinic=clinic, is_active=True).count()
            
            can_switch = future_appointments == 0
            reason = ""
            
            if not can_switch:
                reason = f"無法切換:診所有 {future_appointments} 個未來預約待處理"
            elif target_mode == 'single' and doctor_count > 1:
                reason = "警告:切換到單獸醫模式將影響其他醫師的排班"
            
            return JsonResponse({
                'can_switch': can_switch,
                'reason': reason,
                'doctor_count': doctor_count,
                'future_appointments': future_appointments
            })
        
    except Exception as e:
        return JsonResponse({
            'has_clinic': False,
            'error': str(e)
        })



# ============ 單一醫師模式快速設定 ============

@login_required
# Function: delete_adoption (originally at line 9140)
def delete_adoption(request, pk):
    """刪除送養寵物的資料"""
    adoption = get_object_or_404(AdoptionPet, pk=pk)
    if adoption.owner != request.user:
        return redirect('adoption_petDetail', adoption_id=pk)

    if request.method == 'POST':
        adoption.delete()
        return redirect('adoption')

    return redirect('adoption_petDetail', adoption_id=pk)

@login_required

# Function: delete_adoption_image (originally at line 9098)
def delete_adoption_image(request, adoption_id, picture_field):
    """刪除送養圖片"""
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid request method')

    adoption = get_object_or_404(AdoptionPet, pk=adoption_id)

    if adoption.owner != request.user:
        return HttpResponseForbidden('Permission denied')

    allowed_fields = ['adopt_picture1', 'adopt_picture2', 'adopt_picture3', 'adopt_picture4']
    if picture_field not in allowed_fields:
        return HttpResponseBadRequest('Invalid picture field')

    image_field = getattr(adoption, picture_field, None)

    if image_field:
        if os.path.exists(image_field.path):
            os.remove(image_field.path)

        setattr(adoption, picture_field, None)
        adoption.save()
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'status': 'not_found'})

@require_POST
@login_required

# Function: delete_file (originally at line 9126)
def delete_file(request, adoption_id, field_name):
    """刪除送養證明文件"""
    adoption = get_object_or_404(AdoptionPet, id=adoption_id, owner=request.user)

    if field_name in ["health_certificate", "vaccine_certificate"]:
        file_field = getattr(adoption, field_name, None)
        if file_field:
            file_field.delete(save=False)
            setattr(adoption, field_name, None)
            adoption.save()
            return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)

@login_required
@require_owner
def edit_adoption(request, pk):
    """編輯送養貼文"""
    adoption = get_object_or_404(AdoptionPet, pk=pk)
    other_pet_names = list(
        AdoptionPet.objects.filter(owner=request.user).values_list("name", flat=True)
    )
    vaccine_records = []
    if adoption.original_pet:
        vaccine_records = adoption.original_pet.vaccine_records.all()

    if adoption.owner != request.user:
        return redirect('adoption_petDetail', adoption_id=pk)

    picture_fields = [
        {'index': i, 'name': f'adopt_picture{i}', 'image': getattr(adoption, f'adopt_picture{i}')}
        for i in range(1, 5)
    ]

    if request.method == 'POST':
        form = AdoptionForm(request.POST, request.FILES, instance=adoption, owner=request.user)

        if form.is_valid():
            # 處理圖片刪除
            old_adoption = AdoptionPet.objects.get(pk=pk)
            for field in ['adopt_picture1', 'adopt_picture2', 'adopt_picture3', 'adopt_picture4']:
                new_image = form.cleaned_data.get(field)
                old_image = getattr(old_adoption, field)
                if new_image and old_image and old_image.name != new_image.name:
                    old_path = os.path.join(settings.MEDIA_ROOT, old_image.name)
                    if os.path.exists(old_path):
                        os.remove(old_path)

            # 儲存表單資料
            adoption = form.save(commit=False)
            adoption.breed = form.cleaned_data['breed']
            adoption.vaccine = form.cleaned_data['vaccine']
            adoption.save()

            messages.success(request, "編輯成功")
            return redirect('adoption_petDetail', adoption_id=pk)
        else:
            return render(request, 'adoptions/edit_adoption.html', {
                'adoption_form': form,
                'adoption': adoption,
                'other_pet_names': other_pet_names,
                'feature_choices': FEATURE_CHOICES,
                'physical_choices': PHYSICAL_CHOICES,
                'adoptcondition_choices': ADOPTCONDITION_CHOICES,
                'dog_choices': json.dumps(DOG_CHOICES, ensure_ascii=False),
                'cat_choices': json.dumps(CAT_CHOICES, ensure_ascii=False),
                'dogvaccine_choices': json.dumps(DOGVACCINE_CHOICES, ensure_ascii=False),
                'catvaccine_choices': json.dumps(CATVACCINE_CHOICES, ensure_ascii=False),
                'picture_fields': picture_fields,
                'vaccine_records': vaccine_records,
            })
    else:
        # GET 初始值
        feature_data = safe_json_loads(adoption.feature)
        physical_data = safe_json_loads(adoption.physical_condition)
        adoptcondition_data = safe_json_loads(adoption.adoption_condition)

        # 獲取使用者的寵物資料用於「從我的寵物帶入」功能（排除已刊登且仍在發布的寵物）
        my_pets = []
        if request.user.is_authenticated:
            # 排除已刊登且仍在發布的寵物，但允許當前正在編輯的寵物
            published_pet_ids = AdoptionPet.objects.filter(
                owner=request.user,
                is_publish=True,
                original_pet__isnull=False
            ).exclude(id=adoption.id).values_list('original_pet_id', flat=True)

            pets = Pet.objects.filter(owner=request.user).exclude(
                id__in=published_pet_ids
            )
            for pet in pets:
                pet_data = {
                    'id': pet.id,
                    'name': pet.name,
                    'species': pet.species,
                    'breed': pet.breed,
                    'gender': pet.gender,
                    'birth_date': pet.birth_date.strftime('%Y-%m-%d') if pet.birth_date else '',
                    'chip': pet.chip or '',
                    'weight': float(pet.weight) if pet.weight else '',
                    'sterilization_status': pet.sterilization_status,
                    'feature': pet.feature or '',
                    'picture': pet.picture.url if pet.picture else '',
                    'vaccine_records': list(pet.vaccine_records.values_list('name', flat=True))
                }
                my_pets.append(pet_data)

        form = AdoptionForm(instance=adoption)
        return render(request, 'adoptions/edit_adoption.html', {
            'adoption_form': form,
            'adoption': adoption,
            'picture_fields': picture_fields,
            'feature_choices': FEATURE_CHOICES,
            'physical_choices': PHYSICAL_CHOICES,
            'other_pet_names': other_pet_names,
            'adoptcondition_choices': ADOPTCONDITION_CHOICES,
            'dog_choices': json.dumps(DOG_CHOICES, ensure_ascii=False),
            'cat_choices': json.dumps(CAT_CHOICES, ensure_ascii=False),
            'dogvaccine_choices': json.dumps(DOGVACCINE_CHOICES, ensure_ascii=False),
            'catvaccine_choices': json.dumps(CATVACCINE_CHOICES, ensure_ascii=False),
            'vaccine_records': vaccine_records,
            'my_pets': my_pets,  # 添加寵物資料
            # 新增解析後的資料供前端使用
            'feature_data': json.dumps(feature_data, ensure_ascii=False) if feature_data else 'null',
            'physical_data': json.dumps(physical_data, ensure_ascii=False) if physical_data else 'null',
            'adoptcondition_data': json.dumps(adoptcondition_data, ensure_ascii=False) if adoptcondition_data else 'null',
            'initial_species': adoption.species,
            'initial_breed': adoption.breed,
            'initial_vaccine': adoption.vaccine,
        })

@login_required

# Function: edit_doctor (originally at line 5342)
def edit_doctor(request, doctor_id=None):
    if doctor_id:
        doctor = get_object_or_404(VetDoctor, id=doctor_id)
        user = doctor.user
    else:
        doctor = None
        user = None

    if request.method == 'POST':
        if doctor:
            # 更新現有醫師
            user.first_name = request.POST.get('first_name')
            user.email = request.POST.get('email')
            user.save()
            
            # 更新電話號碼到 Profile
            doctor.phone_number = request.POST.get('phone_number', '')
            
            # 更新專業資料
            doctor.vet_license_number = request.POST.get('vet_license_number', '')
            
            # 處理專科領域邏輯（多選支援）
            # 直接使用前端處理好的專科領域字符串（用「、」分隔）
            doctor.specialization = request.POST.get('specialization', '').strip()
                
            doctor.years_of_experience = int(request.POST.get('years_of_experience', 0))
            doctor.bio = request.POST.get('bio', '')
            
            # 更新權限
            doctor.is_active = 'is_active' in request.POST
            doctor.is_active_veterinarian = 'is_active_veterinarian' in request.POST
            doctor.is_clinic_admin = 'is_clinic_admin' in request.POST
            
            doctor.save()
        
        return redirect('manage_doctors')
    
    context = {
        'doctor': doctor,
    }
    return render(request, 'clinic/edit_doctor.html', context)
@login_required
@require_clinic_management
@require_http_methods(["POST"])

# Function: get_clinic_business_status (originally at line 6508)
def get_clinic_business_status(request):
    """獲取診所當前營業狀態"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 使用你現有模型的管理器方法
        is_open = ClinicBusinessHoursRecord.objects.is_open_now(clinic)
        
        now = timezone.now()
        current_weekday = now.weekday()
        current_time = now.time()
        current_date = now.date()
        
        # 獲取今天的營業時間
        today_hours = ClinicBusinessHoursRecord.objects.active_hours(
            clinic, current_date
        ).order_by('start_time')
        
        current_period = None
        next_period = None
        
        # 檢查當前營業時段
        for period in today_hours:
            if period.start_time <= current_time <= period.end_time:
                current_period = period
                break
        
        # 如果不在營業時間，找下一個營業時段
        if not current_period:
            # 先找今天剩餘的時段
            for period in today_hours:
                if current_time < period.start_time:
                    next_period = period
                    break
            
            # 如果今天沒有，找未來幾天的第一個時段
            if not next_period:
                for day_offset in range(1, 8):
                    check_day = (current_weekday + day_offset) % 7
                    future_date = current_date + timedelta(days=day_offset)
                    future_hours = ClinicBusinessHoursRecord.objects.active_hours(
                        clinic, future_date
                    ).order_by('start_time').first()
                    
                    if future_hours:
                        next_period = future_hours
                        break
        
        status_data = {
            'is_open': is_open,
            'current_time': current_time.strftime('%H:%M'),
            'current_weekday': current_weekday,
            'current_period': None,
            'next_period': None
        }
        
        if current_period:
            status_data['current_period'] = {
                'start_time': current_period.start_time.strftime('%H:%M'),
                'end_time': current_period.end_time.strftime('%H:%M'),
                'notes': current_period.notes or ''
            }
        
        if next_period:
            status_data['next_period'] = {
                'weekday': next_period.weekday,
                'start_time': next_period.start_time.strftime('%H:%M'),
                'end_time': next_period.end_time.strftime('%H:%M'),
                'notes': next_period.notes or ''
            }
        
        return JsonResponse({
            'success': True,
            'status': status_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'獲取營業狀態失敗: {str(e)}'
            })

# ============ 診所業務管理 API ============

@login_required
@ensure_csrf_cookie
def get_notification_count(request):
    """獲取未讀通知數量"""
    try:
        count = 0

        # 首先計算資料庫中的未讀通知
        try:
            db_unread_count = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
            count += db_unread_count
        except Exception as e:
            print(f"資料庫通知計數錯誤: {e}")

        # 檢查是否有今日預約（獸醫師）
        if hasattr(request.user, 'vet_profile'):
            vet_profile = request.user.vet_profile
            today = timezone.now().date()

            count += VetAppointment.objects.filter(
                slot__doctor=vet_profile,
                slot__date=today,
                status='pending'
            ).count()

        # 檢查健康提醒（飼主）
        if hasattr(request.user, 'profile'):
            pets = Pet.objects.filter(owner=request.user)
            for pet in pets:
                latest_vaccine = VaccineRecord.objects.filter(
                    pet=pet
                ).order_by('-date').first()

                if latest_vaccine:
                    days_since_vaccine = (timezone.now().date() - latest_vaccine.date).days
                    if days_since_vaccine > 365:
                        count += 1

        return JsonResponse({'count': count})
        
    except Exception as e:
        return JsonResponse({'count': 0, 'error': str(e)})

@login_required
def get_notifications_api(request):
    """獲取通知列表API"""
    try:
        user = request.user
        notifications = []

        # 首先獲取資料庫中的通知
        try:
            db_notifications = Notification.objects.filter(recipient=user).select_related(
                'sender', 'post', 'comment'
            ).order_by('-created_at')[:15]

            for notification in db_notifications:
                # 格式化時間
                time_diff = timezone.now() - notification.created_at
                if time_diff.days > 0:
                    time_str = f'{time_diff.days}天前'
                elif time_diff.seconds > 3600:
                    time_str = f'{time_diff.seconds // 3600}小時前'
                elif time_diff.seconds > 60:
                    time_str = f'{time_diff.seconds // 60}分鐘前'
                else:
                    time_str = '剛剛'

                notifications.append({
                    'id': notification.id,
                    'type': notification.notification_type,
                    'title': notification.title,
                    'message': notification.message,
                    'time': time_str,
                    'is_read': notification.is_read,
                    'sender': notification.sender.username if notification.sender else '系統',
                    'created_at': notification.created_at.isoformat(),
                    'url': '#'
                })
        except Exception as e:
            print(f"通知模型查詢錯誤: {e}")

        # 為獸醫師添加預約通知（作為補充）
        if hasattr(user, 'vet_profile'):
            try:
                vet_profile = user.vet_profile
                today = timezone.now().date()

                # 今日待處理預約
                pending_appointments = VetAppointment.objects.filter(
                    slot__doctor=vet_profile,
                    slot__date=today,
                    status='pending'
                ).select_related('pet', 'owner')

                for appointment in pending_appointments:
                    notifications.append({
                        'id': f'appointment_{appointment.id}',
                        'type': 'appointment',
                        'title': f'今日預約 - {appointment.pet.name}',
                        'message': f'飼主：{appointment.owner.get_full_name() or appointment.owner.username}',
                        'created_at': appointment.created_at.isoformat() if appointment.created_at else timezone.now().isoformat(),
                        'time': '今天',
                        'is_read': False,
                        'sender': '系統',
                        'url': f'/vet/appointments/'
                    })
            except Exception as e:
                print(f"獸醫預約查詢錯誤: {e}")

        # 為飼主添加健康提醒
        if hasattr(user, 'profile'):
            try:
                pets = Pet.objects.filter(owner=user)
                for pet in pets:
                    # 檢查疫苗提醒
                    try:
                        latest_vaccine = VaccineRecord.objects.filter(
                            pet=pet
                        ).order_by('-date').first()

                        if latest_vaccine:
                            next_due = latest_vaccine.date + timedelta(days=365)
                            days_until_due = (next_due - timezone.now().date()).days

                            if 0 <= days_until_due <= 30:
                                notifications.append({
                                    'id': f'vaccine_{pet.id}',
                                    'type': 'pet_health_reminder',
                                    'title': f'{pet.name} 疫苗提醒',
                                    'message': f'下次疫苗接種將於 {days_until_due} 天後到期',
                                    'created_at': timezone.now().isoformat(),
                                    'time': f'{days_until_due}天後',
                                    'is_read': False,
                                    'sender': '系統',
                                    'url': f'/pet_info/pet_list/'
                                })
                    except Exception:
                        pass

                    # 檢查驅蟲提醒
                    try:
                        latest_deworm = DewormRecord.objects.filter(
                            pet=pet
                        ).order_by('-date').first()

                        if latest_deworm:
                            next_due = latest_deworm.date + timedelta(days=90)
                            days_until_due = (next_due - timezone.now().date()).days

                            if 0 <= days_until_due <= 14:
                                notifications.append({
                                    'id': f'deworm_{pet.id}',
                                    'type': 'pet_health_reminder',
                                    'title': f'{pet.name} 驅蟲提醒',
                                    'message': f'下次驅蟲將於 {days_until_due} 天後到期',
                                    'created_at': timezone.now().isoformat(),
                                    'time': f'{days_until_due}天後',
                                    'is_read': False,
                                    'sender': '系統',
                                    'url': f'/pet_info/pet_list/'
                                })
                    except Exception:
                        pass
            except Exception as e:
                print(f"寵物健康查詢錯誤: {e}")

        # 按時間排序，最新的在前
        try:
            notifications.sort(key=lambda x: x['created_at'], reverse=True)
        except:
            # 如果排序失敗，保持原順序
            pass

        return JsonResponse({
            'success': True,
            'notifications': notifications[:20]  # 限制返回20條
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def mark_notification_read(request, notification_id):
    """標記單個通知為已讀"""
    if request.method == 'POST':
        try:
            # 查找並標記通知為已讀
            notification = Notification.objects.get(
                id=notification_id,
                recipient=request.user
            )
            notification.is_read = True
            notification.save()

            return JsonResponse({
                'success': True,
                'message': '通知已標記為已讀'
            })
        except Notification.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '通知不存在'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    return JsonResponse({'success': False, 'error': '方法不允許'}, status=405)

@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """標記所有通知為已讀"""
    try:
        # 標記用戶所有未讀通知為已讀
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)

        return JsonResponse({
            'success': True,
            'message': f'已標記 {updated_count} 個通知為已讀',
            'updated_count': updated_count
        })
    except Exception as e:
        # 如果通知模型還不存在，返回成功（向後相容）
        print(f"通知模型更新錯誤: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_owner
def my_adoption(request):
    """我的送養紀錄"""
    user = request.user
    filter_option = request.GET.get('filter', 'all')

    adoptions = AdoptionPet.objects.filter(owner=user).order_by('-posted_date')

    if filter_option == 'available':
        adoptions = adoptions.filter(is_adopted=False, is_publish=True)
    elif filter_option == 'adopted':
        adoptions = adoptions.filter(is_adopted=True)
    elif filter_option == 'unpublished':
        adoptions = adoptions.filter(is_publish=False)

    # 使用安全的JSON處理函數
    for adoption in adoptions:
        adoption.parsed_feature = safe_json_loads(adoption.feature)
        adoption.parsed_physical = safe_json_loads(adoption.physical_condition)
        adoption.parsed_adoption_condition = safe_json_loads(adoption.adoption_condition)

    return render(request, 'adoptions/my_adoption.html', {
        'adoptions': adoptions,
        'filter_option': filter_option,
    })

@login_required

# Function: notification_page (originally at line 6648)
def notification_page(request):
    """通知頁面"""
    try:
        # 這裡可以從資料庫獲取通知
        # 目前先使用假資料示例
        notifications = []
        
        # 如果是獸醫師，檢查今日預約
        if hasattr(request.user, 'vet_profile'):
            vet_profile = request.user.vet_profile
            today = timezone.now().date()
            
            today_appointments = VetAppointment.objects.filter(
                slot__doctor=vet_profile,
                slot__date=today,
                status='confirmed'
            ).count()
            
            if today_appointments > 0:
                notifications.append({
                    'id': 1,
                    'type': 'appointment',
                    'title': '今日預約提醒',
                    'message': f'您今天有 {today_appointments} 個預約',
                    'created_at': timezone.now(),
                    'is_read': False
                })
        
        # 如果是飼主，檢查寵物健康提醒
        if hasattr(request.user, 'profile'):
            pets = Pet.objects.filter(owner=request.user)
            for pet in pets:
                # 檢查疫苗到期
                latest_vaccine = VaccineRecord.objects.filter(
                    pet=pet
                ).order_by('-date').first()
                
                if latest_vaccine:
                    days_since_vaccine = (timezone.now().date() - latest_vaccine.date).days
                    if days_since_vaccine > 365:  # 一年未打疫苗
                        notifications.append({
                            'id': f'vaccine_{pet.id}',
                            'type': 'health',
                            'title': '疫苗提醒',
                            'message': f'{pet.name} 的疫苗可能需要更新',
                            'created_at': timezone.now(),
                            'is_read': False
                        })
        
        return render(request, 'pages/notifications.html', {
            'notifications': notifications
        })
        
    except Exception as e:
        messages.error(request, f'載入通知失敗:{str(e)}')
        return redirect('home')

@login_required

# Function: quick_set_business_hours (originally at line 6161)
def quick_set_business_hours(request):
    """快速設定營業時間"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '僅接受 POST 請求'})
    
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        data = json.loads(request.body)
        template = data.get('template')
        
        business_hours_templates = {
            'standard': {
                'name': '標準營業時間',
                'hours': {
                    0: {'is_open': True, 'open_time': '09:00', 'close_time': '17:00'},  # 週一
                    1: {'is_open': True, 'open_time': '09:00', 'close_time': '17:00'},  # 週二
                    2: {'is_open': True, 'open_time': '09:00', 'close_time': '17:00'},  # 週三
                    3: {'is_open': True, 'open_time': '09:00', 'close_time': '17:00'},  # 週四
                    4: {'is_open': True, 'open_time': '09:00', 'close_time': '17:00'},  # 週五
                    5: {'is_open': True, 'open_time': '09:00', 'close_time': '12:00'},  # 週六
                    6: {'is_open': False, 'open_time': None, 'close_time': None},      # 週日
                }
            },
            '24_7': {
                'name': '24小時營業',
                'hours': {i: {'is_open': True, 'open_time': '00:00', 'close_time': '23:59'} 
                         for i in range(7)}
            },
            'weekdays_only': {
                'name': '僅平日營業',
                'hours': {
                    **{i: {'is_open': True, 'open_time': '08:00', 'close_time': '18:00'} 
                       for i in range(5)},  # 週一到週五
                    **{i: {'is_open': False, 'open_time': None, 'close_time': None} 
                       for i in range(5, 7)}  # 週六週日
                }
            }
        }
        
        if template not in business_hours_templates:
            return JsonResponse({'status': 'error', 'message': '無效的模板'})
        
        template_data = business_hours_templates[template]
        
        with transaction.atomic():
            # 這裡需要根據您的 BusinessHours 模型調整
            # for weekday, hours in template_data['hours'].items():
            #     BusinessHours.objects.update_or_create(
            #         clinic=clinic,
            #         weekday=weekday,
            #         defaults=hours
            #     )
            pass
        
        return JsonResponse({
            'status': 'success',
            'message': f'已套用「{template_data["name"]}」模板',
            'business_hours': template_data['hours']
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ============ 營業時間管理 ============

@login_required
# Function: send_for_adoption (originally at line 8962)
def send_for_adoption(request, pet_id):
    """從'我的寵物' 送養"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)

    # 檢查是否已經在送養中
    exists = AdoptionPet.objects.filter(
        original_pet=pet,
        is_adopted=False,
        owner=request.user
    ).exists()

    if exists:
        messages.warning(request, '這隻寵物已經在送養名單中了。')
        return redirect('pet_list')
    
    # 建立新的送養資料（copy 寵物資料）
    adoption = AdoptionPet.objects.create(
        owner=request.user,
        species=pet.species,
        breed=pet.breed,
        name=pet.name,
        sterilization_status=pet.sterilization_status,
        chip=pet.chip,
        birth_date=pet.birth_date,
        gender=pet.gender,
        weight=pet.weight,
        feature=pet.feature,
        adopt_picture1=pet.picture,
        posted_date=timezone.now(),
        is_adopted=False,
        original_pet=pet,
    )
    
    pet.is_adoption_only = True
    pet.save()
    messages.success(request, f'「{pet.name}」已加入送養名單。')
    return redirect('edit_adoption', pk=adoption.id)

@login_required

# Function: simple_clinic_setup (originally at line 6067)
def simple_clinic_setup(request):
    """單一醫師模式快速設定"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 檢查是否已有多位醫師
        doctor_count = VetDoctor.objects.filter(clinic=clinic, is_active=True).count()
        
        if doctor_count > 1:
            messages.warning(request, '您的診所已有多位醫師，建議使用完整的排班管理功能')
            return redirect('schedule_dashboard')
        
        # 獲取唯一的醫師（通常是管理者自己）
        try:
            doctor = VetDoctor.objects.get(clinic=clinic, is_active=True)
        except VetDoctor.DoesNotExist:
            messages.error(request, '找不到有效的醫師資料')
            return redirect('clinic_dashboard')
        except VetDoctor.MultipleObjectsReturned:
            messages.warning(request, '發現多位醫師，請使用完整的排班管理功能')
            return redirect('schedule_dashboard')
        
        if request.method == 'POST':
            try:
                # 獲取表單數據
                working_days = request.POST.getlist('working_days')
                start_time = request.POST.get('start_time')
                end_time = request.POST.get('end_time')
                break_start = request.POST.get('break_start')
                break_end = request.POST.get('break_end')
                appointment_duration = int(request.POST.get('appointment_duration', 30))
                
                with transaction.atomic():
                    # 刪除現有排班
                    VetSchedule.objects.filter(doctor=doctor).delete()
                    
                    # 創建新排班
                    for day_str in working_days:
                        day = int(day_str)
                        
                        # 上午時段
                        if break_start and break_end:
                            VetSchedule.objects.create(
                                doctor=doctor,
                                weekday=day,
                                start_time=datetime.strptime(start_time, '%H:%M').time(),
                                end_time=datetime.strptime(break_start, '%H:%M').time(),
                                appointment_duration=appointment_duration,
                                is_active=True
                            )
                            
                            # 下午時段
                            VetSchedule.objects.create(
                                doctor=doctor,
                                weekday=day,
                                start_time=datetime.strptime(break_end, '%H:%M').time(),
                                end_time=datetime.strptime(end_time, '%H:%M').time(),
                                appointment_duration=appointment_duration,
                                is_active=True
                            )
                        else:
                            # 整天時段
                            VetSchedule.objects.create(
                                doctor=doctor,
                                weekday=day,
                                start_time=datetime.strptime(start_time, '%H:%M').time(),
                                end_time=datetime.strptime(end_time, '%H:%M').time(),
                                appointment_duration=appointment_duration,
                                is_active=True
                            )
                
                messages.success(request, '快速設定完成！')
                return redirect('schedule_dashboard')
                
            except Exception as e:
                messages.error(request, f'設定失敗:{str(e)}')
        
        # 獲取現有排班作為預設值
        existing_schedules = VetSchedule.objects.filter(doctor=doctor, is_active=True)
        
        return render(request, 'clinic/simple_clinic_setup.html', {
            'clinic': clinic,
            'doctor': doctor,
            'existing_schedules': existing_schedules,
            'weekdays': WEEKDAYS
        })
        
    except Exception as e:
        messages.error(request, f'載入快速設定失敗:{str(e)}')
        return redirect('clinic_dashboard')

@login_required
@require_clinic_management

# Function: toggle_doctor_status (originally at line 5913)
def toggle_doctor_status(request, doctor_id):
    """切換醫師狀態 - 支援AJAX和普通請求"""
    
    # 只接受POST請求
    if request.method != 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': '僅支援POST請求'})
        return redirect('manage_doctors')
    
    try:
        vet_profile = request.user.vet_profile
        doctor = get_object_or_404(
            VetDoctor,
            id=doctor_id,
            clinic=vet_profile.clinic
        )
        
        # 不能停用自己
        if doctor.user == request.user:
            error_msg = '不能停用自己的帳號'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
            return redirect('manage_doctors')
        
        # 切換狀態
        old_status = doctor.is_active
        doctor.is_active = not doctor.is_active
        doctor.save()
        
        status_text = '啟用' if doctor.is_active else '停用'
        success_msg = f'醫師「{doctor.user.get_full_name() or doctor.user.username}」已{status_text}'
        
        # 檢查是否為AJAX請求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': success_msg,
                'doctor': {
                    'id': doctor.id,
                    'name': doctor.user.get_full_name() or doctor.user.username,
                    'is_active': doctor.is_active,
                    'status_text': status_text
                }
            })
        else:
            # 普通表單提交
            messages.success(request, success_msg)
            return redirect('manage_doctors')
        
    except Exception as e:
        error_msg = f'切換醫師狀態失敗:{str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': error_msg})
        else:
            messages.error(request, error_msg)
            return redirect('manage_doctors')



# ============ 錯誤處理 view 函數 ============

@login_required
# Function: toggle_status (originally at line 9085)
def toggle_status(request, pk):
    """切換送養狀態"""
    adoption = get_object_or_404(AdoptionPet, pk=pk, owner=request.user)
    if request.method == 'POST':
        action = request.POST.get('action')
        print(f"DEBUG: Toggle status - ID: {pk}, Method: {request.method}")
        print(f"DEBUG: POST data: {dict(request.POST)}")
        print(f"DEBUG: Action: '{action}', Before - Adopted: {adoption.is_adopted}, Published: {adoption.is_publish}")

        if action == 'adopted':
            adoption.is_adopted = not adoption.is_adopted
            print(f"DEBUG: Changed is_adopted to: {adoption.is_adopted}")
        elif action == 'publish':
            adoption.is_publish = not adoption.is_publish
            print(f"DEBUG: Changed is_publish to: {adoption.is_publish}")

        adoption.save()
        print(f"DEBUG: After save - Adopted: {adoption.is_adopted}, Published: {adoption.is_publish}")

        # 根據來源頁面決定重定向
        referer = request.META.get('HTTP_REFERER', '')
        if 'my' in referer:
            return redirect('my_adoption')
        else:
            return redirect('adoption_petDetail', adoption_id=pk)

    return redirect('adoption_petDetail', adoption_id=pk)

@login_required
def adoption_transfer_request(request, pk):
    """創建送養轉交請求"""
    adoption = get_object_or_404(AdoptionPet, pk=pk, owner=request.user)

    if not adoption.is_adopted:
        messages.error(request, '只有已完成領養的寵物才能轉交')
        return redirect('adoption_petDetail', adoption_id=pk)

    if request.method == 'POST':
        to_email = request.POST.get('to_email')
        to_phone = request.POST.get('to_phone')
        transfer_note = request.POST.get('transfer_note', '')

        if not to_email or not to_phone:
            messages.error(request, '請填寫完整的聯絡資訊')
            return redirect('adoption_petDetail', adoption_id=pk)

        # 檢查是否已經有待處理的轉交請求
        existing_request = AdoptionTransferRequest.objects.filter(
            adoption=adoption,
            status='pending'
        ).first()

        if existing_request:
            messages.error(request, '此寵物已有待處理的轉交請求')
            return redirect('adoption_petDetail', adoption_id=pk)

        # 驗證目標用戶是否存在於系統中
        try:
            to_user = User.objects.get(email=to_email)
        except User.DoesNotExist:
            messages.error(request, f'Email地址 {to_email} 不存在於系統中，請確認對方已註冊帳號')
            return redirect('adoption_petDetail', adoption_id=pk)

        # 檢查不能轉交給自己
        if to_user == request.user:
            messages.error(request, '不能將寵物轉交給自己')
            return redirect('adoption_petDetail', adoption_id=pk)

        # 創建轉交請求
        transfer_request = AdoptionTransferRequest.objects.create(
            adoption=adoption,
            from_owner=request.user,
            to_email=to_email,
            to_phone=to_phone,
            to_user=to_user,
            transfer_note=transfer_note
        )

        # 發送通知給目標用戶
        Notification.objects.create(
            recipient=to_user,
            sender=request.user,
            title="收到領養轉交請求",
            message=f"{request.user.username} 想將 {adoption.name} 轉交給您",
            notification_type="adoption_transfer_request"
        )

        messages.success(request, f'轉交請求已發送到 {to_email}')
        return redirect('adoption_petDetail', adoption_id=pk)

    return redirect('adoption_petDetail', adoption_id=pk)

@login_required
def my_adoption_transfers(request):
    """查看我的領養轉交請求"""
    # 我收到的轉交請求
    received_requests = AdoptionTransferRequest.objects.filter(to_user=request.user, status='pending')
    # 我發送的轉交請求
    sent_requests = AdoptionTransferRequest.objects.filter(from_owner=request.user)

    context = {
        'received_requests': received_requests,
        'sent_requests': sent_requests,
    }
    return render(request, 'adoptions/my_adoption_transfers.html', context)

@login_required
def adoption_transfer_confirm(request, transfer_id):
    """確認領養轉交請求"""
    transfer = get_object_or_404(AdoptionTransferRequest, id=transfer_id, to_user=request.user, status='pending')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'accept':
            transfer.status = 'accepted'
            transfer.save()

            # 轉移領養權
            adoption = transfer.adoption
            adoption.owner = request.user
            # 轉交後設為已送養且不刊登（新飼主收養，不是繼續送養）
            adoption.is_adopted = True
            adoption.is_publish = False
            adoption.save()

            # 同時轉移對應的寵物記錄
            try:
                corresponding_pet = None

                # 方法1：優先使用 original_pet 直接關聯（最可靠）
                if adoption.original_pet and adoption.original_pet.owner == transfer.from_owner:
                    corresponding_pet = adoption.original_pet
                    print(f"使用直接關聯找到寵物記錄: {corresponding_pet.name} (ID: {corresponding_pet.id})")

                # 方法2：如果沒有直接關聯，使用晶片號碼匹配（第二可靠）
                if not corresponding_pet and adoption.chip:
                    corresponding_pet = Pet.objects.filter(
                        chip=adoption.chip,
                        owner=transfer.from_owner
                    ).first()
                    if corresponding_pet:
                        print(f"使用晶片號碼找到寵物記錄: {corresponding_pet.name} (晶片: {adoption.chip})")

                # 方法3：如果前兩個方法都失敗，嘗試精確匹配
                if not corresponding_pet:
                    # 建立物種對應表（處理中英文物種名稱不一致問題）
                    species_mapping = {
                        'dog': '狗',
                        'cat': '貓',
                        '狗': 'dog',
                        '貓': 'cat'
                    }

                    # 精確匹配
                    corresponding_pet = Pet.objects.filter(
                        name=adoption.name,
                        species=adoption.species,
                        breed=adoption.breed,
                        owner=transfer.from_owner
                    ).first()

                    # 物種名稱轉換後匹配
                    if not corresponding_pet:
                        mapped_species = species_mapping.get(adoption.species)
                        if mapped_species:
                            corresponding_pet = Pet.objects.filter(
                                name=adoption.name,
                                species=mapped_species,
                                breed=adoption.breed,
                                owner=transfer.from_owner
                            ).first()

                # 方法4：最後手段 - 只用名字匹配（如果只有一個匹配結果）
                if not corresponding_pet:
                    potential_pets = Pet.objects.filter(
                        name=adoption.name,
                        owner=transfer.from_owner
                    )
                    if potential_pets.count() == 1:
                        corresponding_pet = potential_pets.first()
                        print(f"警告：使用名字進行寵物匹配: {corresponding_pet.name}")

                # 執行轉移
                if corresponding_pet:
                    corresponding_pet.owner = request.user
                    corresponding_pet.save()
                    print(f"✅ 成功轉移寵物記錄: {corresponding_pet.name} (ID: {corresponding_pet.id}) 到 {request.user.username}")

                    # 更新 adoption 的 original_pet 關聯，確保一致性
                    if adoption.original_pet != corresponding_pet:
                        adoption.original_pet = corresponding_pet
                        adoption.save()

                else:
                    print(f"❌ 未找到對應的寵物記錄: {adoption.name}")
                    print(f"   物種: {adoption.species}, 品種: {adoption.breed}, 晶片: {adoption.chip}")
                    # 列出原飼主的所有寵物以便除錯
                    owner_pets = Pet.objects.filter(owner=transfer.from_owner)
                    print("   原飼主的所有寵物:")
                    for pet in owner_pets:
                        print(f"     - {pet.name} (物種: {pet.species}, 品種: {pet.breed}, 晶片: {pet.chip})")

            except Exception as e:
                print(f"❌ 轉移寵物記錄時發生錯誤: {e}")
                import traceback
                print(traceback.format_exc())

            # 通知原飼主轉交已被接受
            Notification.objects.create(
                recipient=transfer.from_owner,
                sender=request.user,
                title="領養轉交已被接受",
                message=f"{request.user.username} 已接受您的 {adoption.name} 轉交請求",
                notification_type="adoption_transfer_accepted"
            )

            messages.success(request, f"您已成功接受 {adoption.name} 的領養轉交！")
            return redirect('my_adoption_transfers')

        elif action == 'reject':
            transfer.status = 'rejected'
            transfer.save()

            # 通知原飼主轉交已被拒絕
            Notification.objects.create(
                recipient=transfer.from_owner,
                sender=request.user,
                title="領養轉交已被拒絕",
                message=f"{request.user.username} 拒絕了您的 {transfer.adoption.name} 轉交請求",
                notification_type="adoption_transfer_rejected"
            )

            messages.info(request, "您已拒絕此轉交請求。")
            return redirect('my_adoption_transfers')

    context = {'transfer': transfer}
    return render(request, 'adoptions/adoption_transfer_confirm.html', context)

# Function: transfer_confirm (originally at line 9204)
def transfer_confirm(request, transfer_id):
    """確認轉讓請求"""
    transfer = get_object_or_404(TransferRequest, id=transfer_id, to_user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            transfer.status = 'accepted'
            transfer.save()
            
            # 轉移寵物所有權
            pet = transfer.pet
            pet.owner = request.user
            pet.save()
            
            messages.success(request, f"您已成功接受 {pet.name} 的轉讓！")
            
        elif action == 'reject':
            transfer.status = 'rejected'
            transfer.save()
            messages.info(request, "您已拒絕此轉讓請求。")
            
        else:
            messages.error(request, "請選擇有效操作。")

    return render(request, 'adoptions/transfer_confirm.html', {'transfer': transfer})

# ============ 排班複製功能 ============


# Function: update_doctor (originally at line 5386)
def update_doctor(request, doctor_id):
    """專門處理醫師資料更新的 POST 請求"""
    
    try:
        # 獲取當前用戶和目標醫師
        current_user = request.user
        vet_profile = current_user.vet_profile
        doctor = get_object_or_404(
            VetDoctor,
            id=doctor_id,
            clinic=vet_profile.clinic
        )
        
        # 權限檢查
        if not (vet_profile.is_clinic_admin or doctor.user == current_user):
            return JsonResponse({
                'success': False,
                'message': '您沒有權限編輯此醫師資料'
            })
        
        # 判斷是否為 AJAX 請求
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            # 處理 AJAX 更新請求
            form = EditDoctorForm(request.POST, instance=doctor, user=current_user)
            
            if form.is_valid():
                updated_doctor = form.save()
                
                return JsonResponse({
                    'success': True,
                    'message': '醫師資料更新成功',
                    'data': {
                        'name': updated_doctor.user.get_full_name(),
                        'email': updated_doctor.user.email,
                        'is_active': updated_doctor.is_active,
                        'is_admin': updated_doctor.is_clinic_admin,
                    }
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': '請檢查並修正表單中的錯誤',
                    'errors': form.errors
                })
        else:
            # 非 AJAX 請求，重定向到編輯頁面
            return redirect('edit_doctor', doctor_id=doctor_id)
            
    except Exception as e:
        logger.error(f"更新醫師資料時發生錯誤: {str(e)}")
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': f'系統錯誤:{str(e)}'
            })
        else:
            messages.error(request, f'更新醫師資料失敗:{str(e)}')
            return redirect('manage_doctors')




# ============ Error Handlers ============
def custom_400(request, exception=None):
    """400 錯誤處理"""
    return render(request, 'errors/400.html', {
        'exception': str(exception) if exception else '請求格式錯誤'
    }, status=400)

def custom_403(request, exception=None):
    """403 權限錯誤處理"""
    return render(request, 'errors/403.html', {
        'exception': str(exception) if exception else '您沒有權限訪問此頁面'
    }, status=403)

def custom_404(request, exception=None):
    """404 頁面未找到錯誤處理"""
    return render(request, 'errors/404.html', {
        'exception': str(exception) if exception else '頁面不存在'
    }, status=404)

def custom_500(request):
    """500 伺服器錯誤處理"""
    return render(request, 'errors/500.html', {
        'request_path': getattr(request, 'path', '/')
    },status=500)

# 臨時檔案，用於添加到 views.py 的末尾
#===========📅 進階排班管理系統============#

@login_required
def schedule_dashboard(request):
    """排班管理總覽頁面"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        clinic = vet_doctor.clinic
        
        context = {
            'vet_doctor': vet_doctor,
            'clinic': clinic,
            'is_single_mode': clinic.clinic_mode == 'single',
            'is_team_mode': clinic.clinic_mode == 'multi',
            'can_manage_schedules': vet_doctor.is_clinic_admin,  # 簡化為管理員權限
            'is_admin': vet_doctor.is_clinic_admin,
        }
        
        # 取得當前週的排班資料（擴大範圍以包含更多排班）
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # 擴大查詢範圍：包含前後各2週的排班，確保能看到相關排班
        extended_start = week_start - timedelta(days=14)  # 前2週
        extended_end = week_end + timedelta(days=14)      # 後2週

        # 個人排班 - 包含所有相關狀態的排班（草稿、待審核、已核准、生效中）
        # 修復：正確處理 end_date 為 None 的情況（無限期排班）
        # 修復：包含所有狀態以確保獸醫師能看到診所管理員建立的排班
        # 修復：擴大時間範圍以顯示更多排班
        from django.db.models import Q
        personal_schedules = EnhancedVetSchedule.objects.filter(
            doctor=vet_doctor,
            start_date__lte=extended_end,
            status__in=['draft', 'pending', 'approved', 'active']  # 包含所有相關狀態
        ).filter(
            Q(end_date__gte=extended_start) | Q(end_date__isnull=True)
        ).order_by('start_date')
        
        context.update({
            'personal_schedules': personal_schedules,
            'week_start': week_start,
            'week_end': week_end,
        })
        
        # 總是提供all_doctors給模板使用（避免模板錯誤）
        all_doctors = VetDoctor.objects.filter(clinic=clinic, is_active=True)
        context['all_doctors'] = all_doctors
        
        # 團隊模式額外資料
        if clinic.clinic_mode == 'multi' and vet_doctor.is_clinic_admin:
            # 修復：正確處理 end_date 為 None 的情況（無限期排班）
            # 修復：包含所有狀態以確保管理員能看到所有排班
            # 修復：擴大時間範圍以顯示更多排班
            clinic_schedules = EnhancedVetSchedule.objects.filter(
                clinic=clinic,
                start_date__lte=extended_end,
                status__in=['draft', 'pending', 'approved', 'active']  # 包含所有相關狀態
            ).filter(
                Q(end_date__gte=extended_start) | Q(end_date__isnull=True)
            ).select_related('doctor').order_by('start_date')
            
            pending_requests = ScheduleChangeRequest.objects.filter(
                clinic=clinic,
                status='pending'
            ).select_related('requestor').order_by('-created_at')[:5]
            
            context.update({
                'clinic_schedules': clinic_schedules,
                'pending_requests': pending_requests,
            })
        
        return render(request, 'vet_pages/schedule_dashboard.html', context)
        
    except VetDoctor.DoesNotExist:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')

@login_required
def schedule_create(request):
    """建立新排班"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        clinic = vet_doctor.clinic

        # 檢查是否為團隊模式和管理員權限
        is_team_mode = clinic.clinic_mode == 'multi'
        is_admin = vet_doctor.is_clinic_admin

        # 獲取可管理的醫師列表
        if is_team_mode and is_admin:
            # 管理員可以為所有醫師創建排班
            available_doctors = VetDoctor.objects.filter(clinic=clinic, is_active=True)
        else:
            # 普通醫師只能為自己創建排班
            available_doctors = VetDoctor.objects.filter(id=vet_doctor.id)
        
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # 基本資訊
                    title = request.POST.get('title')
                    schedule_type = request.POST.get('schedule_type', 'regular')
                    start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
                    end_date_str = request.POST.get('end_date')
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

                    # 獲取目標醫師
                    target_doctor_id = request.POST.get('target_doctor')
                    if target_doctor_id:
                        # 驗證目標醫師是否在可管理範圍內
                        target_doctor = available_doctors.filter(id=target_doctor_id).first()
                        if not target_doctor:
                            messages.error(request, '無效的醫師選擇')
                            return redirect('schedule_create')
                    else:
                        target_doctor = vet_doctor  # 預設為當前用戶
                    
                    # 工作日設定
                    weekdays = []
                    for i in range(7):
                        if request.POST.get(f'weekday_{i}'):
                            weekdays.append(i)
                    
                    # 時段設定
                    daily_time_slots = {}
                    for weekday in weekdays:
                        slots = []
                        # 處理 JavaScript 傳送的 JSON 格式資料
                        time_slots_json = request.POST.get(f'time_slots_{weekday}')
                        if time_slots_json:
                            try:
                                slots = json.loads(time_slots_json)
                            except (json.JSONDecodeError, TypeError):
                                slots = []
                        else:
                            # 回退到舊格式 (如果有的話)
                            start_times = request.POST.getlist(f'start_time_{weekday}')
                            end_times = request.POST.getlist(f'end_time_{weekday}')
                            
                            for start_time, end_time in zip(start_times, end_times):
                                if start_time and end_time:
                                    slots.append({'start': start_time, 'end': end_time})
                        
                        daily_time_slots[str(weekday)] = slots
                    
                    # 建立排班
                    schedule = EnhancedVetSchedule.objects.create(
                        doctor=target_doctor,
                        clinic=clinic,
                        title=title,
                        schedule_type=schedule_type,
                        start_date=start_date,
                        end_date=end_date,
                        weekdays=weekdays,
                        daily_time_slots=daily_time_slots,
                        appointment_duration=int(request.POST.get('appointment_duration', 30)),
                        max_appointments_per_slot=int(request.POST.get('max_appointments_per_slot', 1)),
                        buffer_time=int(request.POST.get('buffer_time', 0)),
                        notes=request.POST.get('notes', ''),
                        status='draft',
                        created_by=request.user
                    )
                    
                    # 檢查衝突
                    conflicts = schedule.check_conflicts()
                    
                    if not conflicts:
                        schedule.status = 'active'
                        schedule.save()
                        messages.success(request, f'排班「{title}」已成功建立並啟用')
                    else:
                        messages.warning(request, f'排班「{title}」已建立，但發現 {len(conflicts)} 個衝突')
                    
                    # 檢查是否為AJAX請求
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'schedule_id': schedule.id,
                            'conflicts': conflicts,
                            'message': f'排班「{title}」已成功建立' + ('並啟用' if not conflicts else f'，但發現 {len(conflicts)} 個衝突')
                        })
                    else:
                        return redirect('schedule_detail', schedule_id=schedule.id)
                    
            except Exception as e:
                logger.error(f'建立排班失敗: {e}')
                messages.error(request, f'建立排班失敗：{str(e)}')
                
                # 檢查是否為AJAX請求
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'建立排班失敗：{str(e)}'
                    }, status=400)
                # 非AJAX請求繼續原有流程
        
        # 檢查是否有預選醫師
        preselected_doctor_id = request.GET.get('doctor')
        preselected_doctor = None
        if preselected_doctor_id:
            try:
                preselected_doctor = available_doctors.filter(id=preselected_doctor_id).first()
            except (ValueError, TypeError):
                pass

        context = {
            'vet_doctor': vet_doctor,
            'clinic': clinic,
            'schedule_types': EnhancedVetSchedule.SCHEDULE_TYPE_CHOICES,
            'weekdays': [(i, ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][i]) for i in range(7)],
            'available_doctors': available_doctors,
            'is_team_mode': is_team_mode,
            'is_admin': is_admin,
            'preselected_doctor': preselected_doctor,
        }
        
        return render(request, 'vet_pages/schedule_create.html', context)
        
    except VetDoctor.DoesNotExist:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')

@login_required
def schedule_edit(request, schedule_id):
    """編輯排班"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        schedule = get_object_or_404(EnhancedVetSchedule, id=schedule_id)
        
        # 權限檢查
        if not (schedule.doctor == vet_doctor or 
                (vet_doctor.is_clinic_admin and schedule.clinic == vet_doctor.clinic)):
            messages.error(request, '您沒有權限編輯此排班')
            return redirect('schedule_list')
        
        # 檢查是否可編輯（只有草稿和暫停狀態可編輯）
        if schedule.status not in ['draft', 'suspended']:
            messages.error(request, '只有草稿或暫停狀態的排班可以編輯')
            return redirect('schedule_detail', schedule_id=schedule_id)
        
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # 更新基本資訊
                    schedule.title = request.POST.get('title')
                    schedule.schedule_type = request.POST.get('schedule_type', 'regular')
                    schedule.start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
                    end_date_str = request.POST.get('end_date')
                    schedule.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                    
                    # 更新工作日設定
                    weekdays = []
                    for i in range(7):
                        if request.POST.get(f'weekday_{i}'):
                            weekdays.append(i)
                    schedule.weekdays = weekdays
                    
                    # 更新時段設定
                    daily_time_slots = {}
                    for weekday in weekdays:
                        slots = []
                        time_slots_json = request.POST.get(f'time_slots_{weekday}')
                        if time_slots_json:
                            try:
                                slots = json.loads(time_slots_json)
                            except (json.JSONDecodeError, TypeError):
                                slots = []
                        daily_time_slots[str(weekday)] = slots
                    schedule.daily_time_slots = daily_time_slots
                    
                    # 更新預約設定
                    schedule.appointment_duration = int(request.POST.get('appointment_duration', 30))
                    schedule.max_appointments_per_slot = int(request.POST.get('max_appointments_per_slot', 1))
                    schedule.buffer_time = int(request.POST.get('buffer_time', 0))
                    schedule.notes = request.POST.get('notes', '')
                    
                    schedule.save()
                    
                    # 檢查衝突
                    conflicts = schedule.check_conflicts()
                    
                    # 檢查是否是 AJAX 請求
                    is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                              request.POST.get('ajax') == '1')
                    if is_ajax:
                        # AJAX 請求，返回 JSON
                        return JsonResponse({
                            'success': True,
                            'message': f'排班已成功更新{f"，但發現 {len(conflicts)} 個衝突" if conflicts else ""}',
                            'conflicts': conflicts if conflicts else [],
                            'schedule_id': schedule.id
                        })
                    else:
                        # 普通請求，正常重定向
                        if conflicts:
                            messages.warning(request, f'排班已更新，但發現 {len(conflicts)} 個衝突，請檢查後再啟用')
                        else:
                            messages.success(request, '排班已成功更新')
                        
                        return redirect('schedule_detail', schedule_id=schedule.id)
                    
            except Exception as e:
                # 檢查是否是 AJAX 請求
                is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                          request.POST.get('ajax') == '1')
                if is_ajax:
                    # AJAX 請求，返回 JSON 錯誤
                    return JsonResponse({
                        'success': False,
                        'message': f'更新排班失敗：{str(e)}'
                    })
                else:
                    messages.error(request, f'更新排班失敗：{str(e)}')
        
        # GET 請求，顯示編輯表單
        context = {
            'schedule': schedule,
            'clinic': schedule.clinic,
            'vet_doctor': vet_doctor,
            'schedule_types': EnhancedVetSchedule.SCHEDULE_TYPE_CHOICES,
            'weekdays': [(i, ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][i]) for i in range(7)],
            'is_edit': True,
        }
        
        return render(request, 'vet_pages/schedule_edit.html', context)
        
    except VetDoctor.DoesNotExist:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')

@login_required
def schedule_detail(request, schedule_id):
    """排班詳細檢視"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        schedule = get_object_or_404(EnhancedVetSchedule, id=schedule_id)
        
        # 權限檢查
        if not (schedule.doctor == vet_doctor or 
                (vet_doctor.is_clinic_admin and schedule.clinic == vet_doctor.clinic)):
            messages.error(request, '您沒有權限查看此排班')
            return redirect('schedule_dashboard')
        
        # 生成範例排班日程
        today = date.today()
        sample_dates = []
        for i in range(7):
            check_date = today + timedelta(days=i)
            daily_schedule = schedule.generate_daily_schedule(check_date)
            if daily_schedule:
                sample_dates.append({
                    'date': check_date,
                    'weekday_name': ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][check_date.weekday()],
                    'schedule_items': daily_schedule
                })
        
        context = {
            'vet_doctor': vet_doctor,
            'schedule': schedule,
            'sample_dates': sample_dates,
            'can_edit': schedule.doctor == vet_doctor or vet_doctor.is_clinic_admin,
            'weekday_names': ['週一', '週二', '週三', '週四', '週五', '週六', '週日'],
        }
        
        return render(request, 'vet_pages/schedule_detail.html', context)
        
    except VetDoctor.DoesNotExist:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')

@login_required
def schedule_list(request):
    """排班列表頁面"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        clinic = vet_doctor.clinic
        
        schedules = EnhancedVetSchedule.objects.select_related('doctor__user', 'created_by')
        
        # 根據權限過濾
        if vet_doctor.is_clinic_admin:
            schedules = schedules.filter(clinic=clinic)
        else:
            schedules = schedules.filter(doctor=vet_doctor)
        
        # 篩選條件
        status_filter = request.GET.get('status')
        if status_filter:
            schedules = schedules.filter(status=status_filter)
        
        # 醫師過濾（用於從醫師管理頁面連過來）
        doctor_id_filter = request.GET.get('doctor_id')
        if doctor_id_filter and vet_doctor.is_clinic_admin:
            try:
                target_doctor = VetDoctor.objects.get(id=doctor_id_filter, clinic=clinic)
                schedules = schedules.filter(doctor=target_doctor)
            except VetDoctor.DoesNotExist:
                pass  # 忽略無效的醫師ID
        
        schedules = schedules.order_by('-created_at')
        
        # 分頁
        paginator = Paginator(schedules, 10)
        page_obj = paginator.get_page(request.GET.get('page'))
        
        context = {
            'vet_doctor': vet_doctor,
            'clinic': clinic,
            'page_obj': page_obj,
            'status_choices': EnhancedVetSchedule.STATUS_CHOICES,
            'selected_doctor_id': doctor_id_filter,
        }
        
        if vet_doctor.is_clinic_admin:
            context['doctors'] = VetDoctor.objects.filter(clinic=clinic, is_active=True)
            if doctor_id_filter:
                try:
                    context['selected_doctor'] = VetDoctor.objects.get(id=doctor_id_filter, clinic=clinic)
                except VetDoctor.DoesNotExist:
                    pass
        
        return render(request, 'vet_pages/schedule_list.html', context)
        
    except VetDoctor.DoesNotExist:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')

@login_required
@require_http_methods(["POST"])
def schedule_action(request, schedule_id, action):
    """排班操作"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        schedule = get_object_or_404(EnhancedVetSchedule, id=schedule_id)
        
        # 權限檢查
        can_modify = (schedule.doctor == vet_doctor or 
                     (vet_doctor.is_clinic_admin and schedule.clinic == vet_doctor.clinic))
        
        if not can_modify:
            return JsonResponse({'success': False, 'message': '您沒有權限操作此排班'})
        
        if action == 'activate':
            conflicts = schedule.check_conflicts()
            if conflicts:
                return JsonResponse({
                    'success': False, 
                    'message': f'無法啟用，發現 {len(conflicts)} 個衝突',
                    'conflicts': conflicts
                })
            
            schedule.status = 'active'
            schedule.save()
            return JsonResponse({'success': True, 'message': '排班已啟用'})
            
        elif action == 'suspend':
            schedule.status = 'suspended'
            schedule.save()
            return JsonResponse({'success': True, 'message': '排班已暫停'})
            
        elif action == 'delete':
            if schedule.status == 'active':
                return JsonResponse({'success': False, 'message': '無法刪除啟用中的排班，請先暫停'})
            
            schedule_title = schedule.title
            schedule.delete()
            return JsonResponse({'success': True, 'message': f'排班「{schedule_title}」已刪除'})
        
        else:
            return JsonResponse({'success': False, 'message': '不支援的操作'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def weekly_calendar(request):
    """週檢視排班日曆"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        clinic = vet_doctor.clinic
        
        # 取得週範圍
        week_str = request.GET.get('week')
        if week_str:
            week_start = datetime.strptime(week_str, '%Y-%m-%d').date()
        else:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        # 取得排班資料
        schedules = EnhancedVetSchedule.objects.filter(
            clinic=clinic,
            status='active',
            start_date__lte=week_end,
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=week_start)
        )

        # 生成週日期列表並加載排班資料
        week_dates = []
        
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            weekday = current_date.weekday()
            
            # 找到當天的排班
            daily_schedules = []
            for schedule in schedules:
                # 檢查工作日和日期範圍
                if weekday in schedule.weekdays:
                    # 檢查當前日期是否在排班有效期內
                    if (current_date >= schedule.start_date and 
                        (schedule.end_date is None or current_date <= schedule.end_date)):
                        
                        daily_slots = schedule.daily_time_slots.get(str(weekday), [])
                        for slot in daily_slots:
                            try:
                                daily_schedules.append({
                                    'schedule': schedule,
                                    'start_time': datetime.strptime(slot['start'], '%H:%M').time(),
                                    'end_time': datetime.strptime(slot['end'], '%H:%M').time(),
                                    'schedule_type': schedule.get_schedule_type_display(),
                                    'doctor_name': schedule.doctor.user.get_full_name(),
                                    'doctor_id': schedule.doctor.id,
                                })
                            except (KeyError, ValueError):
                                continue

            # 按時間排序排班項目
            daily_schedules.sort(key=lambda x: x['start_time'])
            
            week_dates.append({
                'date': current_date,
                'weekday': i,
                'weekday_name': ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][i],
                'is_today': current_date == date.today(),
                'schedules': daily_schedules,
            })
        
        # 為醫師分配顏色
        doctor_colors = {}
        color_palette = [
            '#3b82f6',  # 藍色
            '#10b981',  # 綠色
            '#f59e0b',  # 橙色
            '#ef4444',  # 紅色
            '#8b5cf6',  # 紫色
            '#06b6d4',  # 青色
            '#84cc16',  # 萊姆綠
            '#f97316',  # 橙紅色
            '#6366f1',  # 靛青色
            '#ec4899',  # 粉色
        ]

        # 獲取所有相關醫師並分配顏色
        all_doctors = set()
        for date_info in week_dates:
            for schedule in date_info['schedules']:
                all_doctors.add(schedule['doctor_id'])

        for i, doctor_id in enumerate(sorted(all_doctors)):
            doctor_colors[doctor_id] = color_palette[i % len(color_palette)]

        context = {
            'vet_doctor': vet_doctor,
            'clinic': clinic,
            'week_start': week_start,
            'week_end': week_end,
            'week_dates': week_dates,
            'prev_week': week_start - timedelta(days=7),
            'next_week': week_start + timedelta(days=7),
            'is_team_mode': clinic.clinic_mode == 'multi',
            'doctor_colors': doctor_colors,
        }
        
        return render(request, 'vet_pages/weekly_calendar.html', context)
        
    except VetDoctor.DoesNotExist:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')

@login_required
def monthly_calendar(request):
    """月檢視排班日曆"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        clinic = vet_doctor.clinic
        
        # 獲取當前年月
        today = date.today()
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        
        # 確保年月範圍有效
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        
        # 獲取月份的第一天和最後一天
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        # 生成月曆
        import calendar
        cal = calendar.monthcalendar(year, month)
        
        # 獲取診所的醫師
        doctors = VetDoctor.objects.filter(clinic=clinic, is_active=True).select_related('user')
        
        # 取得排班資料
        schedules = EnhancedVetSchedule.objects.filter(
            clinic=clinic,
            status='active',
            start_date__lte=month_end,
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=month_start)
        )
        
        # 組織月份數據 - 載入實際排班資料
        schedule_data = {}
        for week_num, week in enumerate(cal):
            for day_num, day in enumerate(week):
                if day == 0:
                    continue
                day_date = date(year, month, day)
                weekday = day_date.weekday()
                
                # 找到當天的排班
                daily_schedules = []
                for schedule in schedules:
                    # 檢查當前日期是否在排班的開始和結束日期範圍內
                    if day_date < schedule.start_date:
                        continue
                    if schedule.end_date and day_date > schedule.end_date:
                        continue

                    if weekday in schedule.weekdays:
                        daily_slots = schedule.daily_time_slots.get(str(weekday), [])
                        for slot in daily_slots:
                            try:
                                daily_schedules.append({
                                    'schedule': schedule,
                                    'start_time': datetime.strptime(slot['start'], '%H:%M').time(),
                                    'end_time': datetime.strptime(slot['end'], '%H:%M').time(),
                                    'title': schedule.title,
                                    'doctor_name': schedule.doctor.user.get_full_name(),
                                    'doctor_id': schedule.doctor.id,
                                })
                            except (KeyError, ValueError):
                                continue

                # 按時間排序排班項目
                daily_schedules.sort(key=lambda x: x['start_time'])
                
                schedule_data[day] = {
                    'date': day_date,
                    'schedules': daily_schedules,
                    'is_today': day_date == today,
                    'weekday': day_num,
                    'weekday_name': ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][day_num],
                }
        
        # 計算前後月份
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        # 為每位醫師分配顏色
        color_palette = [
            '#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6',
            '#1abc9c', '#e67e22', '#34495e', '#95a5a6', '#d35400'
        ]
        doctor_colors = {}
        for i, doctor in enumerate(doctors):
            doctor_colors[doctor.id] = color_palette[i % len(color_palette)]

        context = {
            'clinic': clinic,
            'vet_doctor': vet_doctor,
            'doctors': doctors,
            'calendar': cal,
            'schedule_data': schedule_data,
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'month_start': month_start,
            'month_end': month_end,
            'prev_month': prev_month,
            'prev_year': prev_year,
            'next_month': next_month,
            'next_year': next_year,
            'is_team_mode': clinic.clinic_mode == 'multi',
            'doctor_colors': doctor_colors,
        }
        
        return render(request, 'vet_pages/monthly_calendar.html', context)
        
    except VetDoctor.DoesNotExist:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')
    except Exception as e:
        messages.error(request, f'載入月檢視失敗:{str(e)}')
        return redirect('schedule_dashboard')

@login_required
def change_request_list(request):
    """排班異動申請列表"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        clinic = vet_doctor.clinic
        
        if vet_doctor.is_clinic_admin:
            requests = ScheduleChangeRequest.objects.filter(clinic=clinic)
        else:
            requests = ScheduleChangeRequest.objects.filter(requestor=vet_doctor)
        
        requests = requests.select_related('requestor__user').order_by('-created_at')
        paginator = Paginator(requests, 10)
        page_obj = paginator.get_page(request.GET.get('page'))
        
        context = {
            'vet_doctor': vet_doctor,
            'page_obj': page_obj,
            'status_choices': ScheduleChangeRequest.STATUS_CHOICES,
            'type_choices': ScheduleChangeRequest.REQUEST_TYPE_CHOICES,
        }
        
        return render(request, 'vet_pages/change_request_list.html', context)
        
    except VetDoctor.DoesNotExist:
        messages.error(request, '您沒有獸醫師權限')
        return redirect('vet_home')

@login_required
@require_http_methods(["POST"])
def api_review_change_request(request, request_id):
    """API: 審核排班異動申請"""
    try:
        # 檢查用戶權限
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        if not vet_doctor.is_clinic_admin:
            return JsonResponse({'success': False, 'message': '權限不足'}, status=403)
        
        # 獲取異動申請
        change_request = get_object_or_404(ScheduleChangeRequest, id=request_id, clinic=vet_doctor.clinic)
        
        if change_request.status != 'pending':
            return JsonResponse({'success': False, 'message': '此申請已被審核'}, status=400)
        
        # 解析請求數據
        data = json.loads(request.body)
        status = data.get('status')
        notes = data.get('notes', '')
        
        if status not in ['approved', 'rejected']:
            return JsonResponse({'success': False, 'message': '無效的審核狀態'}, status=400)
        
        # 更新申請狀態
        change_request.status = status
        change_request.reviewed_by = request.user
        change_request.reviewed_at = timezone.now()
        change_request.review_notes = notes
        change_request.save()
        
        # 如果申請被核准，可以在這裡添加額外的邏輯
        # 例如更新相關的排班、發送通知等
        
        return JsonResponse({
            'success': True, 
            'message': f'申請已{"核准" if status == "approved" else "拒絕"}'
        })
        
    except ScheduleChangeRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': '找不到該申請'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '請求格式錯誤'}, status=400)
    except Exception as e:
        logger.error(f"審核異動申請錯誤: {e}")
        return JsonResponse({'success': False, 'message': '伺服器錯誤'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_check_schedule_conflicts(request):
    """API: 檢查新排班的衝突"""
    try:
        import json
        
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        data = json.loads(request.body)
        
        # 獲取表單數據
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        weekdays = data.get('weekdays', [])
        time_slots = data.get('time_slots', {})
        
        if not start_date or not weekdays:
            return JsonResponse({'error': '缺少必要參數'}, status=400)
        
        conflicts = []
        
        # 檢查每個工作日的時段衝突
        for weekday in weekdays:
            day_slots = time_slots.get(str(weekday), [])
            
            for slot in day_slots:
                start_time = slot.get('start')
                end_time = slot.get('end')
                
                if not start_time or not end_time:
                    continue
                
                # 檢查是否與現有排班衝突
                overlapping = EnhancedVetSchedule.objects.filter(
                    doctor=vet_doctor,
                    status__in=['approved', 'active'],
                    start_date__lte=end_date or start_date,
                    end_date__gte=start_date
                )
                
                for schedule in overlapping:
                    # 檢查週工作日重疊
                    if int(weekday) in schedule.weekdays:
                        conflicts.append({
                            'type': 'doctor_time_overlap',
                            'type_display': '時間衝突',
                            'schedule_id': schedule.id,
                            'schedule_title': schedule.title,
                            'weekday': weekday,
                            'time_slot': f'{start_time}-{end_time}',
                            'message': f'週{["一", "二", "三", "四", "五", "六", "日"][int(weekday)]} {start_time}-{end_time} 與排班「{schedule.title}」時間重疊'
                        })
        
        return JsonResponse({
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts,
            'checked_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"檢查排班衝突錯誤: {e}")
        return JsonResponse({'error': '檢查衝突時發生錯誤'}, status=500)

@login_required
def api_schedule_conflicts(request, schedule_id):
    """API: 取得排班衝突資訊"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        schedule = get_object_or_404(EnhancedVetSchedule, id=schedule_id)
        
        if not (schedule.doctor == vet_doctor or vet_doctor.is_clinic_admin):
            return JsonResponse({'error': '權限不足'}, status=403)
        
        conflicts = schedule.check_conflicts(save=False)
        
        return JsonResponse({
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts,
            'checked_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_schedule_stats(request):
    """排班統計 API"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        clinic = vet_doctor.clinic
        
        # 計算統計數據
        today = timezone.now().date()
        this_week_start = today - timedelta(days=today.weekday())
        this_week_end = this_week_start + timedelta(days=6)
        this_month_start = today.replace(day=1)
        
        # 本週排班數
        # 修復：正確處理 end_date 為 None 的情況（無限期排班）
        # 修復：包含所有相關狀態以確保獸醫師能看到診所管理員建立的排班
        from django.db.models import Q
        weekly_schedules = EnhancedVetSchedule.objects.filter(
            doctor=vet_doctor,
            start_date__lte=this_week_end,
            status__in=['draft', 'pending', 'approved', 'active']  # 包含所有相關狀態
        ).filter(
            Q(end_date__gte=this_week_start) | Q(end_date__isnull=True)  # 處理無限期排班
        ).count()
        
        # 本月總工時（估算）
        monthly_hours = weekly_schedules * 8 * 4  # 簡單估算
        
        # 待處理請求
        pending_requests = ScheduleChangeRequest.objects.filter(
            clinic=clinic,
            status='pending'
        ).count() if vet_doctor.is_clinic_admin else 0
        
        # 團隊總人數
        team_size = VetDoctor.objects.filter(clinic=clinic, is_active=True).count()
        
        return JsonResponse({
            'success': True,
            'stats': {
                'weekly_schedules': weekly_schedules,
                'monthly_hours': monthly_hours,
                'pending_requests': pending_requests,
                'team_size': team_size
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def api_dashboard_schedules(request):
    """排班儀表板資料 API"""
    try:
        vet_doctor = get_object_or_404(VetDoctor, user=request.user)
        clinic = vet_doctor.clinic
        
        # 獲取本週排班資料
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        # 修復：正確處理 end_date 為 None 的情況（無限期排班）
        # 修復：包含所有相關狀態以確保獸醫師能看到診所管理員建立的排班
        from django.db.models import Q
        schedules_queryset = EnhancedVetSchedule.objects.filter(
            clinic=clinic,
            start_date__lte=week_end,
            status__in=['draft', 'pending', 'approved', 'active']  # 包含所有相關狀態
        ).filter(
            Q(end_date__gte=week_start) | Q(end_date__isnull=True)  # 處理無限期排班
        ).select_related('doctor__user')
        
        # 如果不是管理員，只顯示自己的排班
        if not vet_doctor.is_clinic_admin:
            schedules_queryset = schedules_queryset.filter(doctor=vet_doctor)
        
        schedules = []
        for schedule in schedules_queryset:
            schedules.append({
                'id': schedule.id,
                'title': schedule.title,
                'doctor_name': schedule.doctor.user.get_full_name(),
                'doctor_id': schedule.doctor.id,
                'start_date': schedule.start_date.isoformat(),
                'end_date': schedule.end_date.isoformat() if schedule.end_date else None,
                'status': schedule.status,
                'weekdays': list(schedule.weekdays) if hasattr(schedule, 'weekdays') else []
            })
        
        return JsonResponse({
            'success': True,
            'schedules': schedules,
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@require_clinic_management
def api_doctor_time_slots(request):
    """診所管理員專用：獲取醫師在指定日期的可用時段"""
    try:
        doctor_id = request.GET.get('doctor_id')
        date_str = request.GET.get('date')
        
        if not doctor_id or not date_str:
            return JsonResponse({
                'success': False,
                'message': '缺少必要參數'
            })
        
        # 解析日期
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': '日期格式錯誤'
            })
        
        # 獲取醫師
        try:
            doctor = VetDoctor.objects.get(
                id=doctor_id,
                is_active=True,
                is_active_veterinarian=True  # 確保醫師具有獸醫師身份
            )
        except VetDoctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '醫師不存在或不具有獸醫師身份'
            })
        
        # 檢查醫師在該日期是否有排班
        weekday = appointment_date.weekday()  # Monday is 0, Sunday is 6
        clinic = doctor.clinic
        
        # 先檢查醫師排班（優先使用醫師排班時間）
        schedules = EnhancedVetSchedule.objects.filter(
            doctor=doctor,
            status='active',
            start_date__lte=appointment_date
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=appointment_date)
        )
        
        # 檢查該醫師在這天是否有排班
        doctor_available = False
        available_periods = []
        
        for schedule in schedules:
            # 檢查該醫師在這個星期幾是否有排班
            if weekday in schedule.weekdays:
                doctor_available = True
                
                # 獲取該星期幾的時段設定
                weekday_str = str(weekday)
                day_time_slots = schedule.daily_time_slots.get(weekday_str, [])
                
                for slot in day_time_slots:
                    if slot.get('start') and slot.get('end'):
                        available_periods.append({
                            'start': slot['start'],
                            'end': slot['end']
                        })
        
        # 如果醫師沒有排班，檢查診所營業時間
        if not doctor_available:
            business_hours = ClinicBusinessHoursRecord.objects.filter(
                clinic=clinic,
                weekday=weekday,
                status='open'
            )
            
            if not business_hours.exists():
                return JsonResponse({
                    'success': True,
                    'slots': [],
                    'message': '該醫師在此日期無排班且診所未營業',
                    'doctor_name': doctor.user.get_full_name(),
                    'date': date_str
                })
            else:
                # 使用診所營業時間
                for bh in business_hours:
                    if bh.start_time and bh.end_time:
                        available_periods.append({
                            'start': bh.start_time.strftime('%H:%M'),
                            'end': bh.end_time.strftime('%H:%M')
                        })
        
        # 確保有可用時段
        if not available_periods:
            return JsonResponse({
                'success': True,
                'slots': [],
                'message': '無可用時段',
                'doctor_name': doctor.user.get_full_name(),
                'date': date_str
            })
        
        # 生成可用時段
        slots = []
        for period in available_periods:
            try:
                start_time = datetime.strptime(period['start'], '%H:%M').time()
                end_time = datetime.strptime(period['end'], '%H:%M').time()
                
                # 生成30分鐘間隔的時段
                current_datetime = datetime.combine(appointment_date, start_time)
                end_datetime = datetime.combine(appointment_date, end_time)
                
                while current_datetime.time() < end_datetime.time():
                    time_str = current_datetime.strftime('%H:%M')
                    slots.append({
                        'time': time_str,
                        'start': time_str,
                        'available': True
                    })
                    current_datetime += timedelta(minutes=30)
                    
            except (ValueError, KeyError):
                continue
        
        # 獲取已預約的時段
        existing_appointments = VetAppointment.objects.filter(
            slot__doctor=doctor,
            slot__date=appointment_date,
            status__in=['confirmed', 'pending']
        ).values_list('slot__start_time', flat=True)
        
        # 獲取當前時間（用於過濾過去的時間）
        from django.utils import timezone
        now = timezone.now()
        current_time = now.time()
        is_today = appointment_date == now.date()
        
        # 處理每個時段的可用性
        processed_slots = []
        for slot in slots:
            slot_time = datetime.strptime(slot['time'], '%H:%M').time()
            
            # 檢查是否為過去的時間
            is_past = is_today and slot_time < current_time
            
            # 檢查是否已被預約
            is_booked = slot_time in existing_appointments
            
            # 決定時段狀態
            if is_past:
                status = 'past'
                available = False
                css_class = 'time-slot-past'
                title = '已過時間'
            elif is_booked:
                status = 'booked'
                available = False
                css_class = 'time-slot-booked'
                title = '已預約'
            else:
                status = 'available'
                available = True
                css_class = 'time-slot-available'
                title = '可預約'
            
            processed_slots.append({
                'time': slot['time'],
                'start': slot['time'],
                'available': available,
                'status': status,
                'css_class': css_class,
                'title': title
            })
        
        return JsonResponse({
            'success': True,
            'slots': processed_slots,
            'doctor_name': doctor.user.get_full_name(),
            'date': date_str
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'載入時段失敗: {str(e)}'
        })


#===========💊 政府動物用藥資料庫 API===============#

@require_http_methods(["GET"])
@login_required
def drug_search_api(request):
    """政府動物用藥資料庫搜索API - 直接串接政府開放資料"""
    try:
        # 獲取搜索參數
        query = request.GET.get('q', '').strip()
        if not query or len(query) < 2:
            return JsonResponse({
                'success': False,
                'message': '請輸入至少2個字符進行搜索',
                'results': []
            })

        # 直接從政府API搜索
        import requests
        import logging

        logger = logging.getLogger(__name__)

        # 政府開放資料API
        api_url = "https://data.moa.gov.tw/Service/OpenData/FromM/ADProData.aspx?$top=9999&$skip=0&UnitId=023"

        try:
            response = requests.get(api_url, timeout=60)  # 增加timeout
            response.raise_for_status()

            api_data = response.json()
        except requests.exceptions.Timeout:
            logger.error("API請求超時")
            return JsonResponse({
                'success': False,
                'message': 'API請求超時，請稍後再試',
                'results': []
            })
        except Exception as e:
            logger.error(f"API請求失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'API連接失敗: {str(e)}',
                'results': []
            })

        # 搜索匹配的藥品
        results = []
        query_lower = query.lower()

        for item in api_data:
            # 使用欄位位置索引來提取資料
            values = list(item.values())

            license_number = str(values[0]) if len(values) > 0 and values[0] else ''
            chinese_name = str(values[1]) if len(values) > 1 and values[1] else ''
            english_name = str(values[2]) if len(values) > 2 and values[2] else ''
            manufacturer = str(values[3]) if len(values) > 3 and values[3] else ''
            applicant = str(values[4]) if len(values) > 4 and values[4] else ''
            dosage_form = str(values[7]) if len(values) > 7 and values[7] else ''
            packaging = str(values[8]) if len(values) > 8 and values[8] else ''
            indications = str(values[9]) if len(values) > 9 and values[9] else ''
            ingredients = str(values[10]) if len(values) > 10 and values[10] else ''

            # 搜索條件：中文名、英文名、成分、適應症、許可證字號
            searchable_text = f"{chinese_name} {english_name} {ingredients} {indications} {license_number}".lower()

            if query_lower in searchable_text:
                # 從適應症中提取適用動物
                target_animals = _extract_target_animals_from_indications(indications)

                results.append({
                    'license_number': license_number,
                    'chinese_name': chinese_name,
                    'english_name': english_name,
                    'manufacturer': manufacturer,
                    'applicant': applicant,
                    'dosage_form': dosage_form,
                    'packaging': packaging,
                    'indications': indications,
                    'active_ingredients': ingredients,
                    'target_animals': target_animals
                })

                # 限制返回結果數量
                if len(results) >= 20:
                    break

        return JsonResponse({
            'success': True,
            'message': f'找到 {len(results)} 筆相關藥物',
            'results': results,
            'query': query
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'搜索失敗: {str(e)}',
            'results': []
        })


def _extract_target_animals_from_indications(indications):
    """從效能(適應症)欄位中提取適用動物資訊"""
    if not indications:
        return ""

    import re

    # 常見動物名稱
    animals = ['豬', '牛', '羊', '馬', '犬', '貓', '雞', '鴨', '鵝', '兔', '魚', '蝦']

    # 尋找冒號前的動物名稱模式
    colon_match = re.match(r'^([^：:]+)[：:]', indications)
    if colon_match:
        prefix = colon_match.group(1)
        # 檢查前綴是否包含動物名稱
        found_animals = []
        for animal in animals:
            if animal in prefix:
                found_animals.append(animal)

        if found_animals:
            return '、'.join(found_animals)

    # 如果沒有找到標準格式，搜索整個文本中的動物名稱
    found_animals = []
    for animal in animals:
        if animal in indications:
            found_animals.append(animal)

    return '、'.join(found_animals) if found_animals else ""


# ============ 醫療記錄 API ============

@login_required
@require_http_methods(["GET"])
def api_medical_record_detail(request, record_id):
    """API: 獲取醫療記錄詳情"""
    try:
        # 獲取醫療記錄
        medical_record = get_object_or_404(
            MedicalRecord.objects.select_related(
                'pet', 'attending_vet__user'
            ),
            id=record_id
        )

        # 權限檢查：確保只有寵物飼主或相關獸醫師才能查看
        if (medical_record.pet.owner != request.user and
            not (hasattr(request.user, 'vet_profile') and
                 request.user.vet_profile == medical_record.attending_vet)):
            return JsonResponse({
                'success': False,
                'message': '權限不足'
            }, status=403)

        # 合併治療內容和治療計畫
        treatment_content = medical_record.treatment or ''
        treatment_plan_content = getattr(medical_record, 'treatment_plan', '') or ''

        # 如果兩個都有內容，組合它們；否則使用有內容的那個
        if treatment_content and treatment_plan_content:
            combined_treatment = f"{treatment_content}\n\n{treatment_plan_content}"
        else:
            combined_treatment = treatment_content or treatment_plan_content

        # 組裝回應資料
        record_data = {
            'id': medical_record.id,
            'pet_name': medical_record.pet.name,
            'visit_date': medical_record.visit_date.strftime('%Y年%m月%d日'),
            'attending_vet': medical_record.attending_vet.user.get_full_name() if medical_record.attending_vet else None,
            'clinic_location': medical_record.clinic_location,
            'diagnosis': medical_record.diagnosis,
            'treatment': combined_treatment,
            'notes': medical_record.notes,
            'medical_details': medical_record.medical_details,  # 使用 @property
            'created_at': medical_record.created_at.strftime('%Y-%m-%d %H:%M')
        }

        return JsonResponse({
            'success': True,
            'record': record_data
        })

    except Exception as e:
        print(f"API 醫療記錄詳情錯誤: {e}")
        return JsonResponse({
            'success': False,
            'message': '獲取醫療記錄失敗'
        }, status=500)


# ============ 登入後重導向處理 ============
def login_redirect(request):
    """登入後根據用戶類型重導向到適當頁面"""
    if not request.user.is_authenticated:
        return redirect('account_login')

    try:
        user = request.user

        # 檢查是否為後台管理員（超級用戶）
        if user.is_superuser or user.is_staff:
            return redirect('/')  # 後台管理員到首頁 http://127.0.0.1:8000/

        # 檢查是否有 VetDoctor 資料
        if hasattr(user, 'vet_profile') and user.vet_profile:
            vet_doctor = user.vet_profile

            # 診所管理員 -> 診所管理
            if vet_doctor.is_clinic_admin:
                return redirect('clinic_dashboard')

            # 獸醫師 -> 獸醫工作台
            elif vet_doctor.is_veterinarian:
                return redirect('vet_home')

            # 有獸醫資料但角色不明確，根據驗證狀態決定
            elif vet_doctor.license_verified_with_moa:
                return redirect('vet_home')
            else:
                return redirect('clinic_dashboard')

        # 檢查是否有一般用戶 Profile
        elif hasattr(user, 'profile') and user.profile:
            profile = user.profile
            account_type = profile.account_type

            # 飼主 -> 我的毛孩
            if account_type == 'owner':
                return redirect('pet_list')

            # 診所管理員 -> 診所管理
            elif account_type == 'clinic_admin':
                return redirect('clinic_dashboard')

            # 獸醫師 -> 獸醫工作台
            elif account_type == 'veterinarian':
                return redirect('vet_home')

            # 其他帳號類型 -> 首頁
            else:
                return redirect('/')

        # 沒有任何Profile，引導完善資料
        else:
            # 檢查是否是來自Google社群註冊的新用戶
            if request.session.get('google_needs_profile'):
                # 保持session標記，讓 social_signup_extra 可以正確處理
                # session標記會在 social_signup_extra POST 處理後才清除
                return redirect('/accounts/social/signup/extra/')
            else:
                # 檢查是否是社交帳號登入但沒有完成Profile的用戶
                from allauth.socialaccount.models import SocialAccount
                social_accounts = SocialAccount.objects.filter(user=user)

                if social_accounts.exists():
                    # 這是社交帳號用戶但沒有Profile，重新設置標記並導向補充資料頁面
                    logger.info(f"Social account user {user.username} missing profile, redirecting to extra signup")
                    request.session['google_needs_profile'] = True
                    return redirect('/accounts/social/signup/extra/')
                else:
                    # 一般註冊用戶沒有Profile，導向一般編輯頁面
                    messages.info(request, '請完善您的個人資料')
                    return redirect('edit_profile')

    except Exception as e:
        # 發生錯誤時導向首頁
        messages.error(request, '登入過程發生錯誤，請重新登入')
        return redirect('/')

# ============ 帳號刪除功能 ============
@login_required
def delete_account_confirm(request):
    """刪除帳號確認頁面"""
    return render(request, 'account/delete_account_confirm.html')

@login_required
def delete_account(request):
    """刪除帳號處理"""
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_text = request.POST.get('confirm_text')

        # 驗證密碼（如果用戶有設定密碼）
        if request.user.has_usable_password():
            if not password:
                messages.error(request, '請輸入密碼以確認身分')
                return render(request, 'account/delete_account_confirm.html')

            if not request.user.check_password(password):
                messages.error(request, '密碼錯誤')
                return render(request, 'account/delete_account_confirm.html')

        # 驗證確認文字
        if confirm_text != '刪除我的帳號':
            messages.error(request, '請正確輸入確認文字')
            return render(request, 'account/delete_account_confirm.html')

        try:
            # 記錄用戶信息（用於日誌）
            username = request.user.username
            email = request.user.email

            # 刪除用戶帳號（這會級聯刪除相關資料）
            request.user.delete()

            # 成功訊息並重定向到首頁
            messages.success(request, f'帳號 {username} 已成功刪除。感謝您曾經使用我們的服務。')

            # 記錄到日誌
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"User account deleted: {username} ({email})")

            return redirect('home')

        except Exception as e:
            messages.error(request, f'刪除帳號時發生錯誤：{str(e)}')
            return render(request, 'account/delete_account_confirm.html')

    return redirect('delete_account_confirm')


# ==================== AI 客服功能 ====================




@require_GET
def ai_health_check(request):
    """檢查AI服務狀態"""
    try:
        # 檢查RAG服務健康狀態
        health_url = "http://127.0.0.1:8001/health"
        response = requests.get(health_url, timeout=5)

        if response.status_code == 200:
            health_data = response.json()

            # 檢查Ollama模型狀態
            ollama_url = "http://127.0.0.1:8001/ollama"
            try:
                ollama_response = requests.get(ollama_url, timeout=5)
                ollama_data = ollama_response.json() if ollama_response.status_code == 200 else {}
            except:
                ollama_data = {'error': 'Ollama服務無法連接'}

            return JsonResponse({
                'rag_service': health_data,
                'ollama_service': ollama_data
            })
        else:
            return JsonResponse({
                'error': f'RAG服務不可用，狀態碼：{response.status_code}',
                'suggestion': '請確認RAG服務已啟動：uvicorn rag_ollama_server:app --host 127.0.0.1 --port 8001 --reload'
            }, status=500)

    except requests.exceptions.ConnectionError:
        return JsonResponse({
            'error': '無法連接到RAG服務',
            'suggestion': '請先啟動RAG服務：\n1. 開啟命令列\n2. 進入rag目錄\n3. 執行：uvicorn rag_ollama_server:app --host 127.0.0.1 --port 8001 --reload',
            'requirements': {
                'ollama': '需要安裝Ollama並下載模型：ollama pull qwen2.5:3b-instruct',
                'vector_db': '向量資料庫已建立',
                'python_packages': '所需套件已安裝'
            }
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'無法連接到AI服務：{str(e)}'
        }, status=500)

