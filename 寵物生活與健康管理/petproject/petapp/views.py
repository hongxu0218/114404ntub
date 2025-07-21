# petapp/views.py 

from collections import defaultdict
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required

from .models import (
    Profile, Pet, VetClinic, VetDoctor, VetSchedule, VetAppointment, 
    AppointmentSlot, VaccineRecord, DewormRecord, Report, MedicalRecord,PetType
)
from .forms import (
    VetClinicRegistrationForm, VetDoctorForm, AppointmentBookingForm,
    VetScheduleForm, EditProfileForm, PetForm, EditVetDoctorForm,
    SocialSignupExtraForm, MedicalRecordForm, VaccineRecordForm, 
    DewormRecordForm, ReportForm, VetLicenseVerificationForm 
)

from allauth.account.views import SignupView
from allauth.socialaccount.views import SignupView as SocialSignupView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods ,require_GET
from datetime import date, datetime, timedelta, time
from django.core.mail import send_mail  # 匯入發信功能
import json
from django.db.models import Q ,Max, F
from django.core.exceptions import ValidationError
from django.db import transaction

from calendar import monthrange
import calendar
from django.utils.timezone import localtime
from .utils import get_temperature_data, get_weight_data
from dateutil.relativedelta import relativedelta
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from functools import wraps

# ============ 自定義裝飾器定義 ============

def require_clinic_management(view_func):
    """
    自定義裝飾器：要求用戶具有診所管理權限
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 檢查用戶是否已登入
        if not request.user.is_authenticated:
            messages.error(request, '請先登入')
            return redirect('account_login')
        
        try:
            # 檢查是否有 vet_profile
            vet_profile = request.user.vet_profile
            
            # 檢查是否為診所管理員或有管理權限
            if not vet_profile.is_clinic_admin and not vet_profile.can_manage_doctors:
                messages.error(request, '您沒有診所管理權限')
                return redirect('home')
            
            # 檢查是否有關聯的診所
            if not vet_profile.clinic:
                messages.error(request, '找不到與您關聯的診所')
                return redirect('clinic_registration')
            
            return view_func(request, *args, **kwargs)
            
        except AttributeError:
            # 沒有 vet_profile
            messages.error(request, '您不是診所成員')
            return redirect('home')
        except Exception as e:
            messages.error(request, f'權限檢查失敗：{str(e)}')
            return redirect('home')
    
    return _wrapped_view

def require_verified_vet(view_func):
    """
    自定義裝飾器：要求用戶是已驗證的獸醫師
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '請先登入')
            return redirect('account_login')
        
        try:
            vet_profile = request.user.vet_profile
            
            if not vet_profile.is_verified:
                messages.warning(request, '您的獸醫師執照尚未通過驗證')
                return redirect('verify_vet_license')
            
            return view_func(request, *args, **kwargs)
            
        except AttributeError:
            messages.error(request, '您不是獸醫師')
            return redirect('home')
    
    return _wrapped_view

def require_medical_license(view_func):
    """
    自定義裝飾器：要求用戶具有醫療記錄填寫權限（已驗證的獸醫師執照）
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '請先登入')
            return redirect('account_login')
        
        try:
            vet_profile = request.user.vet_profile
            
            # 檢查是否有填寫醫療記錄的權限
            if not vet_profile.can_write_medical_records:
                messages.error(request, '您沒有填寫醫療記錄的權限，需要通過獸醫師執照驗證')
                return redirect('verify_vet_license')
            
            return view_func(request, *args, **kwargs)
            
        except AttributeError:
            messages.error(request, '您不是獸醫師')
            return redirect('home')
    
    return _wrapped_view
    
def require_owner_or_vet(view_func):
    """
    自定義裝飾器：要求用戶是寵物飼主或獸醫師
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

def check_pet_ownership(view_func):
    """
    自定義裝飾器：檢查寵物所有權（用於保護寵物相關頁面）
    """
    @wraps(view_func)
    def _wrapped_view(request, pet_id=None, *args, **kwargs):
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
                            slot__doctor=vet_profile, 
                            pet=pet
                        ).exists():
                            messages.error(request, '您沒有權限查看此寵物資料')
                            return redirect('home')
                    except AttributeError:
                        messages.error(request, '您沒有權限查看此寵物資料')
                        return redirect('home')
                        
            except Pet.DoesNotExist:
                messages.error(request, '找不到指定的寵物')
                return redirect('pet_list')
        
        return view_func(request, pet_id, *args, **kwargs)
    
    return _wrapped_view


# ============ 共用函數定義 ============

def get_user_clinic_info(user):
    """
    獲取用戶的診所資訊 - 共用函數
    返回 (vet_profile, clinic) 或 (None, None)
    """
    vet_profile = None
    clinic = None
    
    try:
        # 方法1：嘗試透過 vet_profile 獲取
        try:
            vet_profile = user.vet_profile
            clinic = vet_profile.clinic
            print(f"✅ 透過 vet_profile 找到診所: {clinic.clinic_name}")
            return vet_profile, clinic
        except Exception:
            pass
        
        # 方法2：透過 VetDoctor 查詢
        try:
            vet_doctors = VetDoctor.objects.filter(user=user, is_active=True)
            if vet_doctors.exists():
                vet_profile = vet_doctors.first()
                clinic = vet_profile.clinic
                print(f"✅ 透過 VetDoctor 查詢找到診所: {clinic.clinic_name}")
                return vet_profile, clinic
        except Exception:
            pass
        
        # 方法3：透過email比對診所
        try:
            profile = user.profile
            if profile.account_type == 'clinic_admin':
                user_email = user.email
                clinics = VetClinic.objects.filter(clinic_email=user_email)
                if clinics.exists():
                    clinic = clinics.first()
                    print(f"✅ 透過email找到診所: {clinic.clinic_name}")
                    
                    # 重建 VetDoctor 關聯
                    vet_profile, created = VetDoctor.objects.get_or_create(
                        user=user,
                        clinic=clinic,
                        defaults={
                            'is_clinic_admin': True,
                            'can_manage_appointments': True,
                            'can_manage_doctors': True,
                            'is_active': True,
                            'is_verified': True
                        }
                    )
                    if created:
                        print(f"✅ 已重建 VetDoctor 關聯")
                    
                    return vet_profile, clinic
        except Exception as e:
            print(f"❌ 方法3失敗: {e}")
        
        # 方法4：如果用戶是第一個診所的創建者
        try:
            if VetClinic.objects.exists():
                clinic = VetClinic.objects.first()  # 取第一個診所
                print(f"⚠️ 使用第一個診所作為備用: {clinic.clinic_name}")
                
                # 建立關聯
                vet_profile, created = VetDoctor.objects.get_or_create(
                    user=user,
                    clinic=clinic,
                    defaults={
                        'is_clinic_admin': True,
                        'can_manage_appointments': True,
                        'can_manage_doctors': True,
                        'is_active': True,
                        'is_verified': True
                    }
                )
                return vet_profile, clinic
        except Exception as e:
            print(f"❌ 方法4失敗: {e}")
    
    except Exception as e:
        print(f"❌ get_user_clinic_info 整體錯誤: {e}")
    
    return None, None


def home(request):
    """首頁 - 區分用戶類型顯示不同內容"""
    context = {}
    
    if request.user.is_authenticated:
        try:
            # 🔧 修復：先檢查是否有 Profile
            profile = getattr(request.user, 'profile', None)
            
            if profile:
                context['user_type'] = profile.account_type
                print(f"🔍 用戶類型: {profile.account_type}")  # 除錯用
                
                if profile.account_type == 'owner':
                    # 飼主邏輯
                    pets = Pet.objects.filter(owner=request.user)[:3]
                    context['pets'] = pets
                    
                elif profile.account_type == 'clinic_admin':
                    # 🔧 修復：診所管理員邏輯
                    try:
                        vet_doctor = getattr(request.user, 'vet_profile', None)
                        
                        if vet_doctor and vet_doctor.clinic:
                            # 有診所，顯示管理介面
                            clinic = vet_doctor.clinic
                            context['clinic'] = clinic
                            context['is_clinic_admin'] = True
                            
                            # 今日預約數
                            today_appointments = VetAppointment.objects.filter(
                                slot__clinic=clinic,
                                slot__date=date.today(),
                                status='confirmed'
                            ).count()
                            context['today_appointments'] = today_appointments
                            
                            print(f"✅ 診所管理員 - 診所: {clinic.clinic_name}")  # 除錯用
                            
                        else:
                            # 🔧 沒有診所關聯，需要重新建立
                            print("⚠️ 診所管理員但沒有診所關聯")
                            context['need_clinic_setup'] = True
                            
                    except Exception as e:
                        print(f"❌ 獲取診所資訊錯誤: {e}")
                        context['need_clinic_setup'] = True
                        
            else:
                # 🔧 沒有 Profile，需要建立
                print("⚠️ 用戶沒有 Profile")
                context['need_profile_setup'] = True
                
        except Exception as e:
            print(f"❌ Home view 錯誤: {e}")
            context['error'] = str(e)
    
    return render(request, 'pages/index.html', context)

# ============ 診所註冊系統 ============

@csrf_protect
def clinic_registration(request):
    """診所註冊頁面"""
    
    if request.method == 'POST':
        print(f"📝 收到診所註冊POST請求")
        print(f"Content-Type: {request.content_type}")
        print(f"User: {request.user}")
        print(f"Is AJAX: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
        
        # 檢查是否為 AJAX 請求
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        form = VetClinicRegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    clinic = form.save()
                    print(f"🎉 診所註冊成功: {clinic}")
                    
                    success_message = f'診所「{clinic.clinic_name}」註冊成功！已通過農委會驗證。'
                    messages.success(request, success_message)
                    
                    # 發送歡迎信給管理員
                    try:
                        send_welcome_email(clinic)
                    except Exception as e:
                        print(f"發送歡迎信失敗: {e}")
                    
                    # 如果是 AJAX 請求，返回 JSON
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': success_message,
                            'redirect': f'/clinic/registration/success/{clinic.id}/'
                        })
                    
                    return redirect('clinic_registration_success', clinic_id=clinic.id)
                    
            except Exception as e:
                print(f"💥 註冊過程發生錯誤: {e}")
                import traceback
                traceback.print_exc()
                
                error_message = f'註冊過程發生錯誤：{str(e)}'
                messages.error(request, error_message)
                
                # 如果是 AJAX 請求，返回錯誤 JSON
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': error_message
                    }, status=400)
        else:
            print("❌ 表單驗證失敗")
            print(f"表單錯誤: {form.errors}")
            print(f"非欄位錯誤: {form.non_field_errors()}")
            
            # 如果是 AJAX 請求，返回表單錯誤
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'errors': dict(form.errors),
                    'non_field_errors': list(form.non_field_errors()),
                    'message': '表單驗證失敗，請檢查輸入資料'
                }, status=400)
    else:
        form = VetClinicRegistrationForm()
    
    return render(request, 'clinic/registration.html', {'form': form})

def clinic_registration_success(request, clinic_id):
    """診所註冊成功頁面"""
    clinic = get_object_or_404(VetClinic, id=clinic_id)
    return render(request, 'clinic/registration_success.html', {'clinic': clinic})

def send_welcome_email(clinic):
    """發送歡迎信給新診所"""
    admin_doctor = clinic.doctors.filter(is_clinic_admin=True).first()
    if admin_doctor:
        subject = "歡迎加入毛日好 Paw&Day 寵物醫療平台"
        message = f"""
親愛的 {clinic.clinic_name} 管理員 您好：

恭喜您成功註冊毛日好 Paw&Day 寵物醫療平台！

診所資訊：
🏥 診所名稱：{clinic.clinic_name}
📍 診所地址：{clinic.clinic_address}
📞 診所電話：{clinic.clinic_phone}
✅ 驗證狀態：已通過農委會驗證

接下來您可以：
1. 登入管理後台新增獸醫師
2. 設定醫師排班時間
3. 開始接受線上預約

管理員登入帳號：{admin_doctor.user.username}

如有任何問題，請聯繫客服：support@pawday.com

感謝您選擇毛日好 Paw&Day！

— 毛日好 Paw&Day 團隊
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [admin_doctor.user.email],
            fail_silently=True
        )



@login_required
def verify_vet_license(request):
    """獸醫師執照驗證"""
    try:
        vet_doctor = request.user.vet_profile
    except:
        messages.error(request, '您不是獸醫師')
        return redirect('home')
    
    if request.method == 'POST':
        form = VetLicenseVerificationForm(request.POST, instance=vet_doctor)
        if form.is_valid():
            vet_doctor = form.save(commit=False)
            
            # 🎯 執行農委會API驗證
            success, message = vet_doctor.verify_vet_license_with_moa()
            
            if success:
                messages.success(request, f'🎉 {message}')
                
                # 發送驗證成功通知給診所管理員
                send_vet_verification_notification(vet_doctor)
                
                return redirect('clinic_dashboard')
            else:
                messages.error(request, f'❌ 驗證失敗：{message}')
                form.add_error('vet_license_number', message)
    else:
        form = VetLicenseVerificationForm(instance=vet_doctor)
    
    context = {
        'form': form,
        'vet_doctor': vet_doctor,
        'is_verified': vet_doctor.license_verified_with_moa,
    }
    return render(request, 'clinic/verify_license.html', context)

def send_vet_verification_notification(vet_doctor):
    """發送獸醫師驗證成功通知"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    # 通知診所管理員
    clinic_admins = vet_doctor.clinic.doctors.filter(is_clinic_admin=True)
    
    for admin in clinic_admins:
        subject = f"【毛日好】獸醫師執照驗證成功 - {vet_doctor.user.get_full_name()}"
        message = f"""
親愛的 {vet_doctor.clinic.clinic_name} 管理員：

獸醫師「{vet_doctor.user.get_full_name()}」已成功通過農委會執照驗證！

📋 驗證資訊：
- 執照號碼：{vet_doctor.vet_license_number}
- 執照類別：{vet_doctor.moa_license_type}

該獸醫師現在可以：
✅ 設定看診排班
✅ 管理預約
✅ 填寫醫療記錄

— 毛日好 Paw&Day 系統
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [admin.user.email],
            fail_silently=True
        )

# ============ 3. 診所管理介面 ============
@login_required
def clinic_dashboard(request):
    """診所管理主控台"""
    try:
        # 🔧 修復：更robust的方式獲取診所資訊
        vet_profile = None
        clinic = None
        
        # 方法1：嘗試透過 vet_profile 獲取
        try:
            vet_profile = request.user.vet_profile
            clinic = vet_profile.clinic
            print(f"✅ 透過 vet_profile 找到診所: {clinic.clinic_name}")
        except Exception as e:
            print(f"❌ 無法透過 vet_profile 獲取診所: {e}")
        
        # 方法2：如果方法1失敗，嘗試透過 Profile 和診所關聯
        if not clinic:
            try:
                profile = request.user.profile
                if profile.account_type == 'clinic_admin':
                    # 查找與該用戶關聯的診所
                    vet_doctors = VetDoctor.objects.filter(user=request.user)
                    if vet_doctors.exists():
                        clinic = vet_doctors.first().clinic
                        vet_profile = vet_doctors.first()
                        print(f"✅ 透過查詢 VetDoctor 找到診所: {clinic.clinic_name}")
            except Exception as e:
                print(f"❌ 無法透過 Profile 獲取診所: {e}")
        
        # 方法3：如果還是沒有，查找用戶相關的所有診所
        if not clinic:
            try:
                # 查找該用戶創建的診所（基於email比對）
                user_email = request.user.email
                clinics = VetClinic.objects.filter(clinic_email=user_email)
                if clinics.exists():
                    clinic = clinics.first()
                    print(f"✅ 透過email比對找到診所: {clinic.clinic_name}")
                    
                    # 嘗試建立遺失的 VetDoctor 關聯
                    vet_profile, created = VetDoctor.objects.get_or_create(
                        user=request.user,
                        clinic=clinic,
                        defaults={
                            'is_clinic_admin': True,
                            'can_manage_appointments': True,
                            'can_manage_doctors': True,
                            'is_active': True,
                            'is_verified': True
                        }
                    )
                    if created:
                        print(f"✅ 已重建 VetDoctor 關聯")
            except Exception as e:
                print(f"❌ 無法透過email查找診所: {e}")
        
        # 如果還是找不到診所
        if not clinic:
            messages.error(request, '找不到與您關聯的診所資訊，請聯絡系統管理員')
            return redirect('clinic_registration')
        
        # 權限檢查
        if not vet_profile or not vet_profile.is_clinic_admin:
            messages.error(request, '您沒有診所管理權限')
            return redirect('home')
        
        # 統計資料
        context = {
            'clinic': clinic,
            'vet_profile': vet_profile,
            'doctors_count': clinic.doctors.filter(is_active=True).count(),
            'today_appointments': VetAppointment.objects.filter(
                slot__clinic=clinic,
                slot__date=date.today(),
                status='confirmed'
            ).count(),
            'pending_appointments': VetAppointment.objects.filter(
                slot__clinic=clinic,
                status='pending'
            ).count(),
            'total_appointments_this_month': VetAppointment.objects.filter(
                slot__clinic=clinic,
                slot__date__year=date.today().year,
                slot__date__month=date.today().month
            ).count(),
        }
        
        return render(request, 'clinic/dashboard.html', context)
        
    except Exception as e:
        print(f"❌ Clinic dashboard 錯誤: {e}")
        messages.error(request, f'發生錯誤：{str(e)}')
        return redirect('home')


@login_required
def manage_doctors(request):
    """管理診所醫師"""
    try:
        # 🔧 使用共用函數獲取診所資訊
        vet_profile, clinic = get_user_clinic_info(request.user)
        
        if not clinic:
            messages.error(request, '找不到與您關聯的診所資訊')
            return redirect('clinic_registration')
        
        if not vet_profile or not vet_profile.is_clinic_admin:
            messages.error(request, '您沒有管理醫師權限')
            return redirect('clinic_dashboard')
        
        doctors = clinic.doctors.all().order_by('user__first_name')
        
        context = {
            'clinic': clinic,
            'doctors': doctors,
            'vet_profile': vet_profile,
        }
        
        return render(request, 'clinic/manage_doctors.html', context)
        
    except Exception as e:
        print(f"❌ Manage doctors 錯誤: {e}")
        messages.error(request, f'發生錯誤：{str(e)}')
        return redirect('clinic_dashboard')
        
@login_required
def add_doctor(request):
    """新增獸醫師"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        if not vet_profile.can_manage_doctors:
            messages.error(request, '您沒有新增醫師權限')
            return redirect('manage_doctors')
        
        if request.method == 'POST':
            form = VetDoctorForm(request.POST, clinic=clinic)
            if form.is_valid():
                doctor = form.save()
                messages.success(request, f'獸醫師「{doctor.user.get_full_name()}」新增成功')
                return redirect('manage_doctors')
        else:
            form = VetDoctorForm(clinic=clinic)
        
        return render(request, 'clinic/add_doctor.html', {
            'form': form,
            'clinic': clinic
        })
        
    except:
        messages.error(request, '發生錯誤')
        return redirect('clinic_dashboard')

@login_required
def edit_doctor(request, doctor_id):
    """編輯獸醫師資料"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 權限檢查：只有診所管理員可以編輯醫師資料
        if not vet_profile.can_manage_doctors:
            messages.error(request, '您沒有編輯醫師資料的權限')
            return redirect('manage_doctors')
        
        # 取得要編輯的醫師（必須是同一診所）
        doctor = get_object_or_404(VetDoctor, id=doctor_id, clinic=clinic)
        
        if request.method == 'POST':
            # 建立編輯表單（需要新增這個表單）
            form = EditVetDoctorForm(request.POST, instance=doctor)
            if form.is_valid():
                updated_doctor = form.save()
                
                # 同時更新 User 資料
                user = updated_doctor.user
                user.first_name = form.cleaned_data.get('first_name', user.first_name)
                user.email = form.cleaned_data.get('email', user.email)
                user.save()
                
                # 更新 Profile 的電話
                if hasattr(user, 'profile'):
                    user.profile.phone_number = form.cleaned_data.get('phone_number', user.profile.phone_number)
                    user.profile.save()
                
                messages.success(request, f'獸醫師「{updated_doctor.user.get_full_name()}」資料已更新')
                return redirect('manage_doctors')
        else:
            # 初始化表單資料
            initial_data = {
                'first_name': doctor.user.first_name,
                'email': doctor.user.email,
                'phone_number': getattr(doctor.user.profile, 'phone_number', '') if hasattr(doctor.user, 'profile') else ''
            }
            form = EditVetDoctorForm(instance=doctor, initial=initial_data)
        
        return render(request, 'clinic/edit_doctor.html', {
            'form': form,
            'doctor': doctor,
            'clinic': clinic
        })
        
    except Exception as e:
        messages.error(request, f'發生錯誤：{str(e)}')
        return redirect('manage_doctors')

@login_required 
@require_POST
def toggle_doctor_status(request, doctor_id):
    """啟用/停用獸醫師"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 權限檢查：只有診所管理員可以啟用/停用醫師
        if not vet_profile.can_manage_doctors:
            messages.error(request, '您沒有管理醫師狀態的權限')
            return redirect('manage_doctors')
        
        # 取得要操作的醫師（必須是同一診所）
        doctor = get_object_or_404(VetDoctor, id=doctor_id, clinic=clinic)
        
        # 防止停用自己
        if doctor == vet_profile:
            messages.error(request, '您不能停用自己的帳號')
            return redirect('manage_doctors')
        
        # 切換狀態
        doctor.is_active = not doctor.is_active
        doctor.save()
        
        # 同時停用/啟用對應的 User 帳號
        doctor.user.is_active = doctor.is_active
        doctor.user.save()
        
        # 如果停用醫師，也要停用其排班
        if not doctor.is_active:
            VetSchedule.objects.filter(doctor=doctor).update(is_active=False)
            messages.warning(request, f'獸醫師「{doctor.user.get_full_name()}」已停用，相關排班也已停用')
        else:
            messages.success(request, f'獸醫師「{doctor.user.get_full_name()}」已啟用')
        
        return redirect('manage_doctors')
        
    except Exception as e:
        messages.error(request, f'操作失敗：{str(e)}')
        return redirect('manage_doctors')

# ============ 4. 排班管理系統 ============
@login_required
def manage_schedules(request, doctor_id=None):
    """管理醫師排班"""
    try:
        # 🔧 使用共用函數獲取診所資訊
        vet_profile, clinic = get_user_clinic_info(request.user)
        
        if not clinic:
            messages.error(request, '找不到與您關聯的診所資訊')
            return redirect('clinic_registration')
        
        # 決定要管理哪位醫師的排班
        if doctor_id:
            doctor = get_object_or_404(VetDoctor, id=doctor_id, clinic=clinic)
            # 檢查權限：只能管理自己或有管理權限
            if doctor != vet_profile and not vet_profile.can_manage_doctors:
                messages.error(request, '您沒有管理此醫師排班的權限')
                return redirect('clinic_dashboard')
        else:
            doctor = vet_profile
        
        schedules = VetSchedule.objects.filter(doctor=doctor, is_active=True).order_by('weekday', 'start_time')
        
        context = {
            'clinic': clinic,
            'doctor': doctor,
            'schedules': schedules,
            'can_edit': doctor == vet_profile or vet_profile.can_manage_doctors,
            'vet_profile': vet_profile,
        }
        
        return render(request, 'clinic/manage_schedules.html', context)
        
    except Exception as e:
        print(f"❌ Manage schedules 錯誤: {e}")
        messages.error(request, f'發生錯誤：{str(e)}')
        return redirect('clinic_dashboard')


@login_required
def add_schedule(request, doctor_id):
    """新增排班"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        doctor = get_object_or_404(VetDoctor, id=doctor_id, clinic=clinic)
        
        # 權限檢查
        if doctor != vet_profile and not vet_profile.can_manage_doctors:
            messages.error(request, '您沒有管理此醫師排班的權限')
            return redirect('manage_schedules', doctor_id=doctor_id)
        
        if request.method == 'POST':
            form = VetScheduleForm(request.POST, doctor=doctor)
            if form.is_valid():
                schedule = form.save(commit=False)
                schedule.doctor = doctor
                schedule.save()
                
                # 自動生成未來30天的預約時段
                generate_appointment_slots(doctor, schedule)
                
                messages.success(request, '排班新增成功，已自動生成預約時段')
                return redirect('manage_schedules', doctor_id=doctor_id)
        else:
            form = VetScheduleForm(doctor=doctor)
        
        return render(request, 'clinic/add_schedule.html', {
            'form': form,
            'doctor': doctor,
            'clinic': clinic
        })
        
    except Exception as e:
        messages.error(request, f'發生錯誤：{str(e)}')
        return redirect('manage_schedules', doctor_id=doctor_id)

@login_required
def edit_schedule(request, schedule_id):
    """編輯排班"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 取得排班記錄（必須是同一診所的醫師）
        schedule = get_object_or_404(VetSchedule, id=schedule_id, doctor__clinic=clinic)
        doctor = schedule.doctor
        
        # 權限檢查
        if doctor != vet_profile and not vet_profile.can_manage_doctors:
            messages.error(request, '您沒有編輯此排班的權限')
            return redirect('manage_schedules', doctor_id=doctor.id)
        
        if request.method == 'POST':
            form = VetScheduleForm(request.POST, instance=schedule, doctor=doctor)
            if form.is_valid():
                updated_schedule = form.save()
                
                # 重新生成受影響日期的預約時段
                regenerate_slots_for_schedule(doctor, updated_schedule)
                
                messages.success(request, '排班已更新，相關預約時段已重新生成')
                return redirect('manage_schedules', doctor_id=doctor.id)
        else:
            form = VetScheduleForm(instance=schedule, doctor=doctor)
        
        return render(request, 'clinic/edit_schedule.html', {
            'form': form,
            'schedule': schedule,
            'doctor': doctor,
            'clinic': clinic
        })
        
    except Exception as e:
        messages.error(request, f'發生錯誤：{str(e)}')
        return redirect('clinic_dashboard')


@login_required
@require_POST
def delete_schedule(request, schedule_id):
    """刪除排班"""
    try:
        vet_profile = request.user.vet_profile
        clinic = vet_profile.clinic
        
        # 取得排班記錄（必須是同一診所的醫師）
        schedule = get_object_or_404(VetSchedule, id=schedule_id, doctor__clinic=clinic)
        doctor = schedule.doctor
        
        # 權限檢查
        if doctor != vet_profile and not vet_profile.can_manage_doctors:
            messages.error(request, '您沒有刪除此排班的權限')
            return redirect('manage_schedules', doctor_id=doctor.id)
        
        # 檢查是否有未來的預約
        future_appointments = VetAppointment.objects.filter(
            slot__doctor=doctor,
            slot__date__gte=date.today(),
            status__in=['pending', 'confirmed']
        )
        
        if future_appointments.exists():
            # 如果有未來預約，只停用排班而不刪除
            schedule.is_active = False
            schedule.save()
            
            # 停用相關的未來預約時段
            future_slots = AppointmentSlot.objects.filter(
                doctor=doctor,
                date__gte=date.today(),
                source='schedule'
            )
            future_slots.update(is_available=False)
            
            messages.warning(request, '由於有未來的預約，排班已停用但未刪除。相關時段已標記為不可預約。')
        else:
            # 沒有未來預約，可以安全刪除
            weekday_name = schedule.get_weekday_display()
            time_range = f"{schedule.start_time}-{schedule.end_time}"
            
            schedule.delete()
            
            # 刪除相關的未來預約時段（沒有預約的）
            AppointmentSlot.objects.filter(
                doctor=doctor,
                date__gte=date.today(),
                source='schedule',
                current_bookings=0
            ).delete()
            
            messages.success(request, f'已刪除 {weekday_name} {time_range} 的排班')
        
        return redirect('manage_schedules', doctor_id=doctor.id)
        
    except Exception as e:
        messages.error(request, f'刪除失敗：{str(e)}')
        return redirect('clinic_dashboard')


def generate_appointment_slots(doctor, schedule, days_ahead=30):
    """根據排班自動生成預約時段"""
    try:
        start_date = date.today() + timedelta(days=1)  # 從明天開始
        end_date = start_date + timedelta(days=days_ahead)
        
        current_date = start_date
        slots_created = 0
        
        while current_date <= end_date:
            if current_date.weekday() == schedule.weekday:
                # 檢查是否已有這天的時段
                existing_slots = AppointmentSlot.objects.filter(
                    doctor=doctor,
                    date=current_date
                ).exists()
                
                if not existing_slots:
                    # 生成時段
                    current_time = datetime.combine(current_date, schedule.start_time)
                    end_time = datetime.combine(current_date, schedule.end_time)
                    
                    while current_time < end_time:
                        slot_end = current_time + timedelta(minutes=schedule.appointment_duration)
                        
                        if slot_end.time() <= schedule.end_time:
                            AppointmentSlot.objects.create(
                                clinic=doctor.clinic,
                                doctor=doctor,
                                date=current_date,
                                start_time=current_time.time(),
                                end_time=slot_end.time(),
                                max_bookings=schedule.max_appointments_per_slot,
                                reserved_for_online=schedule.max_appointments_per_slot,
                                source='schedule'
                            )
                            slots_created += 1
                        
                        current_time = slot_end
            
            current_date += timedelta(days=1)
        
        return slots_created
        
    except Exception as e:
        print(f"生成預約時段失敗：{e}")
        return 0

def regenerate_slots_for_schedule(doctor, schedule):
    """重新生成排班相關的預約時段"""
    # 找出受影響的日期範圍（未來30天）
    start_date = date.today() + timedelta(days=1)
    end_date = start_date + timedelta(days=30)
    
    # 刪除該醫師在指定星期的現有時段（未被預約的）
    AppointmentSlot.objects.filter(
        doctor=doctor,
        date__range=(start_date, end_date),
        date__week_day=schedule.weekday + 2,  # Django week_day: 1=Sunday, 2=Monday
        current_bookings=0,
        source='schedule'
    ).delete()
    
    # 重新生成時段
    generate_appointment_slots(doctor, schedule, 30)

@login_required  
def view_appointment_detail(request, appointment_id):
    """查看預約詳情"""
    try:
        vet_profile = request.user.vet_profile
        appointment = get_object_or_404(VetAppointment, 
                                       id=appointment_id, 
                                       slot__clinic=vet_profile.clinic)
    except:
        messages.error(request, '您沒有權限查看此預約')
        return redirect('clinic_dashboard')
    
    return render(request, 'clinic/appointment_detail.html', {
        'appointment': appointment
    })

@login_required
@require_POST  
def confirm_appointment(request, appointment_id):
    """確認預約"""
    try:
        vet_profile = request.user.vet_profile
        appointment = get_object_or_404(VetAppointment, 
                                       id=appointment_id, 
                                       slot__clinic=vet_profile.clinic)
        
        appointment.status = 'confirmed'
        appointment.save()
        
        messages.success(request, '預約已確認')
        
    except Exception as e:
        messages.error(request, f'確認失敗：{str(e)}')
    
    return redirect('clinic_appointments')

@login_required
@require_POST
def clinic_cancel_appointment(request, appointment_id):
    """診所取消預約"""
    try:
        vet_profile = request.user.vet_profile
        appointment = get_object_or_404(VetAppointment, 
                                       id=appointment_id, 
                                       slot__clinic=vet_profile.clinic)
        
        cancel_reason = request.POST.get('cancel_reason', '').strip()
        if not cancel_reason:
            messages.error(request, '請輸入取消原因')
            return redirect('clinic_appointments')
        
        # 發送通知給飼主
        send_cancellation_notification(appointment, cancel_reason)
        
        appointment.delete()
        messages.success(request, '預約已取消並已通知飼主')
        
    except Exception as e:
        messages.error(request, f'取消失敗：{str(e)}')
    
    return redirect('clinic_appointments')

def send_cancellation_notification(appointment, reason):
    """發送取消通知"""
    subject = f"【毛日好】預約取消通知 - {appointment.pet.name}"
    message = f"""
親愛的 {appointment.owner.get_full_name() or appointment.owner.username}：

您為寵物「{appointment.pet.name}」的預約已被取消：

📅 原預約時間：{appointment.slot.date} {appointment.slot.start_time}
🏥 診所：{appointment.slot.clinic.clinic_name}
📝 取消原因：{reason}

如需重新預約，請重新操作。造成不便敬請見諒。

— 毛日好 Paw&Day 系統
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [appointment.owner.email],
        fail_silently=True
    )

# ============  重新設計的預約系統 ============
@login_required
def create_appointment(request, pet_id):
    """建立預約 - 新流程"""
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    
    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST, pet=pet, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 檢查時段是否仍可預約
                    slot = form.cleaned_data['time_slot']
                    if not slot.can_book_online():
                        messages.error(request, '此時段已被預約，請重新選擇')
                        return render(request, 'appointments/create.html', {'form': form, 'pet': pet})
                    
                    # 建立預約
                    appointment = VetAppointment.objects.create(
                        pet=pet,
                        owner=request.user,
                        slot=slot,
                        reason=form.cleaned_data['reason'],
                        notes=form.cleaned_data['notes'],
                        contact_phone=form.cleaned_data['contact_phone'],
                        contact_email=request.user.email,
                        booking_type='online',
                        status='confirmed'
                    )
                    
                    # 發送通知
                    appointment.send_clinic_notification()
                    
                    messages.success(request, '預約成功！診所將會收到通知。')
                    return redirect('appointment_success', appointment_id=appointment.id)
                    
            except Exception as e:
                messages.error(request, f'預約失敗：{str(e)}')
    else:
        form = AppointmentBookingForm(pet=pet, user=request.user)
    
    return render(request, 'appointments/create.html', {'form': form, 'pet': pet})

def appointment_success(request, appointment_id):
    """預約成功頁面"""
    appointment = get_object_or_404(VetAppointment, id=appointment_id)
    
    # 權限檢查
    if request.user != appointment.owner:
        messages.error(request, '您沒有查看此預約的權限')
        return redirect('home')
    
    return render(request, 'appointments/success.html', {'appointment': appointment})

# ============  AJAX API - 動態載入選項 ============
@require_http_methods(["GET"])
def api_load_doctors(request):
    """AJAX: 根據診所載入醫師列表"""
    clinic_id = request.GET.get('clinic_id')
    
    if not clinic_id:
        return JsonResponse({'doctors': []})
    
    try:
        doctors = VetDoctor.objects.filter(
            clinic_id=clinic_id, 
            is_active=True
        ).order_by('user__first_name')
        
        doctors_data = [
            {
                'id': doctor.id,
                'name': doctor.user.get_full_name() or doctor.user.username,
                'specialization': doctor.specialization
            }
            for doctor in doctors
        ]
        
        return JsonResponse({'doctors': doctors_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def api_load_time_slots(request):
    """AJAX: 根據診所、醫師、日期載入可用時段"""
    clinic_id = request.GET.get('clinic_id')
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')
    
    if not clinic_id or not date_str:
        return JsonResponse({'slots': []})
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # 基本查詢
        slots_query = AppointmentSlot.objects.filter(
            clinic_id=clinic_id,
            date=target_date,
            is_available=True
        ).filter(current_bookings__lt=F('max_bookings'))
        
        # 如果指定醫師
        if doctor_id:
            slots_query = slots_query.filter(doctor_id=doctor_id)
        
        slots = slots_query.order_by('start_time')
        
        slots_data = [
            {
                'id': slot.id,
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'doctor_name': slot.doctor.user.get_full_name() or slot.doctor.user.username,
                'available_slots': slot.available_online_slots
            }
            for slot in slots if slot.available_online_slots > 0
        ]
        
        return JsonResponse({'slots': slots_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# ============ 預約管理 ============
@login_required
def clinic_appointments(request):
    """診所預約管理"""
    try:
        # 🔧 使用與 dashboard 相同的邏輯獲取診所
        vet_profile, clinic = get_user_clinic_info(request.user)
        
        if not clinic:
            messages.error(request, '找不到與您關聯的診所資訊')
            return redirect('clinic_registration')
        
        # 取得篩選參數
        date_filter = request.GET.get('date', 'today')
        status_filter = request.GET.get('status', 'all')
        doctor_filter = request.GET.get('doctor', 'all')
        
        # 基本查詢
        appointments = VetAppointment.objects.filter(slot__clinic=clinic)
        
        # 日期篩選
        if date_filter == 'today':
            appointments = appointments.filter(slot__date=date.today())
        elif date_filter == 'tomorrow':
            appointments = appointments.filter(slot__date=date.today() + timedelta(days=1))
        elif date_filter == 'week':
            week_start = date.today()
            week_end = week_start + timedelta(days=7)
            appointments = appointments.filter(slot__date__range=[week_start, week_end])
        
        # 狀態篩選
        if status_filter != 'all':
            appointments = appointments.filter(status=status_filter)
        
        # 醫師篩選
        if doctor_filter != 'all':
            appointments = appointments.filter(slot__doctor_id=doctor_filter)
        
        appointments = appointments.order_by('slot__date', 'slot__start_time')
        
        # 取得診所醫師列表用於篩選
        doctors = clinic.doctors.filter(is_active=True).order_by('user__first_name')
        
        context = {
            'clinic': clinic,
            'appointments': appointments,
            'doctors': doctors,
            'date_filter': date_filter,
            'status_filter': status_filter,
            'doctor_filter': doctor_filter,
        }
        
        return render(request, 'clinic/appointments.html', context)
        
    except Exception as e:
        print(f"❌ Clinic appointments 錯誤: {e}")
        messages.error(request, f'發生錯誤：{str(e)}')
        return redirect('clinic_dashboard')



@require_http_methods(["GET"])
def api_search_clinics(request):
    """AJAX: 搜尋診所 - 預約系統核心功能"""
    query = request.GET.get('q', '').strip()
    
    try:
        # 基本查詢：只顯示已驗證的診所
        clinics = VetClinic.objects.filter(is_verified=True)
        
        # 如果有搜尋關鍵字，進行篩選
        if query:
            clinics = clinics.filter(
                Q(clinic_name__icontains=query) |
                Q(clinic_address__icontains=query)
            )
        
        # 限制結果數量，提升效能
        clinics = clinics[:20]
        
        # 整理資料
        clinics_data = [
            {
                'id': clinic.id,
                'name': clinic.clinic_name,
                'address': clinic.clinic_address,
                'phone': clinic.clinic_phone,
            }
            for clinic in clinics
        ]
        
        return JsonResponse({'clinics': clinics_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# 使用者一般註冊流程覆寫
class CustomSignupView(SignupView):
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)  # 繼承原始邏輯

    def form_valid(self, form):
        response = super().form_valid(form)
        return redirect('/')  # 註冊成功導向首頁

# Google 社群註冊流程（含 session 取資料）
class CustomSocialSignupView(SocialSignupView):
    def form_valid(self, form):
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

        # 儲存獸醫證照檔案（若有）
        if vet_license_name and vet_license_content:
            from django.core.files.base import ContentFile
            profile.vet_license.save(
                vet_license_name,
                ContentFile(vet_license_content.encode('ISO-8859-1'))
            )

        return redirect('home')  # 註冊完成導向首頁

# Google 註冊補充資料表單

def social_signup_extra(request):
    if request.method == 'POST':
        form = SocialSignupExtraForm(request.POST, request.FILES)
        if form.is_valid():
            from allauth.socialaccount.models import SocialLogin
            if 'socialaccount_sociallogin' not in request.session:
                return HttpResponseBadRequest("找不到登入資訊，請重新操作")

            sociallogin = SocialLogin.deserialize(request.session.pop('socialaccount_sociallogin'))
            user = sociallogin.user
            user.username = form.cleaned_data['username']
            user.save()

            # 建立 Profile 資料
            profile = Profile.objects.create(
                user=user,
                account_type=form.cleaned_data['account_type'],
                phone_number=form.cleaned_data['phone_number'],
                vet_license_city=form.cleaned_data.get('vet_license_city'),
                vet_license=form.cleaned_data.get('vet_license'),
                clinic_name=form.cleaned_data.get('clinic_name'),
                clinic_address=form.cleaned_data.get('clinic_address'),
            )

            # 寄信通知管理員（若為獸醫帳號）
            if profile.account_type == 'vet':
                from django.core.mail import send_mail

                subject = "[系統通知] 有新獸醫帳號註冊待審核"
                message = f"""
您好，系統管理員：

有使用者完成 Google 註冊並選擇了「獸醫帳號」。

🔹 使用者名稱：{user.username}
🔹 Email：{user.email}

請盡快登入後台進行審核：
http://127.0.0.1:8000/admin/petapp/profile/

— 毛日好(Paw&Day) 系統
"""
                send_mail(subject, message, '毛日好(Paw&Day) <{}>'.format(settings.DEFAULT_FROM_EMAIL),
                          [settings.ADMIN_EMAIL], fail_silently=False)

            from allauth.account.utils import complete_signup
            from allauth.account import app_settings

            return complete_signup(
                request, user, app_settings.EMAIL_VERIFICATION,
                success_url=settings.LOGIN_REDIRECT_URL
            )
    else:
        form = SocialSignupExtraForm()

    return render(request, 'account/social_signup_extra.html', {'form': form})

# 註冊後選擇帳號類型
@login_required
def select_account_type(request):
    if request.method == 'POST':
        account_type = request.POST.get('account_type')
        profile = request.user.profile
        profile.account_type = account_type
        profile.save()
        return redirect('dashboard')
    return render(request, 'pages/select_account_type.html')

# 編輯個人檔案資料
@login_required
def edit_profile(request):
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=profile, user=user)
        if form.is_valid():
            new_username = form.cleaned_data.get('username')
            if new_username != user.username:
                from django.contrib.auth.models import User
                if User.objects.exclude(pk=user.pk).filter(username=new_username).exists():
                    form.add_error('username', '此使用者名稱已被使用')
                else:
                    form.save()
                    messages.success(request, '帳號資料已成功更新')
                    return redirect('home')
            else:
                form.save()
                messages.success(request, '帳號資料已成功更新')
                return redirect('home')
    else:
        form = EditProfileForm(instance=profile, user=user)

    return render(request, 'account/edit.html', {'form': form})

# 飼主主控台
@login_required
def owner_dashboard(request):
    return render(request, 'pet_info/pet_list.html')

# 獸醫主控台（需審核通過）
@login_required
def vet_dashboard(request):
    profile = request.user.profile
    if not profile.is_verified_vet:
        messages.warning(request, "您的獸醫帳號尚未通過管理員驗證。請稍後再試。")
        return redirect('home')
    return render(request, 'vet_pages/vet_home.html')

# 登出成功頁面

def logout_success(request):
    return render(request, 'account/logout_success.html')

# Google 登入前選擇帳號類型

def select_type_then_social_login(request):
    if request.method == 'POST':
        request.session['pending_account_type'] = request.POST.get('account_type')
        return redirect('/accounts/google/login/?next=/accounts/social/signup/extra/')
    return render(request, 'pages/select_account_type.html')

# 根據帳號類型導向對應主控台

def dashboard_redirect(request):
    profile = request.user.profile
    if profile.account_type == 'owner':
        return redirect('pet_list.html')
    elif profile.account_type == 'vet':
        return redirect('vet_home.html')
    else:
        return redirect('home')

# 標記從註冊流程進入

def mark_from_signup_and_redirect(request):
    request.session['from_signup'] = True
    return redirect('/accounts/google/login/?next=/accounts/social/signup/extra/')

# 清除註冊提示訊息

def clear_signup_message(request):
    request.session.pop('signup_redirect_message', None)
    return JsonResponse({'cleared': True})


# 新增寵物資料
from datetime import date as dt_date
@login_required
def add_pet(request):
    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            pet = form.save(commit=False)  # 不馬上存進資料庫
            pet.owner = request.user  # 指定目前登入使用者為飼主
            pet.save()  # 現在儲存到資料庫

            # 🔽 初始化 6 筆分類 DailyRecord（日期可為 today，content 可為空）
            categories = ['temperature', 'weight', 'diet', 'exercise', 'allergen', 'other']
            for cat in categories:
                DailyRecord.objects.create(
                    pet=pet,
                    category=cat,
                    content='',
                    date=date.today()
                )
            return redirect('pet_list')
    else:
        form = PetForm()
    return render(request, 'pet_info/add_pet.html', {
        'form': form,
    })


# 寵物列表
def pet_list(request):
    pets = Pet.objects.filter(owner=request.user)
    today = date.today()
    now = datetime.now()

    # 預約資料
    for pet in pets:
        pet.future_appointments = VetAppointment.objects.filter(pet=pet, date__gte=today).order_by('date', 'time')

    # 明天內尚未過時的預約
    tomorrow = today + timedelta(days=1)
    if request.user.is_authenticated:
        tomorrow_appointments = VetAppointment.objects.filter(
            owner=request.user,
            date=tomorrow,
        ).filter(
            time__gt=now.time() if tomorrow == today else time(0, 0)
        ).order_by('time')
    else:
        tomorrow_appointments = []
    
    appointment_digest = "|".join([
        f"{appt.date.isoformat()}_{appt.time.strftime('%H:%M')}_{appt.vet_id}_{appt.pet_id}"
        for appt in tomorrow_appointments
    ])

    notif_count = len(tomorrow_appointments)

    return render(request, 'pet_info/pet_list.html', {
        'pets': pets,
        'tomorrow_appointments': tomorrow_appointments,
        'notif_count': notif_count,
        'appointment_digest': appointment_digest,
    })


# 編輯寵物
def edit_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES, instance=pet, owner=request.user)
        if form.is_valid():
            form.save()
            messages.info(request, f"寵物 {pet.name} 資料已更新。")
            return redirect('pet_list')
    else:
        form = PetForm(instance=pet)
    return render(request, 'pet_info/edit_pet.html', {'form': form, 'pet': pet})

# 刪除寵物

def delete_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    if request.method == 'POST':
        pet.delete()
        messages.success(request, f"寵物 {pet.name} 資料已刪除。")
        return redirect('pet_list')
    return render(request, 'pet_info/delete_pet.html', {'pet': pet})

# 健康紀錄列表
def health_rec(request):
    # 撈出 飼主 所擁有的所有寵物
    pets = Pet.objects.filter(owner=request.user).prefetch_related(
        'vaccine_records', 'deworm_records', 'reports'
    )

    # 健康記錄 撈資料
    records = DailyRecord.objects.filter(pet__in=pets).select_related('pet').order_by('date')
    grouped_records = []
    pet_map = defaultdict(list)
    for record in records:
        pet_map[record.pet].append(record)
    for pet, recs in pet_map.items():
        grouped_records.append({
            'pet': pet,
            'records': recs,
        })
    pet_temperatures = {}
    pet_weights = {}
    # 取得當前月份以及過去 2 個月（共 3 個月）的體溫資料
    months = [datetime.now() - relativedelta(months=i) for i in range(3)]

    for pet in pet_map.keys():
        temp_by_month = {}
        weight_by_month = {}
        for dt in months:
            year, month = dt.year, dt.month
            key = f"{year}-{str(month).zfill(2)}"

            temp_records = get_temperature_data(pet, year, month)
            weight_records = get_weight_data(pet, year, month)

            temp_by_month[key] = [
                {'date': rec['date'], 'temperature': rec['temperature']}
                for rec in temp_records
            ]
            weight_by_month[key] = [
                {'date': rec['date'], 'weight': rec['weight']}
                for rec in weight_records
            ]
        pet_temperatures[pet.id] = temp_by_month
        pet_weights[pet.id] = weight_by_month

    return render(request, 'health_records/health_rec.html', {
        'grouped_records': grouped_records,
        'pet_temperatures': pet_temperatures,
        'pet_weights': pet_weights,
        'pets':pets
    })

# 新增每日健康紀錄
@require_POST
@csrf_exempt
def add_daily_record(request, pet_id):
    data = json.loads(request.body)
    category = data.get('category')
    content = data.get('content')
    if not category or not content:
        return JsonResponse({'success': False, 'message': '缺少欄位'})
    pet = get_object_or_404(Pet, id=pet_id)
    record = DailyRecord.objects.create(
        pet=pet,
        category=category,
        content=content,
        date=date.today()
    )
    return JsonResponse({
        'success': True,
        'record_id': record.id,
        'category': category,
        'content': content,
        'date': record.date.isoformat()
    })

# 儲存每日健康紀錄（非綁定 pet_id）
@csrf_exempt
@require_http_methods(["POST"])
def save_daily_record(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'})
    pet_id = data.get('pet_id')
    category = data.get('category')
    content = data.get('content')
    if not pet_id or not category or not content:
        return JsonResponse({'status': 'error', 'message': 'Missing required fields'})
    try:
        pet = Pet.objects.get(id=pet_id)
    except Pet.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Pet not found'})
    record = DailyRecord.objects.create(
        pet=pet,
        category=category,
        content=content,
        date=date.today()
    )
    return JsonResponse({
        'success': True,
        'record_id': record.id,
        'category': category,
        'content': content,
        'date': record.date.isoformat()
    })
# 更新生活紀錄
@csrf_exempt
def update_daily_record(request, record_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            record = DailyRecord.objects.get(id=record_id)

            if not content:
                return JsonResponse({'success': False, 'error': '內容不得為空'})

            record.content = content
            record.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': '只接受 POST'})

# 刪除每日健康紀錄
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_daily_record(request, pet_id):
    try:
        data = json.loads(request.body)
        record_id = data['record_id']
        record = DailyRecord.objects.get(id=record_id, pet_id=pet_id)
        record.delete()
        return JsonResponse({'success': True})
    except DailyRecord.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Record not found'}, status=404)


# 取消預約
@require_POST
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(VetAppointment, id=appointment_id, owner=request.user)
    appointment.delete()
    messages.success(request, "預約已取消")
    return redirect('pet_list')

@login_required
def my_appointments(request):
    """我的預約列表"""
    user = request.user
    
    # 取得篩選參數
    status_filter = request.GET.get('status', 'upcoming')
    
    if status_filter == 'upcoming':
        appointments = VetAppointment.objects.filter(
            owner=user,
            slot__date__gte=date.today(),
            status__in=['pending', 'confirmed']
        ).order_by('slot__date', 'slot__start_time')
    elif status_filter == 'past':
        appointments = VetAppointment.objects.filter(
            owner=user,
            slot__date__lt=date.today()
        ).order_by('-slot__date', '-slot__start_time')
    else:
        appointments = VetAppointment.objects.filter(
            owner=user
        ).order_by('-slot__date', '-slot__start_time')
    
    return render(request, 'appointments/my_appointments.html', {
        'appointments': appointments,
        'status_filter': status_filter,
    })

# 獸醫查看預約狀況
@login_required
def vet_appointments(request):
    # 確保是獸醫帳號
    profile = request.user.profile
    if not profile.is_verified_vet:
        return render(request, 'pages/403.html', status=403)

    # 取得該獸醫的所有預約
    today = date.today()
    now_time = datetime.now().time()

    show_history = request.GET.get('history') == '1'

    if show_history:
        # 顯示已看診紀錄（今天以前，或今天但時間已過）
        appointments = VetAppointment.objects.filter(
            vet=profile
        ).filter(
            (Q(date__lt=today)) |
            (Q(date=today) & Q(time__lt=now_time))
        )
    else:
        # 顯示尚未看診
        appointments = VetAppointment.objects.filter(
            vet=profile
        ).filter(
            (Q(date__gt=today)) |
            (Q(date=today) & Q(time__gte=now_time))
        )

    appointments = appointments.order_by('date', 'time')
    return render(request, 'vet_pages/vet_appointments.html', {'appointments': appointments, 'show_history': show_history})


@require_POST
@login_required
def vet_cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(VetAppointment, id=appointment_id)

    # 確認使用者是該名獸醫
    if appointment.vet.user != request.user:
        messages.error(request, "您無權限取消此預約。")
        return redirect('vet_appointments')

    # 取得取消原因
    cancel_reason = request.POST.get('cancel_reason', '').strip()
    if not cancel_reason:
        messages.error(request, "請輸入取消原因。")
        return redirect('vet_appointments')

    # 蒐集資料
    owner_email = appointment.owner.email
    pet_name = appointment.pet.name
    date = appointment.date
    time = appointment.time
    vet_name = f"{request.user.last_name}{request.user.first_name}" or request.user.username

    # 建立信件內容
    subject = "【毛日好】預約取消通知"
    message = f"""親愛的飼主您好：

您為寵物「{pet_name}」所預約的看診（{date} {time.strftime('%H:%M')}）已由獸醫（{vet_name}）取消。
📌 取消原因：{cancel_reason}

如需看診請重新預約，造成不便敬請見諒。

— 毛日好（Paw&Day）系統
"""

    # 刪除預約後寄信
    appointment.delete()

    print("寄信前：", owner_email)
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [owner_email],
        fail_silently=False
    )
    print("寄信成功")

    messages.success(request, "已成功取消預約，並通知飼主。")
    return redirect('vet_appointments')



# 顯示「我的看診寵物」
@login_required
def my_patients(request):
    """顯示獸醫的看診寵物"""
    try:
        vet_doctor = request.user.vet_profile
        # 使用 VetDoctor 的驗證狀態
        if not vet_doctor.is_verified:
            messages.warning(request, "您的獸醫師執照尚未通過驗證")
            return redirect('verify_vet_license')
    except:
        messages.error(request, '您不是獸醫師')
        return redirect('home')

    # 原始清單（該獸醫曾看診過的所有寵物，避免重複）
    pets = Pet.objects.filter(vetappointment__slot__doctor=vet_doctor).distinct()

    # 取得搜尋關鍵字
    q = request.GET.get('q', '')
    if q:
        pets = pets.filter(
            Q(name__icontains=q) |
            Q(owner__first_name__icontains=q) |
            Q(owner__last_name__icontains=q)
        )

    pets = pets.prefetch_related('vaccine_records', 'deworm_records', 'reports')

    return render(request, 'vet_pages/my_patients.html', {
        'pets': pets,
        'query': q,
    })
    
@login_required
def vet_pet_detail(request, pet_id):
    """獸醫查看寵物詳情"""
    try:
        vet_doctor = request.user.vet_profile
        if not vet_doctor.is_verified:
            messages.warning(request, "您的獸醫師執照尚未通過驗證")
            return redirect('verify_vet_license')
    except:
        messages.error(request, '您不是獸醫師')
        return redirect('home')

    pet = get_object_or_404(Pet, id=pet_id)
    
    # 檢查是否看診過這隻寵物
    if not VetAppointment.objects.filter(slot__doctor=vet_doctor, pet=pet).exists():
        messages.error(request, '您沒有權限查看此寵物資料')
        return redirect('my_patients')

    medical_records = pet.medicalrecord_set.filter(vet=vet_doctor).order_by('-visit_date')
    vaccine_records = pet.vaccine_records.filter(vet__user=vet_doctor.user).order_by('-date')
    deworm_records = pet.deworm_records.filter(vet__user=vet_doctor.user).order_by('-date')
    reports = pet.reports.filter(vet__user=vet_doctor.user).order_by('-date_uploaded')

    return render(request, 'vet_pages/pet_detail.html', {
        'pet': pet,
        'medical_records': medical_records,
        'vaccine_records': vaccine_records,
        'deworm_records': deworm_records,
        'reports': reports,
    })

# 新增指定寵物的病例
@login_required
def add_medical_record(request, pet_id):
    # TODO: 為指定寵物新增病例
    return render(request, 'vet_pages/create_medical_record.html')

# 修改指定寵物的病例
@login_required
def edit_medical_record(request, pet_id, record_id):
    record = get_object_or_404(MedicalRecord, id=record_id, pet_id=pet_id)

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save(commit=False)
            record.pet = record.pet  # 保險設定
            record.save()
            return redirect('my_patients')
    else:
        form = MedicalRecordForm(instance=record)

    return render(request, 'vet_pages/edit_medical_record.html', {
        'form': form,
        'pet': record.pet
    })
# 刪除指定寵物的病例
@login_required
def delete_medical_record(request, record_id):
    record = get_object_or_404(MedicalRecord, id=record_id)
    record.delete()
    return redirect('my_patients')


# 飼主取消預約通知獸醫
@require_POST
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(VetAppointment, id=appointment_id, owner=request.user)

    # 寄信資料
    vet_user = appointment.vet.user
    vet_email = vet_user.email
    pet_name = appointment.pet.name
    owner_name = f"{request.user.last_name}{request.user.first_name}" or request.user.username
    clinic = appointment.vet.clinic_name or "您的診所"
    date = appointment.date
    time = appointment.time

    subject = f"【毛日好】預約取消通知：{pet_name}"
    message = f"""親愛的 {vet_user.last_name} 醫師您好：

飼主 {owner_name} 已取消以下預約：

🐾 寵物名稱：{pet_name}
📅 日期：{date}
🕒 時間：{time.strftime('%H:%M')}
🏥 診所：{clinic}

請您留意行程更新，謝謝您的配合！

— 毛日好（Paw&Day）系統"""

    # 刪除資料
    appointment.delete()

    # 發送通知 Email 給獸醫
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [vet_email], fail_silently=False)

    messages.success(request, "預約已取消，並已通知獸醫。")
    return redirect('pet_list')




# 刪除每日健康紀錄
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_daily_record(request, pet_id):
    try:
        data = json.loads(request.body)
        record_id = data['record_id']
        record = DailyRecord.objects.get(id=record_id, pet_id=pet_id)
        record.delete()
        return JsonResponse({'success': True})
    except DailyRecord.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Record not found'}, status=404)


# 體溫頁面
def tem_rec(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    # 預設為今天的年月
    today = datetime.today()
    year, month = today.year, today.month

    # 嘗試從網址取得指定月份
    month_str = request.GET.get('month')
    if month_str:
        try:
            year, month = map(int, month_str.split('-'))
        except ValueError:
            pass  # 若格式錯誤則維持今天年月

    is_current_month = (year == today.year and month == today.month)

    # 當月的起始與結束日期
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    # 篩選當月資料
    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='temperature',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    # 整理資料
    records = []
    for rec in raw_records:
        try:
            temp_value = float(rec.content)
        except ValueError:
            continue
        records.append({
            'id': rec.id,
            'date': rec.date.strftime('%Y-%m-%d'),
            'datetime': rec.date.strftime('%Y-%m-%d'),
            'recorded_date': rec.date.strftime('%Y-%m-%d'),
            'submitted_at': localtime(rec.created_at).strftime('%H:%M'),
            'temperature': temp_value,
            'raw_content': rec.content,
        })

    context = {
        'pet': pet,
        'records': records,
        'current_month': f"{year}-{month:02d}",
        'current_month_display': f"{year} 年 {month} 月",
        'is_current_month': is_current_month,
    }
    return render(request, 'health_records/tem_rec.html', context)


# 增加體溫資料
from datetime import date as dt_date
def add_tem(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    months = list(range(1, 13))
    today = dt_date.today()   #抓取今天的日期
    current_year = today.year

    context = {
        'pet': pet,
        'months': months,
        'month': today.month,
        'day': today.day,
        'temperature': '',
    }
    if request.method == 'POST':
        try:
            month = int(request.POST.get('month'))
            day = int(request.POST.get('day'))
            temperature = request.POST.get('temperature', '').strip()
            if not temperature:
                messages.error(request, "請輸入體溫")
                raise ValueError("Missing temperature")
            record_date = dt_date(current_year, month, day)
            if record_date > today:
                messages.error(request, "日期不可超過今天")
                context.update({
                    'temperature': temperature,
                    'month': month,
                    'day': day,
                })
                return render(request, 'health_records/add_tem.html', context)
            DailyRecord.objects.create(
                pet=pet,
                date=record_date,# date 欄位只顯示年月日，時間為儲存當下時間，使用者不見
                category='temperature',
                content=temperature
            )
            return redirect('tem_rec', pet_id=pet.id)
        except ValueError:
            messages.error(request, "日期格式錯誤，請重新輸入")
            return redirect('add_tem', pet_id=pet.id)

    return render(request, 'health_records/add_tem.html', context)

# 修改體溫資料
def edit_tem(request, pet_id, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, pet_id=pet_id, category='temperature')
    if isinstance(record.date, datetime):
        record_date = record.date.date()
    else:
        record_date = record.date

    now = datetime.now()
    year = now.year

    # 取得預設月份與日
    default_month = record_date.month
    default_day = record_date.day

    # 使用 GET/POST 選擇的值（優先），否則用預設
    month = int(request.POST.get('month') or request.GET.get('month') or default_month)
    day = int(request.POST.get('day') or request.GET.get('day') or default_day)

    # 取得該月份所有天數，給前端用
    days_in_month = calendar.monthrange(year, month)[1]
    days = list(range(1, days_in_month + 1))
    months = list(range(1, 13))

    context = {
        'pet_id': pet_id,
        'months': months,
        'days': days,
        'month': month,
        'day': day,
        'temperature': record.content,
    }
    if request.method == 'POST' and 'temperature' in request.POST:
        temperature = request.POST.get('temperature')
        selected_date = datetime(year, month, day)

        # 驗證未來日期（只比對年月日）
        if selected_date.date() > datetime.today().date():
            messages.error(request, "日期不可超過今天")
            context.update({
                'temperature': temperature,
                'month': month,
                'day': day,
            })
            return render(request, 'health_records/edit_tem.html', context)

        combined_datetime = datetime.combine(selected_date, now.time())

        record.date = combined_datetime
        record.content = temperature
        record.save()
        return redirect('tem_rec', pet_id=pet_id)

    return render(request, 'health_records/edit_tem.html', context)

# 刪除體溫資料
def delete_tem(request, pet_id, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, pet_id=pet_id, category='temperature')
    record.delete()
    return redirect('tem_rec', pet_id=pet_id)

# （體溫）共用函式
def get_monthly_tem(request, pet_id, year, month):
    pet = get_object_or_404(Pet, id=pet_id)

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='temperature',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')
    result = []
    for rec in raw_records:
        try:
            temp = float(rec.content)
        except ValueError:
            continue
        result.append({
            'date': rec.date.strftime('%Y-%m-%d'),
            'temperature': temp,
        })
    return JsonResponse(result, safe=False)

# （體重）共用函式
def get_monthly_weight(request, pet_id, year, month):
    pet = get_object_or_404(Pet, id=pet_id)

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='weight',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    result = []
    for rec in raw_records:
        try:
            weight = float(rec.content)
        except ValueError:
            continue
        result.append({
            'date': rec.date.strftime('%Y-%m-%d'),
            'weight': weight,
        })
    return JsonResponse(result, safe=False)



# 體重頁面
def weight_rec(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    # 預設為今天的年月
    today = datetime.today()
    year, month = today.year, today.month

    # 取得目前選定月份
    month_str = request.GET.get('month')
    if month_str:
        try:
            year, month = map(int, month_str.split('-'))
        except ValueError:
            year, month = datetime.now().year, datetime.now().month
    else:
        year, month = datetime.now().year, datetime.now().month

    is_current_month = (year == today.year and month == today.month)

    # 當月的起始與結束日期
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    # 篩選當月資料
    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='weight',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    # 整理資料
    records = []
    for rec in raw_records:
        try:
            weight_value = float(rec.content)
        except ValueError:
            continue
        records.append({
            'id': rec.id,
            'date': rec.date.strftime('%Y-%m-%d'),
            'datetime': rec.date.strftime('%Y-%m-%d'),  # 使用者填的日期
            'recorded_date': rec.date.strftime('%Y-%m-%d'),  # ✅ 額外：使用者填的
            'submitted_at': localtime(rec.created_at).strftime('%H:%M'),
            'weight': weight_value,
            'raw_content': rec.content,
        })
    context = {
        'pet': pet,
        'records': records,
        'current_month': f"{year}-{month:02d}",
        'current_month_display': f"{year} 年 {month} 月",
        'is_current_month': is_current_month,
    }
    return render(request, 'health_records/weight_rec.html', context)


#  增加體重資料
from datetime import date as dt_date
def add_weight(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    months = list(range(1, 13))
    today = dt_date.today()
    current_year = today.year
    context = {
        'pet': pet,
        'months': months,
        'month': today.month,
        'day': today.day,
        'weight': '',
    }
    if request.method == 'POST':
        try:
            month = int(request.POST.get('month'))
            day = int(request.POST.get('day'))
            weight = request.POST.get('weight', '').strip()
            if not weight:
                messages.error(request, "請輸入體重")
                raise ValueError("Missing weight")
            record_date = dt_date(current_year, month, day)
            if record_date > today:
                messages.error(request, "日期不可超過今天")
                context.update({
                    'weight': weight,
                    'month': month,
                    'day': day,
                })
                return render(request, 'health_records/add_weight.html', context)
            DailyRecord.objects.create(
                pet=pet,
                date=record_date,# date 欄位只顯示年月日，時間為儲存當下時間，使用者不見
                category='weight',
                content=weight
            )
            return redirect('weight_rec', pet_id=pet.id)
        except ValueError:
            messages.error(request, "日期格式錯誤，請重新輸入")
            return redirect('add_weight', pet_id=pet.id)

    return render(request, 'health_records/add_weight.html', context)

# 修改體重資料
def edit_weight(request, pet_id, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, pet_id=pet_id, category='weight')

    if isinstance(record.date, datetime):
        record_date = record.date.date()
    else:
        record_date = record.date

    now = datetime.now()
    year = now.year

    # 取得預設月份與日
    default_month = record_date.month
    default_day = record_date.day

    # 使用 GET/POST 選擇的值（優先），否則用預設
    month = int(request.POST.get('month') or request.GET.get('month') or default_month)
    day = int(request.POST.get('day') or request.GET.get('day') or default_day)

    # 取得該月份所有天數，給前端用
    days_in_month = calendar.monthrange(year, month)[1]
    days = list(range(1, days_in_month + 1))
    months = list(range(1, 13))

    context = {
        'pet_id': pet_id,
        'months': months,
        'days': days,
        'month': month,
        'day': day,
        'weight': record.content,
    }
    if request.method == 'POST' and 'weight' in request.POST:
        weight = request.POST.get('weight')
        selected_date = datetime(year, month, day)
        # 驗證未來日期（只比對年月日）
        if selected_date.date() > datetime.today().date():
            messages.error(request, "日期不可超過今天")
            context.update({
                'weight': weight,
                'month': month,
                'day': day,
            })
            return render(request, 'health_records/edit_weight.html', context)

        combined_datetime = datetime.combine(selected_date, now.time())

        record.date = combined_datetime
        record.content = weight
        record.save()
        return redirect('weight_rec', pet_id=pet_id)

    return render(request, 'health_records/edit_weight.html', context)

# 刪除體重資料
def delete_weight(request, pet_id, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, pet_id=pet_id, category='weight')
    record.delete()
    return redirect('weight_rec', pet_id=pet_id)

# 新增疫苗
@login_required
def add_vaccine(request, pet_id):
    """新增疫苗記錄"""
    try:
        vet_doctor = request.user.vet_profile
        if not vet_doctor.is_verified:
            messages.warning(request, "您的獸醫師執照尚未通過驗證")
            return redirect('verify_vet_license')
    except:
        messages.error(request, '您不是獸醫師')
        return redirect('home')
    
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        form = VaccineRecordForm(request.POST)
        if form.is_valid():
            vaccine = form.save(commit=False)
            vaccine.pet = pet
            # 建立對應的 Profile 記錄
            vaccine.vet, created = Profile.objects.get_or_create(
                user=vet_doctor.user,
                defaults={'account_type': 'vet'}
            )
            vaccine.save()
            messages.success(request, '疫苗記錄已新增')
            return redirect('vet_pet_detail', pet_id=pet.id)
    else:
        form = VaccineRecordForm()
    
    return render(request, 'vaccine&deworm/add_vaccine.html', {
        'form': form,
        'pet': pet
    })

from django.http import HttpResponseForbidden

@login_required
def edit_vaccine(request, pet_id, vaccine_id):
    pet = get_object_or_404(Pet, id=pet_id)
    vaccine = get_object_or_404(VaccineRecord, id=vaccine_id, pet=pet)

    # 權限檢查：只能編輯自己建立的疫苗紀錄
    if vaccine.vet != request.user.profile:
        return HttpResponseForbidden("你沒有權限編輯這筆疫苗紀錄。")

    if request.method == 'POST':
        form = VaccineRecordForm(request.POST, instance=vaccine)
        if form.is_valid():
            edited_vaccine = form.save(commit=False)
            edited_vaccine.vet = request.user.profile  # 保持原獸醫資訊
            edited_vaccine.save()
            return redirect('my_patients')
    else:
        form = VaccineRecordForm(instance=vaccine)

    return render(request, 'vaccine&deworm/edit_vaccine.html', {
        'form': form,
        'pet': pet,
        'vaccine': vaccine,
    })


# 刪除疫苗紀錄
@login_required
def delete_vaccine(request, vaccine_id):
    vaccine = get_object_or_404(VaccineRecord, id=vaccine_id)

    # 確保只有該紀錄的獸醫或具權限者能刪除（可自定邏輯）
    if request.user.profile == vaccine.vet:
        pet_id = vaccine.pet.id
        vaccine.delete()
        return redirect('my_patients')  # 或導回特定 pet 的健康紀錄頁面
    else:
        return redirect('permission_denied')  # 可自定一個拒絕頁面


# 新增疫苗
@login_required
def add_deworm(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        form = DewormRecordForm(request.POST)
        if form.is_valid():
            deworms = form.save(commit=False)
            deworms.pet = pet
            deworms.vet = request.user.profile  # 登入獸醫
            deworms.save()
            return redirect('my_patients')
    else:
        form = DewormRecordForm()

    return render(request, 'vaccine&deworm/add_deworm.html', {
        'form': form,
        'pet': pet
    })


@login_required
def edit_deworm(request, pet_id, deworm_id):
    pet = get_object_or_404(Pet, id=pet_id)
    deworm = get_object_or_404(DewormRecord, id=deworm_id, pet=pet)

    # 權限檢查：只能編輯自己建立的疫苗紀錄
    if deworm.vet != request.user.profile:
        return HttpResponseForbidden("你沒有權限編輯這筆疫苗紀錄。")

    if request.method == 'POST':
        form = DewormRecordForm(request.POST, instance=deworm)
        if form.is_valid():
            edited_deworm = form.save(commit=False)
            edited_deworm.vet = request.user.profile  # 保持原獸醫資訊
            edited_deworm.save()
            return redirect('my_patients')
    else:
        form = DewormRecordForm(instance=deworm)

    return render(request, 'vaccine&deworm/edit_deworm.html', {
        'form': form,
        'pet': pet,
        'deworm': deworm,
    })

# 刪除疫苗紀錄
@login_required
def delete_deworm(request, deworm_id):
    deworm = get_object_or_404(DewormRecord, id=deworm_id)

    # 確保只有該紀錄的獸醫或具權限者能刪除（可自定邏輯）
    if request.user.profile == deworm.vet:
        pet_id = deworm.pet.id
        deworm.delete()
        return redirect('my_patients')  # 或導回特定 pet 的健康紀錄頁面
    else:
        return redirect('permission_denied')  # 可自定一個拒絕頁面

# 新增報告
@login_required
def add_report(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.pet = pet
            report.vet = request.user.profile  # 登入的獸醫
            report.save()
            return redirect('my_patients')
    else:
        form = ReportForm()

    return render(request, 'vaccine&deworm/add_report.html', {
        'form': form,
        'pet': pet
    })
# 刪除報告
@login_required
def delete_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)

    # 確保只有該紀錄的獸醫或具權限者能刪除（可自定邏輯）
    if request.user.profile == report.vet:
        pet_id = report.pet.id
        report.delete()
        return redirect('my_patients')  # 或導回特定 pet 的健康紀錄頁面
    else:
        return redirect('permission_denied')  # 可自定一個拒絕頁面

 
@login_required
@require_medical_license
def create_medical_record(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    profile = request.user.profile

    if profile.account_type != 'vet':
        return render(request, 'unauthorized.html')  # 非獸醫導向未授權頁

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.pet = pet
            record.vet = profile
            record.clinic_location = profile.clinic_name  # 自動填入診所地點
            record.save()
            return redirect('my_patients')  # 統一導向與 add_vaccine 相同
    else:
        form = MedicalRecordForm(initial={'pet': pet, 'clinic_location': profile.clinic_name})

    return render(request, 'vet_pages/create_medical_record.html', {
        'form': form,
        'pet': pet
    })

# 通知
@login_required
def get_notification_count(request):
    user = request.user
    tomorrow = timezone.now().date() + timedelta(days=1)
    count = 0

    if hasattr(user, 'profile'):
        account_type = user.profile.account_type
        if account_type == 'owner':
            count = VetAppointment.objects.filter(owner=user, date=tomorrow).count()
        elif account_type == 'vet':
            count = VetAppointment.objects.filter(vet=user.profile, date=tomorrow).count()

    return JsonResponse({'count': count})

# 通知頁面邏輯
@login_required
def notification_page(request):
    user = request.user
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    appointments = []
    vaccine_reminders = []
    deworm_reminders = []
    role = None

    if hasattr(user, 'profile'):
        role = user.profile.account_type

        if role == 'owner':
            appointments = VetAppointment.objects.filter(owner=user, date=tomorrow)

            # 每隻寵物的最新疫苗日期
            # ---------- 疫苗：一年效期 ----------
            latest_vaccine_dates = (VaccineRecord.objects
                .filter(pet__owner=user)
                .values('pet')
                .annotate(last_vaccine_date=Max('date'))
            )

            for item in latest_vaccine_dates:
                pet_id = item['pet']
                last_date = item['last_vaccine_date']
                days_diff = (today - last_date).days

                # 如果是提前一天或提前一個月提醒
                if days_diff in [365 - 30, 365 - 1]:  # 即 335 或 364 天
                    pet = Pet.objects.get(id=pet_id)
                    vaccine_reminders.append({
                        'pet': pet,
                        'last_date': last_date,
                        'days_left': 365 - days_diff
                    })

                    # 寄信通知
                    subject = f"【疫苗提醒】{pet.name} 的疫苗即將到期"
                    message = f"""
親愛的 {user.last_name or ''}{user.first_name or user.username} 飼主您好：

您的寵物「{pet.name}」的最近一次疫苗接種日期為 {last_date}。
目前距離一年效期只剩下 {365 - days_diff} 天，建議您儘快安排補打疫苗。

歡迎使用「毛日好 Paw&Day」系統預約獸醫進行疫苗接種。

祝 平安健康，
毛日好 Paw&Day 團隊
"""
                    send_mail(
                        subject,
                         message,
                        f"毛日好通知 <{settings.DEFAULT_FROM_EMAIL}>",
                        [user.email],
                        fail_silently=True
                    )

            # ---------- 驅蟲：半年效期 ----------
            latest_deworm_dates = (DewormRecord.objects
                .filter(pet__owner=user)
                .values('pet')
                .annotate(last_deworm_date=Max('date'))
            )

            for item in latest_deworm_dates:
                pet_id = item['pet']
                last_date = item['last_deworm_date']
                days_diff = (today - last_date).days

                if days_diff in [182 - 30, 182 - 1]:  # 半年約 182 天
                    pet = Pet.objects.get(id=pet_id)
                    deworm_reminders.append({
                        'pet': pet,
                        'last_date': last_date,
                        'days_left': 182 - days_diff
                    })

                    # Email 通知驅蟲
                    send_mail(
                        subject=f"【驅蟲提醒】{pet.name} 的驅蟲即將到期",
                        message=f"""
親愛的 {user.last_name or ''}{user.first_name or user.username} 飼主您好：

您的寵物「{pet.name}」的最近一次驅蟲日期為 {last_date}。
目前距離半年效期只剩下 {182 - days_diff} 天，建議您儘快安排補打驅蟲藥。

歡迎使用「毛日好 Paw&Day」系統預約獸醫進行驅蟲服務。

祝 平安健康，
毛日好 Paw&Day 團隊
""",
                        from_email=f"毛日好通知 <{settings.DEFAULT_FROM_EMAIL}>",
                        recipient_list=[user.email],
                        fail_silently=True
                    )

        elif role == 'vet':
            appointments = VetAppointment.objects.filter(vet=user.profile, date=tomorrow)

    return render(request, 'pages/notifications.html', {
        'appointments': appointments,
        'role': role,
        'tomorrow': tomorrow,
        'vaccine_reminders': vaccine_reminders,
        'deworm_reminders': deworm_reminders,
    })

###############################地圖############################

pet_types = PetType.objects.filter(is_active=True).order_by('name')

def map_home(request):
    """地圖首頁"""
    # 取得所有可用的城市，用於篩選器
    cities = PetLocation.objects.values_list('city', flat=True).distinct().order_by('city')
    cities = [city for city in cities if city]  # 過濾空值
    
    # 從資料庫取得寵物類型並加上圖標
    pet_types_raw = PetType.objects.filter(is_active=True).order_by('name')
    
    # 為寵物類型添加圖標（這應該在模型中定義，或使用字典映射）
    PET_TYPE_ICONS = {
        'small_dog': '🐕‍',
        'medium_dog': '🐕',
        'large_dog': '🦮',
        'cat': '🐈',
        'bird': '🦜',
        'rodent': '🐹',
        'reptile': '🦎',
        'other': '🦝'
    }
    
    pet_types = []
    for pet_type in pet_types_raw:
        pet_types.append({
            'code': pet_type.code,
            'name': pet_type.name,
            'icon': PET_TYPE_ICONS.get(pet_type.code, '🐾')
        })
    
    context = {
        'cities': cities,
        'pet_types': pet_types,
    }
    return render(request, 'petmap/map.html', context)


def api_locations(request):
    """簡化版地點資料 API - 專注於解決篩選問題"""
    try:
        print("🔍 API 請求開始...")
        print(f"所有 GET 參數: {dict(request.GET)}")
        
        # 取得查詢參數
        location_type = request.GET.get('type', None)
        city = request.GET.get('city', None)
        search = request.GET.get('search', None)
        
        # 處理寵物類型篩選參數
        pet_type_codes = []
        for param_name, param_value in request.GET.items():
            if param_name.startswith('support_') and param_value == 'true':
                pet_code = param_name.replace('support_', '')
                pet_type_codes.append(pet_code)
        
        print(f"📊 篩選條件:")
        print(f"  - 服務類型: {location_type}")
        print(f"  - 城市: {city}")
        print(f"  - 搜尋: {search}")
        print(f"  - 寵物類型: {pet_type_codes}")
        
        # 基本查詢 - 只選擇有座標的地點
        query = PetLocation.objects.filter(
            lat__isnull=False, 
            lon__isnull=False
        ).prefetch_related('service_types', 'pet_types')
        
        initial_count = query.count()
        print(f"📍 初始查詢結果: {initial_count} 個有座標的地點")
        
        # 服務類型篩選
        if location_type:
            print(f"🏥 應用服務類型篩選: {location_type}")
            
            # 檢查這個服務類型是否存在
            service_exists = ServiceType.objects.filter(code=location_type, is_active=True).exists()
            print(f"服務類型 '{location_type}' 是否存在: {service_exists}")
            
            if service_exists:
                filtered_query = query.filter(
                    service_types__code=location_type,
                    service_types__is_active=True
                ).distinct()
                
                filtered_count = filtered_query.count()
                print(f"篩選後結果: {filtered_count} 個地點")
                
                if filtered_count > 0:
                    query = filtered_query
                else:
                    print("⚠️ 篩選後沒有結果，但仍會返回空列表")
            else:
                print(f"❌ 服務類型 '{location_type}' 不存在")
                query = query.none()  # 返回空查詢集
        
        # 城市篩選
        if city:
            before_count = query.count()
            query = query.filter(city=city)
            after_count = query.count()
            print(f"🏙️ 城市篩選 ({city}): {before_count} -> {after_count}")
        
        # 搜尋篩選
        if search:
            before_count = query.count()
            query = query.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search)
            ).distinct()
            after_count = query.count()
            print(f"🔍 搜尋篩選 ({search}): {before_count} -> {after_count}")
        
        # 寵物類型篩選
        if pet_type_codes:
            print(f"🐾 應用寵物類型篩選: {pet_type_codes}")
            
            # 檢查有效的寵物類型代碼
            valid_pet_codes = list(PetType.objects.filter(
                code__in=pet_type_codes, 
                is_active=True
            ).values_list('code', flat=True))
            
            print(f"有效的寵物類型代碼: {valid_pet_codes}")
            
            if valid_pet_codes:
                before_count = query.count()
                pet_filtered_query = query.filter(
                    pet_types__code__in=valid_pet_codes,
                    pet_types__is_active=True
                ).distinct()
                
                pet_filtered_count = pet_filtered_query.count()
                print(f"寵物類型篩選: {before_count} -> {pet_filtered_count}")
                
                # 如果沒有地點明確支援這些寵物類型，不篩選（顯示所有地點）
                if pet_filtered_count > 0:
                    query = pet_filtered_query
                else:
                    print("⚠️ 沒有地點明確支援指定寵物類型，顯示所有符合其他條件的地點")
        
        # 限制結果數量並執行查詢
        max_results = 200
        final_locations = list(query[:max_results])
        final_count = len(final_locations)
        
        print(f"📊 最終結果: {final_count} 個地點")
        
        # 轉換為 GeoJSON 格式
        features = []
        
        for i, location in enumerate(final_locations):
            try:
                # 獲取關聯資料
                service_types = list(location.service_types.all())
                pet_types = list(location.pet_types.all())
                
                service_names = [st.name for st in service_types]
                pet_names = [pt.name for pt in pet_types]
                
                # 建立寵物支援屬性
                pet_support = {}
                for pt in pet_types:
                    pet_support[f'support_{pt.code}'] = True
                
                properties = {
                    'id': location.id,
                    'name': location.name or '未命名',
                    'address': location.address or '',
                    'phone': location.phone or '',
                    'city': location.city or '',
                    'district': location.district or '',
                    'rating': float(location.rating) if location.rating else None,
                    'rating_count': location.rating_count or 0,
                    'has_emergency': location.has_emergency,
                    'service_types': service_names,
                    'supported_pet_types': pet_names,
                    **pet_support
                }
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [float(location.lon), float(location.lat)]
                    },
                    'properties': properties
                }
                features.append(feature)
                
                # 每處理 20 個地點輸出一次進度
                if (i + 1) % 20 == 0:
                    print(f"🔄 已處理 {i + 1}/{final_count} 個地點")
                    
            except Exception as e:
                print(f"❌ 處理地點 {location.id} 時發生錯誤: {e}")
                continue
        
        geojson_response = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        print(f"✅ API 處理完成，返回 {len(features)} 個地點特徵")
        print(f"回應大小: {len(str(geojson_response))} 字元")
        
        return JsonResponse(geojson_response)
        
    except Exception as e:
        print(f"💥 API 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'error': 'Internal server error',
            'message': str(e),
            'type': 'server_error'
        }, status=500)
                        
@login_required
def manage_business_hours(request, location_id):
    """管理地點營業時間"""
    location = get_object_or_404(PetLocation, id=location_id)
    
    if request.method == 'POST':
        # 處理營業時間的新增/修改
        pass
    
    # 取得現有營業時間
    business_hours = BusinessHours.objects.filter(location=location).order_by('day_of_week', 'period_order')
    
    return render(request, 'petmap/manage_business_hours.html', {
        'location': location,
        'business_hours': business_hours
    })

@login_required  
def add_location(request):
    """新增地點"""
    if request.method == 'POST':
        # 處理地點新增邏輯
        pass
    
    service_types = ServiceType.objects.filter(is_active=True)
    pet_types = PetType.objects.filter(is_active=True)
    
    return render(request, 'petmap/add_location.html', {
        'service_types': service_types,
        'pet_types': pet_types
    })

def api_stats(request):
    """統計資料 API（可選）"""
    # 按服務類型統計
    service_stats = {}
    for service_type in ServiceType.objects.filter(is_active=True):
        count = service_type.locations.count()
        service_stats[service_type.code] = {
            'name': service_type.name,
            'count': count
        }


###############################地圖############################

###############################24小時急診地圖############################

def emergency_map_home(request):
    """24小時急診地圖首頁"""
    # 取得所有可用的城市，用於篩選器
    cities = PetLocation.objects.values_list('city', flat=True).distinct().order_by('city')
    cities = [city for city in cities if city]  # 過濾空值
    
    # 從資料庫取得寵物類型
    pet_types_raw = PetType.objects.filter(is_active=True).order_by('name')
    
    # 為寵物類型添加圖標
    PET_TYPE_ICONS = {
        'small_dog': '🐕‍',
        'medium_dog': '🐕',
        'large_dog': '🦮',
        'cat': '🐈',
        'bird': '🦜',
        'rodent': '🐹',
        'reptile': '🦎',
        'other': '🦝'
    }
    
    pet_types = []
    for pet_type in pet_types_raw:
        pet_types.append({
            'code': pet_type.code,
            'name': pet_type.name,
            'icon': PET_TYPE_ICONS.get(pet_type.code, '🐾')
        })
    
    context = {
        'cities': cities,
        'pet_types': pet_types,
        'page_title': '24小時急診地圖',
        'is_emergency_page': True,
    }
    return render(request, 'petmap/emergency_map.html', context)


def api_emergency_locations(request):
    """急診醫院資料 API - 專門提供急診醫療服務"""
    try:
        print("🚨 急診醫院 API 請求開始...")
        print(f"所有 GET 參數: {dict(request.GET)}")
        
        # 取得查詢參數
        location_type = request.GET.get('type', 'hospital')  # 預設只查醫院
        city = request.GET.get('city', None)
        search = request.GET.get('search', None)
        emergency_only = request.GET.get('emergency', 'true')  # 預設只要急診
        
        # 處理寵物類型篩選參數
        pet_type_codes = []
        for param_name, param_value in request.GET.items():
            if param_name.startswith('support_') and param_value == 'true':
                pet_code = param_name.replace('support_', '')
                pet_type_codes.append(pet_code)
        
        print(f"🏥 急診篩選條件:")
        print(f"  - 服務類型: {location_type}")
        print(f"  - 城市: {city}")
        print(f"  - 搜尋: {search}")
        print(f"  - 只要急診: {emergency_only}")
        print(f"  - 寵物類型: {pet_type_codes}")
        
        # 基本查詢 - 只選擇有座標的醫院
        query = PetLocation.objects.filter(
            lat__isnull=False, 
            lon__isnull=False
        ).prefetch_related('service_types', 'pet_types')
        
        # 限制為醫院類型
        if location_type == 'hospital':
            query = query.filter(
                service_types__code='hospital',
                service_types__is_active=True
            ).distinct()
        
        # 急診篩選 - 只顯示有急診服務的醫院
        if emergency_only == 'true':
            query = query.filter(has_emergency=True)
        
        initial_count = query.count()
        print(f"🏥 初始急診醫院查詢結果: {initial_count} 個")
        
        # 城市篩選
        if city:
            before_count = query.count()
            query = query.filter(city=city)
            after_count = query.count()
            print(f"🏙️ 城市篩選 ({city}): {before_count} -> {after_count}")
        
        # 搜尋篩選
        if search:
            before_count = query.count()
            query = query.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search)
            ).distinct()
            after_count = query.count()
            print(f"🔍 搜尋篩選 ({search}): {before_count} -> {after_count}")
        
        # 寵物類型篩選
        if pet_type_codes:
            print(f"🐾 應用寵物類型篩選: {pet_type_codes}")
            
            valid_pet_codes = list(PetType.objects.filter(
                code__in=pet_type_codes, 
                is_active=True
            ).values_list('code', flat=True))
            
            if valid_pet_codes:
                before_count = query.count()
                query = query.filter(
                    pet_types__code__in=valid_pet_codes,
                    pet_types__is_active=True
                ).distinct()
                after_count = query.count()
                print(f"寵物類型篩選: {before_count} -> {after_count}")
        
        # 限制結果數量並執行查詢
        max_results = 100  # 急診醫院數量相對較少
        final_locations = list(query[:max_results])
        final_count = len(final_locations)
        
        print(f"🏥 最終急診醫院結果: {final_count} 個")
        
        # 轉換為 GeoJSON 格式
        features = []
        
        for i, location in enumerate(final_locations):
            try:
                # 獲取關聯資料
                service_types = list(location.service_types.all())
                pet_types = list(location.pet_types.all())
                
                service_names = [st.name for st in service_types]
                pet_names = [pt.name for pt in pet_types]
                
                # 建立寵物支援屬性
                pet_support = {}
                for pt in pet_types:
                    pet_support[f'support_{pt.code}'] = True
                
                # 急診醫院特殊屬性
                emergency_level = 'basic'
                if any('一級' in service or '重度' in service for service in service_names):
                    emergency_level = 'trauma_center'
                elif any('重症' in service or 'ICU' in service for service in service_names):
                    emergency_level = 'icu'
                elif any('外科' in service for service in service_names):
                    emergency_level = 'surgery'
                
                properties = {
                    'id': location.id,
                    'name': location.name or '急診醫院',
                    'address': location.address or '',
                    'phone': location.phone or '',
                    'city': location.city or '',
                    'district': location.district or '',
                    'rating': float(location.rating) if location.rating else None,
                    'rating_count': location.rating_count or 0,
                    'has_emergency': location.has_emergency,
                    'emergency_level': emergency_level,
                    'service_types': service_names,
                    'supported_pet_types': pet_names,
                    'lat': float(location.lat),
                    'lon': float(location.lon),
                    **pet_support
                }
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [float(location.lon), float(location.lat)]
                    },
                    'properties': properties
                }
                features.append(feature)
                
            except Exception as e:
                print(f"❌ 處理急診醫院 {i} 時發生錯誤: {e}")
                continue
        
        geojson_response = {
            'type': 'FeatureCollection',
            'features': features,
            'metadata': {
                'total_count': final_count,
                'emergency_hospitals': True,
                'query_params': {
                    'city': city,
                    'search': search,
                    'emergency_only': emergency_only,
                    'pet_types': pet_type_codes
                }
            }
        }
        
        print(f"✅ 急診醫院 API 處理完成，返回 {len(features)} 個急診醫院")
        
        return JsonResponse(geojson_response)
        
    except Exception as e:
        print(f"💥 急診醫院 API 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'error': 'Emergency hospital API error',
            'message': str(e),
            'type': 'server_error',
            'emergency_contact': '119'  # 提供緊急聯絡方式
        }, status=500)

###############################24小時急診地圖############################

def custom_400(request, exception=None):
    """自訂 400 錯誤處理器"""
    return render(request, 'pages/400.html', status=400)

def custom_403(request, exception=None):
    """自訂 403 錯誤頁面"""
    return render(request, 'pages/403.html', status=403)

def custom_404(request, exception=None):
    """自訂 404 錯誤頁面"""
    return render(request, 'pages/404.html', status=404)

def custom_500(request):
    """自訂 500 錯誤頁面"""
    return render(request, 'pages/500.html', status=500)

def permission_denied_view(request):
    """自訂權限不足頁面（可在 views 中直接調用）"""
    return render(request, 'pages/permission_denied.html')