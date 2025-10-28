# petapp/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.db import models, transaction
from .models import (
    # VetClinic, VetDoctor,
    Profile, Pet, Species, SterilizationStatus,
    Gender, DailyRecord, VaccineRecord, DewormRecord,
    Report, MedicalRecord,
    # VetSchedule, AppointmentSlot, VetAppointment, VetScheduleException,
    AdoptionPet, TransferRequest, REGION_CHOICES, # WEEKDAYS
)
from .choices import (
    SPECIES_CHOICES, DOG_CHOICES, CAT_CHOICES, OTHER_CHOICES,
    FEATURE_CHOICES, PHYSICAL_CHOICES, ADOPTCONDITION_CHOICES, 
    DOGVACCINE_CHOICES, CATVACCINE_CHOICES
)
from allauth.account.forms import SignupForm
import re
import requests
import json
from datetime import date, time, datetime, timedelta

# 縣市選項常數
CITY_CHOICES = [
    ('台北市', '台北市'), ('新北市', '新北市'), ('桃園市', '桃園市'),
    ('台中市', '台中市'), ('台南市', '台南市'), ('高雄市', '高雄市'),
    ('基隆市', '基隆市'), ('新竹市', '新竹市'), ('嘉義市', '嘉義市'),
    ('新竹縣', '新竹縣'), ('苗栗縣', '苗栗縣'), ('彰化縣', '彰化縣'),
    ('南投縣', '南投縣'), ('雲林縣', '雲林縣'), ('嘉義縣', '嘉義縣'),
    ('屏東縣', '屏東縣'), ('宜蘭縣', '宜蘭縣'), ('花蓮縣', '花蓮縣'),
    ('台東縣', '台東縣'), ('澎湖縣', '澎湖縣'), ('金門縣', '金門縣'),
    ('連江縣', '連江縣'),
]


# ===== 獸醫院註冊表單 =====
# VetClinicRegistrationForm 已註解停用 (2025-10-24)
# class VetClinicRegistrationForm(forms.ModelForm):
#     """診所註冊表單"""
    
    # 診所基本資訊
#     clinic_name = forms.CharField(
#         max_length=100,
#         label='診所名稱',
#         help_text='請填寫與農委會登記完全相同的診所名稱',
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：台北市愛心動物醫院'
#         })
#     )
    
#     license_number = forms.CharField(
#         max_length=50,
#         label='開業執照字號',
#         help_text='請填寫與農委會登記完全相同的執照字號',
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：北市動字第1234567號'
#         })
#     )
    
#     clinic_phone = forms.CharField(
#         max_length=20,
#         label='診所電話',
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：02-12345678'
#         })
#     )
    
#     clinic_email = forms.EmailField(
#         label='診所信箱',
#         widget=forms.EmailInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：clinic@example.com'
#         })
#     )
    
#     clinic_address = forms.CharField(
#         max_length=255,
#         label='診所地址',
#         help_text='請填寫與農委會登記完全相同的診所地址',
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：台北市中正區重慶南路一段122號'
#         })
#     )
    
    # 管理員帳號資訊
#     admin_username = forms.CharField(
#         max_length=30,
#         label='管理員帳號',
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '英文、數字或底線，3-30個字元'
#         })
#     )
    
#     admin_email = forms.EmailField(
#         label='管理員信箱',
#         widget=forms.EmailInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：admin@example.com'
#         })
#     )
    
#     admin_password = forms.CharField(
#         min_length=8,
#         label='管理員密碼',
#         widget=forms.PasswordInput(attrs={
#             'class': 'form-control',
#             'placeholder': '至少8個字元，建議包含大小寫字母、數字'
#         })
#     )
    
#     admin_password_confirm = forms.CharField(
#         label='確認密碼',
#         widget=forms.PasswordInput(attrs={
#             'class': 'form-control',
#             'placeholder': '請再次輸入密碼'
#         })
#     )
    
#     admin_real_name = forms.CharField(
#         max_length=20,
#         label='管理員真實姓名',
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：王小明'
#         })
#     )
    
#     admin_phone = forms.CharField(
#         max_length=15,
#         label='管理員電話',
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：0912345678'
#         })
#     )
    
    # 驗證確認
#     verification_confirmed = forms.BooleanField(
#         label='確認接受農委會驗證',
#         required=True,
#         widget=forms.CheckboxInput(attrs={
#             'class': 'form-check-input'
#         })
#     )
    
#     class Meta:
#         model = VetClinic
#         fields = [
#             'clinic_name', 'license_number', 'clinic_phone',
#             'clinic_address', 'clinic_email', 'clinic_mode',
#         ]
#         widgets = {
#            'clinic_mode': forms.RadioSelect(choices=VetClinic.CLINIC_MODE_CHOICES),
#         }
    
#     def clean_admin_username(self):
#         """驗證管理員帳號"""
#         username = self.cleaned_data['admin_username']
        
        # 檢查是否已存在
#         if User.objects.filter(username=username).exists():
#             raise forms.ValidationError('此使用者名稱已被使用')
        
        # 檢查格式
#         if not re.match(r'^[a-zA-Z0-9_]+$', username):
#             raise forms.ValidationError('帳號只能包含英文、數字和底線')
        
#         return username
    
#     def clean_admin_email(self):
#         """驗證管理員信箱"""
#         email = self.cleaned_data['admin_email']
        
        # 檢查是否已存在
#         if User.objects.filter(email=email).exists():
#             raise forms.ValidationError('此電子郵件已被使用')
        
#         return email
    
#     def clean_license_number(self):
#         """驗證執照字號"""
#         license_number = self.cleaned_data['license_number']
        
        # 檢查是否已存在
#         if VetClinic.objects.filter(license_number=license_number).exists():
#             raise forms.ValidationError('此執照字號已被註冊')
        
#         return license_number
    
#     def clean(self):
#         """全表單驗證"""
#         cleaned_data = super().clean()
        
        # 驗證密碼確認
#         password = cleaned_data.get('admin_password')
#         password_confirm = cleaned_data.get('admin_password_confirm')
        
#         if password and password_confirm:
#             if password != password_confirm:
#                 raise forms.ValidationError('密碼確認不符')
        
#         return cleaned_data
    
#     def verify_with_moa_api(self, clinic_name, license_number):
#         """即時驗證農委會API"""
#         try:
#             api_url = "https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=078"
#             print(f"INFO 開始驗證: {clinic_name} - {license_number}")
            
#             response = requests.get(api_url, timeout=30)
            
#             if response.status_code == 200:
#                 data = response.json()
#                 print(f"INFO API回應資料筆數: {len(data)}")
                
#                 for clinic_data in data:
                    # 精確比對診所名稱和執照字號
#                     api_license = clinic_data.get('字號', '').strip()
#                     api_name = clinic_data.get('機構名稱', '').strip()
                    
#                     if api_license == license_number and api_name == clinic_name:
#                         print(f"SUCCESS 找到匹配的診所: {clinic_data}")
                        
                        # 檢查開業狀態
#                         status = clinic_data.get('狀態', '').strip()
#                         if status != '開業':
#                             return False, f"診所狀態為「{status}」，無法註冊"
                        
                        # 儲存驗證資料到表單實例
#                         self.moa_data = clinic_data
#                         return True, "農委會資料驗證成功"
                
#                 return False, "農委會資料庫中找不到對應的診所資訊，請確認診所名稱和執照字號是否與農委會登記完全相同"
#             else:
#                 return False, f"無法連接農委會API (HTTP {response.status_code})"
                
#         except Exception as e:
#             print(f"ERROR 驗證過程發生錯誤: {e}")
#             import traceback
#             traceback.print_exc()
#             return False, f"驗證過程發生錯誤：{str(e)}"

#     def save(self, commit=True):
#         """保存診所和管理員資料"""
#         from django.contrib.auth.models import User
#         from django.db import transaction
#         from .models import VetClinic, VetDoctor, Profile
#         from django.utils import timezone
#         from datetime import datetime
        
#         cleaned_data = self.cleaned_data
        
        # 先進行農委會驗證
#         clinic_name = cleaned_data['clinic_name']
#         license_number = cleaned_data['license_number']
        
#         success, message = self.verify_with_moa_api(clinic_name, license_number)
#         if not success:
#             raise forms.ValidationError(f'農委會驗證失敗：{message}')
        
#         with transaction.atomic():
            # 建立診所實例
#             clinic = VetClinic(
#                 clinic_name=cleaned_data['clinic_name'],
#                 license_number=cleaned_data['license_number'],
#                 clinic_phone=cleaned_data['clinic_phone'],
#                 clinic_email=cleaned_data['clinic_email'],
#                 clinic_address=cleaned_data['clinic_address'],
#                 clinic_mode=cleaned_data['clinic_mode'],
#             )
            
            # 填入農委會驗證資料
#             if hasattr(self, 'moa_data'):
#                 moa_data = self.moa_data
#                 clinic.moa_county = moa_data.get('縣市', '')
#                 clinic.moa_status = moa_data.get('狀態', '')
#                 clinic.moa_responsible_vet = moa_data.get('負責獸醫', '')
                
                # 轉換發照日期
#                 issue_date_str = moa_data.get('發照日期', '')
#                 if issue_date_str and len(issue_date_str) == 8:
#                     try:
#                         clinic.moa_issue_date = datetime.strptime(issue_date_str, '%Y%m%d').date()
#                     except ValueError:
#                         pass
                
#                 clinic.is_verified = True
#                 clinic.verification_date = timezone.now()
            
#             clinic.save()
            
            # 建立管理員使用者
#             admin_user = User.objects.create_user(
#                 username=cleaned_data['admin_username'],
#                 email=cleaned_data['admin_email'],
#                 password=cleaned_data['admin_password'],
#                 first_name=cleaned_data['admin_real_name']
#             )
            
            # 建立使用者檔案
#             profile = Profile.objects.create(
#                 user=admin_user,
#                 account_type='clinic_admin',
#                 phone_number=cleaned_data['admin_phone']
#             )

#             clinic.clinic_admin = admin_user   
#             if commit:
#                 clinic.save()
            
            # 建立獸醫師檔案（診所管理員）
#             vet_doctor = VetDoctor.objects.create(
#                 user=admin_user,
#                 clinic=clinic,
#                 vet_license_number='',  
#                 is_active=True,
#                 is_clinic_admin=True, 
#                 is_active_veterinarian=False 
#             )

            
#             return clinic


# ===== 診所模式切換 =====
# ClinicModeSwitchForm 已註解停用 (2025-10-24)
# class ClinicModeSwitchForm(forms.ModelForm):
#     class Meta:
#         model = VetClinic
#         fields = ['clinic_mode']

#     def clean_clinic_mode(self):
#         mode = self.cleaned_data['clinic_mode']
#         if mode not in ['single', 'multi']:
#             raise forms.ValidationError("模式只能是 單一醫師 或 多醫師")
#         return mode

# ===== 獸醫師表單（已廢棄，由診所管理員統一管理） =====
# VetProfileEditForm 已註解停用 (2025-10-24)
# class VetProfileEditForm(forms.ModelForm):
#     """獸醫師檔案編輯表單 - 已廢棄，保留僅供相容性"""
    
#     class Meta:
#         model = VetDoctor
#         fields = []
    
#     def __init__(self, *args, **kwargs):
#         kwargs.pop('user', None)  # 移除不需要的參數
#         super().__init__(*args, **kwargs)
    
#     def save(self, commit=True):
        # 不執行任何操作，直接返回實例
#         return self.instance


# VetDoctorForm 已註解停用 (2025-10-24)
# class VetDoctorForm(forms.ModelForm):
#     """獸醫師新增表單"""
    
#     username = forms.CharField(
#         max_length=150, 
#         label='使用者帳號',
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '英文、數字或底線，3-30個字元'
#         }),
#         help_text='英文、數字或底線，3-30個字元'
#     )
#     email = forms.EmailField(
#         label='電子信箱',
#         widget=forms.EmailInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：doctor@example.com'
#         }),
#         help_text='將作為登入帳號和通知信箱'
#     )
#     password = forms.CharField(
#         widget=forms.PasswordInput(attrs={
#             'class': 'form-control',
#             'placeholder': '至少8個字元'
#         }), 
#         label='密碼',
#         min_length=8,
#         help_text='至少8個字元，建議包含大小寫字母、數字'
#     )
#     first_name = forms.CharField(
#         max_length=30, 
#         label='真實姓名',
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例：王小明'
#         }),
#         help_text='醫師的真實姓名'
#     )
#     phone_number = forms.CharField(
#         max_length=20, 
#         label='聯絡電話',
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control', 
#             'placeholder': '09xxxxxxxx'
#         }),
#         help_text='台灣手機號碼格式'
#     )
    
#     class Meta:
#         model = VetDoctor
#         fields = [
#             'vet_license_number', 'specialization', 'years_of_experience', 'bio',
#             'is_active_veterinarian', 'is_clinic_admin'
#         ]
#         labels = {
#             'vet_license_number': '獸醫師執照號碼',
#             'specialization': '專科領域',
#             'years_of_experience': '執業年資',
#             'bio': '個人簡介',
#             'is_active_veterinarian': '獸醫師功能',
#             'is_clinic_admin': '診所管理員權限',
#         }
#         widgets = {
#             'vet_license_number': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': '例：94府農畜字第13273號'
#             }),
#             'specialization': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': '例：小動物內科、外科、皮膚科'
#             }),
#             'years_of_experience': forms.NumberInput(attrs={
#                 'class': 'form-control', 
#                 'min': 0, 
#                 'max': 50,
#                 'placeholder': '0'
#             }),
#             'bio': forms.Textarea(attrs={
#                 'class': 'form-control', 
#                 'rows': 3,
#                 'placeholder': '可包含專業背景、治療理念、特殊專長等資訊'
#             }),
#         }
#         help_texts = {
#             'vet_license_number': '可稍後填寫，需通過農委會驗證後才能填寫醫療記錄',
#             'specialization': '例如：小動物內科、外科、皮膚科等',
#             'years_of_experience': '以年為單位',
#             'bio': '可包含專業背景、治療理念、特殊專長等',
#         }
    
#     def __init__(self, *args, **kwargs):
#         self.clinic = kwargs.pop('clinic', None)
#         super().__init__(*args, **kwargs)
        
        # 設定預設值
#         if not self.instance.pk:
#             self.fields['years_of_experience'].initial = 0
    
#     def clean_username(self):
#         username = self.cleaned_data['username']
        
        # 檢查格式
#         if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
#             raise forms.ValidationError('帳號只能包含英文、數字和底線，長度3-30個字元')
        
        # 檢查是否已存在
#         if User.objects.filter(username=username).exists():
#             raise forms.ValidationError('此使用者名稱已被使用')
        
#         return username
    
#     def clean_email(self):
#         email = self.cleaned_data['email']
        
        # 檢查是否已存在
#         if User.objects.filter(email=email).exists():
#             raise forms.ValidationError('此信箱已被註冊')
        
#         return email
    
#     def clean_phone_number(self):
#         phone = self.cleaned_data.get('phone_number')
#         if phone and not re.match(r'^09\d{8}$', phone):
#             raise forms.ValidationError('請輸入有效的台灣手機號碼（格式：09xxxxxxxx）')

        # 檢查電話號碼是否已被其他用戶使用
#         if phone:
#             existing_profile = Profile.objects.filter(phone_number=phone).first()
#             if existing_profile:
#                 raise forms.ValidationError("這支電話號碼已被使用，請使用其他號碼")

#         return phone
    
#     def clean_years_of_experience(self):
#         years = self.cleaned_data.get('years_of_experience')
#         if years is not None and (years < 0 or years > 50):
#             raise forms.ValidationError('執業年資應在0-50年之間')
#         return years
    
#     def clean_password(self):
#         password = self.cleaned_data.get('password')
        
#         if len(password) < 8:
#             raise forms.ValidationError('密碼至少需要8個字元')
        
#         return password

# ===== 獸醫師執照驗證表單 =====
# LicenseVerificationForm 已註解停用 (2025-10-24)
# class LicenseVerificationForm(forms.Form):
#     """
#     執照驗證表單 - 獨立處理執照驗證邏輯
#     """
#     vet_license_number = forms.CharField(
#         label='獸醫師執照號碼',
#         max_length=50,
#         required=True,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '請輸入完整執照號碼，例如：94府農畜字第13273號'
#         })
#     )
    
#     def __init__(self, *args, **kwargs):
#         self.doctor = kwargs.pop('doctor', None)
#         super().__init__(*args, **kwargs)
        
#         if self.doctor and self.doctor.vet_license_number:
#             self.fields['vet_license_number'].initial = self.doctor.vet_license_number
    
#     def clean_vet_license_number(self):
#         """驗證執照號碼"""
#         license_number = self.cleaned_data.get('vet_license_number')
        
#         if not license_number:
#             raise forms.ValidationError('請輸入執照號碼')
        
        # 檢查是否已被其他醫師驗證使用
#         existing_doctor = VetDoctor.objects.filter(
#             vet_license_number=license_number,
#             license_verified_with_moa=True
#         )
        
#         if self.doctor:
#             existing_doctor = existing_doctor.exclude(pk=self.doctor.pk)
        
#         if existing_doctor.exists():
#             doctor = existing_doctor.first()
#             raise forms.ValidationError(
#                 f'此執照號碼已被 {doctor.user.get_full_name()} 驗證使用'
#             )
        
#         return license_number


# ===== 編輯醫師表單 =====
# EditDoctorForm 已註解停用 (2025-10-24)
# class EditDoctorForm(forms.ModelForm):
#     """
#     編輯醫師表單 - 簡化版本，專注核心功能
#     分離關注點：基本資料 vs 權限管理
#     """
    
    # 基本個人資料
#     first_name = forms.CharField(
#         label='醫師姓名',
#         max_length=30,
#         required=True,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '請輸入醫師真實姓名'
#         })
#     )
    
#     email = forms.EmailField(
#         label='電子郵件',
#         required=True,
#         widget=forms.EmailInput(attrs={
#             'class': 'form-control',
#             'placeholder': '用於登入和接收通知'
#         })
#     )
    
#     phone_number = forms.CharField(
#         label='聯絡電話',
#         max_length=20,
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '09xxxxxxxx'
#         })
#     )
    
    # 專業資訊
#     specialization = forms.CharField(
#         label='專科領域',
#         max_length=100,
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '例如：小動物內科、外科、皮膚科'
#         })
#     )
    
#     years_of_experience = forms.IntegerField(
#         label='執業年資',
#         min_value=0,
#         max_value=50,
#         required=False,
#         widget=forms.NumberInput(attrs={
#             'class': 'form-control',
#             'placeholder': '0'
#         })
#     )
    
#     bio = forms.CharField(
#         label='個人簡介',
#         required=False,
#         widget=forms.Textarea(attrs={
#             'class': 'form-control',
#             'rows': 4,
#             'maxlength': 500,
#             'placeholder': '醫師的專業背景和治療理念介紹'
#         })
#     )
    
    # 權限設定 - 簡化為核心權限
#     can_manage_appointments = forms.BooleanField(
#         label='預約管理權限',
#         required=False,
#         initial=True,
#         widget=forms.CheckboxInput(attrs={
#             'class': 'form-check-input'
#         })
#     )
    
#     is_clinic_admin = forms.BooleanField(
#         label='診所管理員權限',
#         required=False,
#         widget=forms.CheckboxInput(attrs={
#             'class': 'form-check-input'
#         })
#     )
    
    # 帳號狀態
#     is_active = forms.BooleanField(
#         label='帳號啟用',
#         required=False,
#         widget=forms.CheckboxInput(attrs={
#             'class': 'form-check-input'
#         })
#     )

#     class Meta:
#         model = VetDoctor
#         fields = [
#             'specialization', 'years_of_experience', 'bio',
#             'can_manage_appointments', 'is_clinic_admin', 'is_active'
#         ]

#     def __init__(self, *args, **kwargs):
#         self.user = kwargs.pop('user', None)  # 當前操作用戶
#         super().__init__(*args, **kwargs)
        
        # 如果有實例，填充用戶相關欄位
#         if self.instance and self.instance.pk:
#             self.fields['first_name'].initial = self.instance.user.first_name
#             self.fields['email'].initial = self.instance.user.email
            
            # 從 Profile 獲取電話
#             try:
#                 profile = self.instance.user.profile
#                 self.fields['phone_number'].initial = profile.phone_number
#             except:
#                 pass
    
#     def clean_email(self):
#         """驗證 email 唯一性"""
#         email = self.cleaned_data.get('email')
#         if not email:
#             return email
            
        # 檢查是否被其他用戶使用（排除當前用戶）
#         existing_user = User.objects.filter(email=email).first()
#         if existing_user and existing_user != self.instance.user:
#             raise forms.ValidationError('此信箱已被其他用戶使用')
        
#         return email
    
#     def clean_phone_number(self):
#         """驗證手機號碼格式"""
#         phone = self.cleaned_data.get('phone_number')
#         if phone and not re.match(r'^09\d{8}$', phone):
#             raise forms.ValidationError('請輸入有效的台灣手機號碼（格式：09xxxxxxxx）')

        # 檢查電話號碼是否已被其他用戶使用（排除當前用戶）
#         if phone and self.instance and self.instance.user:
#             existing_profile = Profile.objects.filter(phone_number=phone).exclude(user=self.instance.user).first()
#             if existing_profile:
#                 raise forms.ValidationError("這支電話號碼已被使用，請使用其他號碼")

#         return phone
    
#     def clean_years_of_experience(self):
#         """驗證執業年資"""
#         years = self.cleaned_data.get('years_of_experience')
#         if years is not None and (years < 0 or years > 50):
#             raise forms.ValidationError('執業年資應在0-50年之間')
#         return years
    
#     def clean_is_clinic_admin(self):
#         """管理員權限驗證"""
#         is_admin = self.cleaned_data.get('is_clinic_admin', False)
        
        # 檢查當前用戶是否有權限設置管理員
#         if is_admin and self.user:
#             if not (self.user.vet_profile.is_clinic_admin or self.user.is_superuser):
#                 raise forms.ValidationError('只有管理員可以設置其他管理員')
        
#         return is_admin
    
#     def clean(self):
#         """整體表單驗證"""
#         cleaned_data = super().clean()
        
        # 確保至少有一個管理員
#         if not cleaned_data.get('is_clinic_admin', False):
            # 檢查診所是否還有其他管理員
#             clinic = self.instance.clinic
#             other_admins = VetDoctor.objects.filter(
#                 clinic=clinic,
#                 is_clinic_admin=True,
#                 is_active=True
#             ).exclude(pk=self.instance.pk)
            
#             if not other_admins.exists():
                # 如果這是最後一個管理員，不能取消管理員權限
#                 if self.instance.is_clinic_admin:
#                     self.add_error('is_clinic_admin', '診所必須至少有一位管理員')
        
#         return cleaned_data
    
#     def save(self, commit=True):
#         """保存表單數據"""
        # 保存 VetDoctor 實例
#         doctor = super().save(commit=False)
        
#         if commit:
            # 更新用戶基本資料
#             user = doctor.user
#             user.first_name = self.cleaned_data['first_name']
#             user.email = self.cleaned_data['email']
#             user.save()
            
            # 更新或創建 Profile
#             profile, created = Profile.objects.get_or_create(user=user)
#             phone_number = self.cleaned_data.get('phone_number', '')
#             if phone_number:
#                 profile, created = Profile.objects.get_or_create(
#                     user=doctor.user,
#                     defaults={'account_type': 'vet'}
#                 )
#                 profile.phone_number = phone_number
#                 profile.save()

#             profile.save()
            
            # 保存醫師資料
#             doctor.save()
        
#         return doctor

class PasswordResetForm(forms.Form):
    """
    密碼重設表單 - 獨立處理密碼重設邏輯
    """
    email = forms.EmailField(
        label='確認信箱地址',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': True
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        
        if self.doctor:
            self.fields['email'].initial = self.doctor.user.email


# ===== 獸醫師排班表單 =====
# VetScheduleForm 已註解停用 (2025-10-24)
# class VetScheduleForm(forms.ModelForm):
#     """獸醫師排班表單"""
    
#     class Meta:
#         model = VetSchedule
#         fields = [
#             'weekday', 'start_time', 'end_time', 
#             'appointment_duration', 'max_appointments_per_slot', 'notes'
#         ]
#         labels = {
#             'weekday': '星期',
#             'start_time': '開始時間',
#             'end_time': '結束時間',
#             'appointment_duration': '預約時長（分鐘）',
#             'max_appointments_per_slot': '每時段最大預約數',
#             'notes': '備註'
#         }
#         widgets = {
#             'weekday': forms.Select(choices=WEEKDAYS, attrs={'class': 'form-control'}),
#             'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
#             'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
#             'appointment_duration': forms.Select(choices=[
#                 (15, '15分鐘'), (20, '20分鐘'), (30, '30分鐘'), 
#                 (45, '45分鐘'), (60, '60分鐘')
#             ], attrs={'class': 'form-control'}),
#             'max_appointments_per_slot': forms.NumberInput(attrs={
#                 'class': 'form-control', 'min': 1, 'max': 5
#             }),
#             'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
#         }
    
#     def __init__(self, *args, **kwargs):
#         self.doctor = kwargs.pop('doctor', None)
#         super().__init__(*args, **kwargs)
        
        # 確保weekday字段有正確的choices
#         self.fields['weekday'].choices = WEEKDAYS
        
        # 設定預設值
#         if not self.instance.pk:
#             self.fields['appointment_duration'].initial = 30
#             self.fields['max_appointments_per_slot'].initial = 1
    
#     def clean(self):
#         cleaned_data = super().clean()
#         start_time = cleaned_data.get('start_time')
#         end_time = cleaned_data.get('end_time')
#         weekday = cleaned_data.get('weekday')
        
#         if start_time and end_time:
#             if start_time >= end_time:
#                 raise forms.ValidationError('結束時間必須晚於開始時間')
            
            # 檢查時間重疊
#             if self.doctor:
#                 overlapping = VetSchedule.objects.filter(
#                     doctor=self.doctor,
#                     weekday=weekday,
#                     is_active=True
#                 ).exclude(pk=self.instance.pk if self.instance else None)
                
#                 for schedule in overlapping:
#                     if (start_time < schedule.end_time and end_time > schedule.start_time):
#                         raise forms.ValidationError(
#                             f'與現有排班時間重疊：{schedule.start_time.strftime("%H:%M")}-{schedule.end_time.strftime("%H:%M")}'
#                         )
        
#         return cleaned_data


# ===== 飼主預約表單 =====
# AppointmentBookingForm 已註解停用 (2025-10-24)
# class AppointmentBookingForm(forms.Form):
#     """飼主預約表單 - 診所→醫師→時段流程"""
    
    # 診所搜索
#     search_clinic = forms.CharField(
#         label='搜索診所',
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '輸入診所名稱或地址搜索...',
#             'id': 'clinic-search'
#         })
#     )
    
#     clinic = forms.ModelChoiceField(
#         queryset=VetClinic.objects.filter(is_verified=True).order_by('clinic_name'),
#         label='選擇診所',
#         widget=forms.Select(attrs={
#             'class': 'form-control',
#             'onchange': 'loadDoctors(this.value)'
#         }),
#         empty_label='請選擇診所'
#     )
    
#     doctor = forms.ModelChoiceField(
#         queryset=VetDoctor.objects.none(),
#         label='選擇醫師',
#         required=False,
#         widget=forms.Select(attrs={
#             'class': 'form-control',
#             'onchange': 'loadAvailableSlots()'
#         }),
#         empty_label='任何醫師'
#     )
    
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
        # 更新診所的widget屬性，添加搜索功能
#         self.fields['clinic'].widget.attrs.update({
#             'class': 'form-control searchable-select',
#             'data-live-search': 'true',
#             'data-size': '8'
#         })
        # 預設顯示前30個診所，格式為 "名稱 (地址)"
#         clinics = VetClinic.objects.filter(is_verified=True).order_by('clinic_name')[:30]
#         self.fields['clinic'].queryset = clinics
        # 自定義選項顯示
#         self.fields['clinic'].choices = [('', '請選擇診所')] + [
#             (clinic.id, f"{clinic.clinic_name} ({clinic.clinic_address})")
#             for clinic in clinics
#         ]
    
#     appointment_date = forms.DateField(
#         label='預約日期',
#         widget=forms.DateInput(attrs={
#             'type': 'date',
#             'class': 'form-control',
#             'min': (date.today() + timedelta(days=1)).isoformat(),
#             'onchange': 'loadAvailableSlots()'
#         })
#     )
    
#     time_slot = forms.ModelChoiceField(
#         queryset=AppointmentSlot.objects.none(),
#         label='預約時段',
#         widget=forms.Select(attrs={'class': 'form-control'}),
#         empty_label='請先選擇日期'
#     )
    
#     reason = forms.CharField(
#         label='預約原因',
#         widget=forms.Textarea(attrs={
#             'class': 'form-control',
#             'rows': 3,
#             'placeholder': '請簡述預約原因，如：定期健檢、疫苗接種、身體不適等'
#         }),
#         max_length=500,
#         required=False
#     )
    
#     notes = forms.CharField(
#         label='備註',
#         widget=forms.Textarea(attrs={
#             'class': 'form-control',
#             'rows': 2,
#             'placeholder': '其他需要診所知道的資訊'
#         }),
#         max_length=300,
#         required=False
#     )
    
    # 聯絡資訊
#     contact_phone = forms.CharField(
#         label='聯絡電話',
#         max_length=20,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '09xxxxxxxx'
#         }),
#         help_text='如需變更預約時的聯絡電話'
#     )
    
#     def __init__(self, *args, **kwargs):
        # 處理自定義參數
#         self.pet = kwargs.pop('pet', None)
#         self.user = kwargs.pop('user', None)
#         super().__init__(*args, **kwargs)
        
        # 設定預設聯絡電話
#         if self.user and hasattr(self.user, 'profile') and self.user.profile.phone_number:
#             self.fields['contact_phone'].initial = self.user.profile.phone_number
        
        # 動態載入醫師選項
#         if 'clinic' in self.data:
#             try:
#                 clinic_id = int(self.data.get('clinic'))
#                 self.fields['doctor'].queryset = VetDoctor.objects.filter(
#                     clinic_id=clinic_id, is_active=True
#                 ).order_by('user__first_name')
#             except (ValueError, TypeError):
#                 pass
        
        # 動態載入時段選項
#         if all(k in self.data for k in ['clinic', 'appointment_date']):
#             try:
#                 clinic_id = int(self.data.get('clinic'))
#                 appointment_date = datetime.strptime(self.data.get('appointment_date'), '%Y-%m-%d').date()
#                 doctor_id = self.data.get('doctor')
                
#                 slots_query = AppointmentSlot.objects.filter(
#                     clinic_id=clinic_id,
#                     date=appointment_date,
#                     is_available=True
#                 ).filter(current_bookings__lt=models.F('max_bookings'))
                
#                 if doctor_id:
#                     slots_query = slots_query.filter(doctor_id=doctor_id)
                
#                 self.fields['time_slot'].queryset = slots_query.order_by('start_time')
                
#             except (ValueError, TypeError):
#                 pass
    
#     def clean_contact_phone(self):
#         phone = self.cleaned_data.get('contact_phone')
#         if phone and not re.match(r'^09\d{8}$', phone):
#             raise ValidationError('請輸入有效的台灣手機號碼（格式：09xxxxxxxx）')
#         return phone
    
#     def clean_appointment_date(self):
#         appointment_date = self.cleaned_data['appointment_date']
        
        # 不能預約今天或過去的日期
#         if appointment_date <= date.today():
#             raise ValidationError('預約日期必須是明天以後')
        
        # 不能預約太遠的未來（例如60天後）
#         max_future_date = date.today() + timedelta(days=60)
#         if appointment_date > max_future_date:
#             raise ValidationError('預約日期不能超過60天後')
        
#         return appointment_date
    
#     def clean(self):
#         cleaned_data = super().clean()
#         clinic = cleaned_data.get('clinic')
#         doctor = cleaned_data.get('doctor')
#         appointment_date = cleaned_data.get('appointment_date')
#         time_slot = cleaned_data.get('time_slot')
        
#         if time_slot:
            # 驗證時段是否仍可預約
#             if not time_slot.can_book():
#                 raise ValidationError('此時段已被預約，請重新選擇')
            
            # 如果指定了醫師，確認時段屬於該醫師
#             if doctor and time_slot.doctor != doctor:
#                 raise ValidationError('所選時段不屬於指定醫師')
            
            # 驗證時段日期
#             if time_slot.date != appointment_date:
#                 raise ValidationError('時段日期不符')
            
            # 檢查該用戶在同一時段是否已有預約
#             if self.user:
#                 existing_appointment = VetAppointment.objects.filter(
#                     owner=self.user,
#                     slot=time_slot,
#                     status__in=['pending', 'confirmed']
#                 ).exists()
                
#                 if existing_appointment:
#                     raise ValidationError('您在此時段已有預約')
        
#         return cleaned_data

# ===== 飼主註冊表單 =====
class CustomSignupForm(SignupForm):
    """飼主註冊表單（僅支援飼主註冊，獸醫院另外註冊）"""
    
    phone_number = forms.CharField(max_length=20, label="手機號碼", required=True)
    last_name = forms.CharField(label="姓氏", max_length=30, required=False)
    first_name = forms.CharField(label="名字", max_length=30, required=False)

    def clean_email(self):
        """驗證電子信箱是否已被使用"""
        email = self.cleaned_data.get('email')

        # 檢查電子信箱是否已被註冊
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("此電子信箱已被註冊，請使用其他信箱或直接登入")

        return email

    def clean_phone_number(self):
        """驗證手機號碼格式與是否已被使用"""
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")

        # 檢查電話號碼是否已被其他用戶使用
        existing_profile = Profile.objects.filter(phone_number=phone).first()
        if existing_profile:
            raise forms.ValidationError("這支電話號碼已被使用，請使用其他號碼")

        return phone

    def save(self, request):
        user = super().save(request)
        phone_number = self.cleaned_data['phone_number']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']

        # 建立飼主 Profile
        profile = Profile.objects.create(
            user=user,
            account_type='owner',  # 統一為飼主
            phone_number=phone_number,
        )

        user.first_name = first_name
        user.last_name = last_name
        user.save()

        # 移除自動登入,讓 allauth 的 email 驗證流程正常運作
        # 使用者必須先驗證 email 才能登入
        return user

# ===== Google 註冊後補資料表單 =====
class SocialSignupExtraForm(forms.Form):
    """Google 註冊後補資料表單 - 簡化版（只註冊飼主）"""
    
    username = forms.CharField(
        label='使用者名稱', 
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入使用者名稱'
        })
    )
    
    phone_number = forms.CharField(
        label='手機號碼',
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：0912345678'
        })
    )

    password1 = forms.CharField(
        label='設定密碼（可選）',
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '設定登入密碼（8位以上）'
        }),
        help_text='如果您想要使用密碼登入，請設定密碼。如果留空，將只能使用 Google 登入。'
    )

    password2 = forms.CharField(
        label='確認密碼',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '再次輸入密碼確認'
        })
    )

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        # 如果其中一個有值，則兩個都必須有值且相同
        if password1 or password2:
            if not password1:
                raise forms.ValidationError('請輸入密碼')
            if not password2:
                raise forms.ValidationError('請確認密碼')
            if password1 != password2:
                raise forms.ValidationError('兩次輸入的密碼不一致')

        return password2

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")

        # 檢查電話號碼是否已被其他用戶使用（排除當前用戶）
        if self.current_user:
            existing_profile = Profile.objects.filter(phone_number=phone).exclude(user=self.current_user).first()
            if existing_profile:
                raise forms.ValidationError("這支電話號碼已被使用，請使用其他號碼")

        return phone

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        # 檢查是否與其他用戶衝突（排除當前用戶）
        existing_users = User.objects.filter(username=username)
        if self.current_user:
            existing_users = existing_users.exclude(id=self.current_user.id)
            
        if existing_users.exists():
            # 生成建議的替代用戶名
            suggestions = []
            base_username = username
            for i in range(1, 6):  # 生成5個建議
                suggested = f"{base_username}{i}"
                check_users = User.objects.filter(username=suggested)
                if self.current_user:
                    check_users = check_users.exclude(id=self.current_user.id)
                if not check_users.exists():
                    suggestions.append(suggested)
            
            if suggestions:
                suggestion_text = "、".join(suggestions[:3])  # 顯示前3個建議
                raise forms.ValidationError(f"此使用者名稱已被使用。建議使用：{suggestion_text}")
            else:
                raise forms.ValidationError("此使用者名稱已被使用，請嘗試其他名稱")
        return username

# ===== 編輯個人資料用表單 =====
class EditProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, label='使用者名稱')
    first_name = forms.CharField(max_length=30, label='名字', required=False)
    last_name = forms.CharField(max_length=30, label='姓氏', required=False)

    class Meta:
        model = Profile
        fields = ['phone_number']
        labels = {
            'phone_number': '手機號碼',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name

            # 初始化手機號碼，優先從 Profile 獲取，如果沒有再從 VetDoctor 獲取
            if hasattr(self.user, 'profile') and self.user.profile.phone_number:
                self.fields['phone_number'].initial = self.user.profile.phone_number
            elif hasattr(self.user, 'vet_profile') and hasattr(self.user.vet_profile, 'user') and hasattr(self.user.vet_profile.user, 'profile'):
                # 對於獸醫師用戶，從 VetDoctor 關聯的 Profile 獲取手機號碼
                vet_profile = self.user.vet_profile.user.profile
                if vet_profile.phone_number:
                    self.fields['phone_number'].initial = vet_profile.phone_number

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            if not re.match(r'^09\d{8}$', phone):
                raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")

            # 檢查手機號碼是否已被其他用戶使用
            existing_profile = Profile.objects.filter(phone_number=phone).exclude(user=self.user).first()
            if existing_profile:
                raise forms.ValidationError("此手機號碼已被其他用戶使用")
        return phone

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            if self.user:
                self.user.username = self.cleaned_data['username']
                self.user.first_name = self.cleaned_data['first_name']
                self.user.last_name = self.cleaned_data['last_name']
                self.user.save()
        return profile

# ===== 寵物資料管理用表單 =====
class PetForm(forms.ModelForm):
    # 自定義種類欄位 
    species = forms.ChoiceField(
        choices=SPECIES_CHOICES,
        label='種類',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # 自定義品種欄位，初始為空，會根據種類動態更新
    breed = forms.ChoiceField(
        choices=[],
        label='品種',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # 自定義品種文字輸入欄位（當選擇"其他"時顯示）
    breed_other = forms.CharField(
        max_length=50,
        required=False,
        label='請輸入品種',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入具體品種名稱'
        })
    )
    
    class Meta:
        model = Pet
        fields = [
            'species', 'breed', 'breed_other', 'name', 'sterilization_status', 'chip',
            'gender', 'weight', 'feature', 'picture', 'birth_date',
        ]
        labels = {
            'name': '名字', 'sterilization_status': '絕育狀態', 'chip': '晶片號碼',
            'gender': '性別', 'weight': '體重（公斤）', 'feature': '特徵',
            'picture': '圖片', 'birth_date': '出生日期',
        }
        widgets = {
            'name': forms.TextInput(attrs={'maxlength': 50}),
            'chip': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '15', 'placeholder': '請輸入15位數晶片號碼'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'feature': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        
        # 根據種類設置品種選項
        if self.instance and self.instance.pk:
            # 編輯模式：根據現有的種類設置品種選項
            species_value = self.instance.species
            
            # 檢查是否為自定義品種（不在預定義選項中）
            breed_choices = self.get_breed_choices_for_species(species_value)
            breed_values = [choice[0] for choice in breed_choices]
            
            if self.instance.breed not in breed_values:
                # 如果是自定義品種，設置breed_other欄位並將breed設為"其他"
                self.fields['breed_other'].initial = self.instance.breed
        else:
            # 新增模式：取得POST或初始數據中的種類
            species_value = self.data.get('species') if self.data else self.initial.get('species', 'dog')
        
        self.set_breed_choices(species_value)
        
        self.fields['picture'].required = True
        for field_name in ['breed', 'name', 'chip', 'weight', 'feature','birth_date']:
            self.fields[field_name].required = True
        if not self.initial.get('date'):
            self.initial['date'] = date.today()
    
    def get_breed_choices_for_species(self, species):
        """根據種類獲取品種選項"""
        if species == 'dog':
            return DOG_CHOICES
        elif species == 'cat':
            return CAT_CHOICES
        elif species == 'other':
            return OTHER_CHOICES
        else:
            return DOG_CHOICES
    
    def set_breed_choices(self, species):
        """根據種類設置品種選項"""
        self.fields['breed'].choices = self.get_breed_choices_for_species(species)

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is None or weight <= 0 or weight > 1000:
            raise forms.ValidationError("請輸入合理的體重")
        return weight

    def clean_birth_date(self):
        record_date = self.cleaned_data.get('birth_date')
        if record_date and record_date > date.today():
            raise forms.ValidationError("日期不能是未來")
        return record_date

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # 移除重複名字檢查，允許用戶新增多隻寵物，即使名字相同
            pass
        if len(name) > 20:
            raise forms.ValidationError("名字最多只能輸入 50 個字元。")
        return name

    def clean(self):
        cleaned_data = super().clean()
        breed = cleaned_data.get('breed')
        breed_other = cleaned_data.get('breed_other')
        
        # 如果品種選擇"其他"，則需要填寫breed_other
        if breed == '其他' and not breed_other:
            raise forms.ValidationError({'breed_other': '當品種選擇"其他"時，請輸入具體品種名稱'})
        
        # 如果選擇"其他"，將breed_other的值存入breed欄位
        if breed == '其他' and breed_other:
            cleaned_data['breed'] = breed_other
        
        return cleaned_data

    def clean_breed(self):
        breed = self.cleaned_data.get('breed')
        if breed and len(breed) > 50:
            raise forms.ValidationError("品種最多只能輸入 50 個字元。")
        return breed

    def clean_chip(self):
        chip = self.cleaned_data.get('chip')
        if chip:
            # 檢查晶片號碼是否已被其他寵物使用
            existing_pet = Pet.objects.filter(chip=chip)
            if self.instance.pk:
                existing_pet = existing_pet.exclude(pk=self.instance.pk)
            if existing_pet.exists():
                raise forms.ValidationError("此晶片號碼已被其他寵物使用")
        return chip

# ===== 健康紀錄輸入表單 =====
class DailyRecordForm(forms.ModelForm):
    class Meta:
        model = DailyRecord
        fields = ['date', 'category', 'content', 'temperature', 'weight', 'medication_dosage', 'exercise_duration']
        labels = {
            'date': '日期', 
            'category': '類別', 
            'content': '記錄內容',
            'temperature': '體溫 (°C)',
            'weight': '體重 (kg)',
            'medication_dosage': '藥物劑量',
            'exercise_duration': '運動時長 (分鐘)'
        }
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }, format='%Y-%m-%d'),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'onchange': 'toggleFields(this.value)'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '輸入詳細記錄內容...'
            }),
            'temperature': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '35.0',
                'max': '45.0',
                'placeholder': '例：38.5'
            }),
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.1',
                'max': '100.0',
                'placeholder': '例：5.2'
            }),
            'medication_dosage': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例：每日2次，每次1錠'
            }),
            'exercise_duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '720',
                'placeholder': '例：30'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('date'):
            self.initial['date'] = date.today()
            
        # 設置字段為非必填（根據分類動態顯示）
        self.fields['content'].required = False
        self.fields['temperature'].required = False
        self.fields['weight'].required = False
        self.fields['medication_dosage'].required = False
        self.fields['exercise_duration'].required = False

    def clean_date(self):
        record_date = self.cleaned_data.get('date')
        if record_date and record_date > date.today():
            raise forms.ValidationError("日期不能是未來")
        return record_date
    
    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        content = cleaned_data.get('content')
        temperature = cleaned_data.get('temperature')
        weight = cleaned_data.get('weight')
        medication_dosage = cleaned_data.get('medication_dosage')
        exercise_duration = cleaned_data.get('exercise_duration')
        
        # 健康數據類：只需要數值，用於趨勢圖分析
        if category == 'temperature':
            if not temperature:
                raise ValidationError({'temperature': '請輸入體溫數值'})
            # 清空content，因為健康數據不需要文字說明
            cleaned_data['content'] = ''
        elif category == 'weight':
            if not weight:
                raise ValidationError({'weight': '請輸入體重數值'})
            # 清空content，因為健康數據不需要文字說明
            cleaned_data['content'] = ''
        elif category == 'exercise':
            if not exercise_duration:
                raise ValidationError({'exercise_duration': '請輸入運動時長'})
            # 清空content，因為健康數據不需要文字說明
            cleaned_data['content'] = ''
        
        # 生活筆記類：只需要內容記錄
        else:
            if not content:
                if category == 'medication':
                    if not medication_dosage:
                        raise ValidationError({'content': '請輸入用藥記錄內容'})
                else:
                    raise ValidationError({'content': '請輸入記錄內容'})
        
        return cleaned_data


# ===== 體溫編輯表單 =====
class TemperatureEditForm(forms.Form):
    date = forms.DateField(label='紀錄時間',
        widget=forms.DateInput(attrs={'type': 'date'}),input_formats=['%Y-%m-%d'])
    temperature = forms.FloatField(label='體溫 (°C)')
    
    def clean_date(self):
        selected_date = self.cleaned_data['date']
        if selected_date > date.today():
            raise forms.ValidationError("日期不能超過今天")
        return selected_date

# ===== 體重編輯表單 =====
class WeightEditForm(forms.Form):
    date = forms.DateField(label='紀錄時間',
            widget=forms.DateInput(attrs={'type': 'date'}),input_formats=['%Y-%m-%d'])
    weight = forms.FloatField(label='體重 (公斤)')
    def clean_date(self):
        selected_date = self.cleaned_data['date']
        if selected_date > date.today():
            raise forms.ValidationError("日期不能超過今天")
        return selected_date

# ===== 疫苗表單 - 飼主輸入版本 =====
class VaccineRecordForm(forms.ModelForm):
    class Meta:
        model = VaccineRecord
        fields = ['name', 'date', 'location', 'protection_period_months', 'next_due_date']
        labels = {
            'name':'疫苗品牌',
            'date':'施打日期',
            'location':'施打地點',
            'protection_period_months': '保護效期（月）',
            'next_due_date': '下次接種日期'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：狂犬病疫苗'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：XX動物醫院'}),
            'date': forms.DateInput(attrs={'type': 'date','class': 'form-control',
                                           'max': date.today().isoformat(),
                                           'value': date.today().isoformat()
            },format='%Y-%m-%d'),
            'next_due_date': forms.DateInput(attrs={'type': 'date','class': 'form-control'}, format='%Y-%m-%d'),
            'protection_period_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '120', 'placeholder': '例：12'})
        }

    def clean_date(self):
        vaccination_date = self.cleaned_data['date']
        if vaccination_date > date.today():
            raise forms.ValidationError("疫苗接種日期不能是未來")
        return vaccination_date

# ===== 驅蟲表單 - 飼主輸入版本 =====
class DewormRecordForm(forms.ModelForm):
    class Meta:
        model = DewormRecord
        fields = ['name', 'date', 'location', 'protection_period_months', 'next_due_date']
        labels = {
            'name':'驅蟲品牌',
            'date':'施打日期',
            'location':'施打地點',
            'protection_period_months': '保護效期（月）',
            'next_due_date': '下次施打日期'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：心絲蟲藥'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：XX動物醫院'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control',
                                           'max': date.today().isoformat(),
                                           'value': date.today().isoformat()
                }, format='%Y-%m-%d'),
            'next_due_date': forms.DateInput(attrs={'type': 'date','class': 'form-control'}, format='%Y-%m-%d'),
            'protection_period_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '120', 'placeholder': '例：3'})
        }

    def clean_date(self):
        deworm_date = self.cleaned_data['date']
        if deworm_date > date.today():
            raise forms.ValidationError("驅蟲日期不能是未來")
        return deworm_date

# ===== 報告表單 =====
class ReportForm(forms.ModelForm):
    """寵物檢驗報告表單 - 飼主專用"""

    class Meta:
        model = Report
        fields = ['title', 'report_type', 'report_date', 'clinic_name', 'pdf']
        labels = {
            'title': '報告標題',
            'report_type': '報告類型',
            'report_date': '檢驗日期',
            'clinic_name': '醫院/診所名稱',
            'pdf': 'PDF檔案'
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如：2025年血液檢查報告'
            }),
            'report_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'report_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': date.today().isoformat()
            }, format='%Y-%m-%d'),
            'clinic_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如：XX動物醫院'
            }),
            'pdf': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf'
            }),
        }

    def clean_pdf(self):
        pdf_file = self.cleaned_data.get('pdf')
        if pdf_file:
            # 檢查副檔名
            if not pdf_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError('請上傳 PDF 格式的檔案。')
            # 檢查 MIME 類型（支援多種 PDF MIME 類型）
            allowed_types = ['application/pdf', 'application/x-pdf', 'application/acrobat',
                           'applications/vnd.pdf', 'text/pdf', 'text/x-pdf']
            if pdf_file.content_type and pdf_file.content_type not in allowed_types:
                raise forms.ValidationError(f'檔案格式無效，請確認為 PDF 檔案。（偵測到的類型：{pdf_file.content_type}）')
            # 檢查檔案大小（上限：10MB）
            max_size = 10 * 1024 * 1024  # 10MB
            if pdf_file.size > max_size:
                raise forms.ValidationError('檔案太大，請上傳小於 10MB 的 PDF 檔案。')
        return pdf_file

# ===== 看診記錄表單 - 飼主輸入版本 =====
class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = [
            'visit_date', 'clinic_location', 'diagnosis', 'treatment',
            'notes', 'total_cost', 'follow_up_required', 'follow_up_date'
        ]
        labels = {
            'visit_date': '看診日期',
            'clinic_location': '看診地點',
            'diagnosis': '診斷結果',
            'treatment': '治療內容',
            'notes': '備註',
            'total_cost': '費用',
            'follow_up_required': '需要追蹤',
            'follow_up_date': '追蹤日期'
        }
        widgets = {
            'visit_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': date.today().isoformat(),
                'value': date.today().isoformat()
            }, format='%Y-%m-%d'),
            'clinic_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例：XX動物醫院'
            }),
            'diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '請輸入獸醫師的診斷結果'
            }),
            'treatment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '請輸入治療內容或處方藥物'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '其他備註或醫囑'
            }),
            'total_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'placeholder': '例：1500'
            }),
            'follow_up_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }, format='%Y-%m-%d'),
        }

# ===== 獸醫預約管理表單 =====
# VetAppointmentForm 已註解停用 (2025-10-24)
# class VetAppointmentForm(forms.ModelForm):
#     """獸醫師建立預約表單"""
    
#     class Meta:
#         model = VetAppointment
#         fields = ['pet', 'slot', 'reason', 'notes', 'contact_phone', 'status']
#         labels = {
#             'pet': '寵物',
#             'slot': '時段',
#             'reason': '預約原因',
#             'notes': '備註',
#             'contact_phone': '聯絡電話',
#             'status': '狀態'
#         }
#         widgets = {
#             'pet': forms.Select(attrs={'class': 'form-control'}),
#             'slot': forms.Select(attrs={'class': 'form-control'}),
#             'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#             'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
#             'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
#             'status': forms.Select(attrs={'class': 'form-control'}),
#         }

# ===== 獸醫可看診時間表單 =====
# VetAvailableTimeForm 已註解停用 (2025-10-24)
# class VetAvailableTimeForm(forms.ModelForm):
#     """獸醫師可看診時間設定表單"""
    
#     class Meta:
#         model = VetSchedule  # 使用 VetSchedule 模型
#         fields = ['weekday', 'start_time', 'end_time', 'appointment_duration', 'notes']
#         labels = {
#             'weekday': '星期',
#             'start_time': '開始時間',
#             'end_time': '結束時間',
#             'appointment_duration': '預約時長（分鐘）',
#             'notes': '備註'
#         }
#         widgets = {
#             'weekday': forms.Select(choices=WEEKDAYS, attrs={'class': 'form-control'}),
#             'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
#             'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
#             'appointment_duration': forms.Select(choices=[
#                 (15, '15分鐘'), (20, '20分鐘'), (30, '30分鐘'),
#                 (45, '45分鐘'), (60, '60分鐘')
#             ], attrs={'class': 'form-control'}),
#             'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
#         }

# ===== 診所設定表單 =====
# ClinicSettingsForm 已註解停用 (2025-10-24)
# class ClinicSettingsForm(forms.ModelForm):
#     """診所基本設定表單"""
    
#     class Meta:
#         model = VetClinic
#         fields = [
#             'clinic_name', 'clinic_phone', 'clinic_email', 'clinic_address',
#             'default_appointment_duration', 'advance_booking_days'
#         ]
#         labels = {
#             'clinic_name': '診所名稱',
#             'clinic_phone': '診所電話',
#             'clinic_email': '診所信箱',
#             'clinic_address': '診所地址',
#             'default_appointment_duration': '預設預約時長（分鐘）',
#             'advance_booking_days': '可提前預約天數'
#         }
#         widgets = {
#             'clinic_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
#             'clinic_phone': forms.TextInput(attrs={'class': 'form-control'}),
#             'clinic_email': forms.EmailInput(attrs={'class': 'form-control'}),
#             'clinic_address': forms.TextInput(attrs={'class': 'form-control'}),
#             'default_appointment_duration': forms.Select(choices=[
#                 (15, '15分鐘'), (20, '20分鐘'), (30, '30分鐘'),
#                 (45, '45分鐘'), (60, '60分鐘')
#             ], attrs={'class': 'form-control'}),
#             'advance_booking_days': forms.NumberInput(attrs={
#                 'class': 'form-control', 'min': 1, 'max': 90
#             }),
#         }

# ===== 診所搜尋表單 =====
# ClinicSearchForm 已註解停用 (2025-10-24)
# class ClinicSearchForm(forms.Form):
#     """診所搜尋表單"""
    
#     search_query = forms.CharField(
#         label='搜尋關鍵字',
#         max_length=100,
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '輸入診所名稱或地址...'
#         })
#     )
    
#     city = forms.ChoiceField(
#         label='縣市',
#         choices=[('', '全部')] + CITY_CHOICES,
#         required=False,
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )
    
#     service_type = forms.ChoiceField(
#         label='服務類型',
#         choices=[
#             ('', '全部'),
#             ('general', '一般診療'),
#             ('emergency', '急診'),
#             ('surgery', '手術'),
#             ('dental', '牙科'),
#             ('grooming', '美容'),
#         ],
#         required=False,
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

# ================ 領養專區表單 ================
# import json

def safe_json_loads(value, default=None):
    """安全地解析JSON，如果失敗返回預設值"""
    if default is None:
        default = {}
    try:
        return json.loads(value) if value else default
    except (json.JSONDecodeError, TypeError):
        return default

class AdoptionForm(forms.ModelForm):
    widget_attrs = {
        'class': 'form-control auto-grow-textarea',
        'rows': 1,
    }
    feature_other = forms.CharField(
        required=False,
        label="其他個性特徵",
        widget=forms.Textarea(attrs={**widget_attrs,
            'id': 'id_feature_other',
            'class': 'form-control auto-grow-textarea',
            'placeholder': '請輸入其他個性特徵'})
    )
    physical_condition_other = forms.CharField(
        required=False,
        label="其他健康狀況",
        widget=forms.Textarea(attrs={**widget_attrs,
            'id': 'id_physical_condition_other',
            'class': 'form-control auto-grow-textarea',
            'placeholder': '請輸入其他健康狀況'})
    )
    adoption_condition_other = forms.CharField(
        required=False,
        label="其他領養條件",
        widget=forms.Textarea(attrs={**widget_attrs,
            'id': 'id_adoption_condition_other',
            'class': 'form-control auto-grow-textarea',
            'placeholder': '請輸入其他領養條件'})
    )
    species_other = forms.CharField(
        required=False,
        label="其他種類",
        max_length=20,
        widget=forms.TextInput(attrs={'id': 'id_species_other', 'placeholder': '請輸入寵物的種類'})
    )
    breed_other = forms.CharField(
        required=False,
        label="其他品種",
        max_length=20,
        widget=forms.TextInput(attrs={'id': 'id_breed_other', 'placeholder': '請輸入寵物的品種'})
    )
    vaccine_other = forms.CharField(
        required=False,
        label="其他疫苗",
        max_length=20,
        widget=forms.TextInput(attrs={'id': 'id_vaccine_other', 'placeholder': '請輸入其他疫苗'})
    )

    # 個性特徵選項
    feature_choice = forms.MultipleChoiceField(
        required=False,
        choices=FEATURE_CHOICES,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'multiple': True,
            'size': '6'
        })
    )

    # 健康狀況選項
    physical_condition_choice = forms.MultipleChoiceField(
        required=False,
        choices=PHYSICAL_CHOICES,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'multiple': True,
            'size': '6'
        })
    )

    # 領養條件選項
    adoption_condition_choice = forms.MultipleChoiceField(
        required=False,
        choices=ADOPTCONDITION_CHOICES,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'multiple': True,
            'size': '6'
        })
    )
    adopt_picture1 = forms.ImageField(
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    adopt_picture2 = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    adopt_picture3 = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    adopt_picture4 = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = AdoptionPet
        fields = ['species', 'breed', 'breed_other', 'species_other', 'vaccine_other',
                  'name', 'sterilization_status', 'chip',
                  'gender', 'weight', 'vaccine', 'feature', 'birth_date',
                  'physical_condition', 'adoption_condition', 'adopt_place',
                  'phone', 'line_id',
                  'adopt_picture1', 'adopt_picture2', 'adopt_picture3', 'adopt_picture4',
                  "health_certificate", "vaccine_certificate"]
        widgets = {
            'species': forms.HiddenInput(),
            'breed': forms.HiddenInput(),
            "vaccine": forms.HiddenInput(),
            'name': forms.TextInput(attrs={'maxlength': 20, 'placeholder': '請填寫寵物的名字', 'autocomplete': 'name'}),
            'chip': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '15', 'placeholder': '請填寫寵物的晶片號碼', 'autocomplete': 'off'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'autocomplete': 'off'}, format='%Y-%m-%d'),
            'gender': forms.Select(attrs={'class': 'form-select', 'autocomplete': 'off'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'maxlength': 5, 'placeholder': '請填寫寵物的重量（公斤/kg）', 'autocomplete': 'off'}),
            'feature': forms.Textarea(attrs={'class': 'form-control', 'maxlength': 300, 'placeholder': '請填寫寵物的個性特征'}),
            'physical_condition': forms.Textarea(attrs={'class': 'form-control', 'maxlength': 300, 'placeholder': '請填寫寵物的健康狀況'}),
            'adoption_condition': forms.Textarea(attrs={'class': 'form-control', 'maxlength': 300, 'placeholder': '請填寫寵物的領養條件'}),
            'adopt_place': forms.Select(attrs={'class': 'form-select', 'autocomplete': 'street-address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '請填寫手機號碼或line_id', 'autocomplete': 'tel'}),
            'line_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '請填寫手機號碼或line_id', 'autocomplete': 'off'}),
            'health_certificate': forms.FileInput(attrs={'accept': 'application/pdf,image/jpeg,image/jpg,image/png'}),
            'vaccine_certificate': forms.FileInput(attrs={'accept': 'application/pdf,image/jpeg,image/jpg,image/png'}),
        }
        labels = {
            'species': '種類', 'breed': '品種', 'name': '名字',
            'sterilization_status': '絕育狀態', 'chip': '晶片號碼',
            'gender': '性別', 'weight': '體重（公斤）', 'vaccine': '疫苗', 'feature': '個性特徵',
            'birth_date': '出生日期', 'physical_condition': '健康狀況', 'adoption_condition': '領養條件',
            'adopt_place': '領養地點',
            'adopt_picture1': '圖片1',
            'adopt_picture2': '圖片2', 'adopt_picture3': '圖片3',
            'adopt_picture4': '圖片4',
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)

        # 如果是新增模式且有 owner，預設填入電話號碼
        if not self.instance.pk and self.owner:
            try:
                if hasattr(self.owner, 'profile') and self.owner.profile.phone_number:
                    self.fields['phone'].initial = self.owner.profile.phone_number
            except:
                pass

        # 設定 hidden input 的初始值
        self.fields['species'].widget = forms.HiddenInput()
        self.fields['breed'].widget = forms.HiddenInput()
        self.fields['vaccine'].widget = forms.HiddenInput()
        if self.instance and self.instance.pk:
            self.fields['species'].initial = self.instance.species
            self.fields['breed'].initial = self.instance.breed
            self.fields['vaccine'].initial = self.instance.vaccine

        # 這些欄位通過自訂邏輯處理，但保留為隱藏欄位用於儲存
        self.fields['feature'].required = False
        self.fields['feature'].widget = forms.HiddenInput()
        self.fields['physical_condition'].required = False
        self.fields['physical_condition'].widget = forms.HiddenInput()
        self.fields['adoption_condition'].required = False
        self.fields['adoption_condition'].widget = forms.HiddenInput()

        # 設定下拉選單選項
        self.fields['sterilization_status'].choices = [('', '請選擇')] + list(SterilizationStatus.choices)
        self.fields['gender'].choices = [('', '請選擇')] + list(Gender.choices)
        self.fields['adopt_place'].choices = [('', '請選擇')] + list(REGION_CHOICES)

        # 如果是編輯模式，初始化多選欄位的值
        if self.instance and self.instance.pk:
            # 解析並設置個性特徵初始值
            if self.instance.feature:
                feature_data = safe_json_loads(self.instance.feature)
                if feature_data and 'feature_choice' in feature_data:
                    self.fields['feature_choice'].initial = feature_data['feature_choice']
                if feature_data and 'feature_other' in feature_data:
                    self.fields['feature_other'].initial = feature_data['feature_other']

            # 解析並設置健康狀況初始值
            if self.instance.physical_condition:
                physical_data = safe_json_loads(self.instance.physical_condition)
                if physical_data and 'physical_condition_choice' in physical_data:
                    self.fields['physical_condition_choice'].initial = physical_data['physical_condition_choice']
                if physical_data and 'physical_condition_other' in physical_data:
                    self.fields['physical_condition_other'].initial = physical_data['physical_condition_other']

            # 解析並設置領養條件初始值
            if self.instance.adoption_condition:
                adoption_data = safe_json_loads(self.instance.adoption_condition)
                if adoption_data and 'adoption_condition_choice' in adoption_data:
                    self.fields['adoption_condition_choice'].initial = adoption_data['adoption_condition_choice']
                if adoption_data and 'adoption_condition_other' in adoption_data:
                    self.fields['adoption_condition_other'].initial = adoption_data['adoption_condition_other']

        # 設定必填欄位
        for field_name in ['name', 'weight', 'birth_date', 'sterilization_status', 'gender']:
            self.fields[field_name].required = True

    def clean_chip(self):
        chip = self.cleaned_data.get('chip')
        if chip:
            qs = AdoptionPet.objects.filter(chip=chip)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("此晶片號碼已被使用")
        return chip

    def clean(self):
        cleaned_data = super().clean()
        
        # 處理個性特徵
        feature_choice = self.data.getlist('feature_choice')
        feature_other = cleaned_data.get('feature_other', '')
        feature_data = {
            'feature_choice': feature_choice,
            'feature_other': feature_other
        }
        cleaned_data['feature'] = json.dumps(feature_data, ensure_ascii=False)

        # 處理健康狀況
        physical_choice = self.data.getlist('physical_condition_choice')
        physical_other = cleaned_data.get('physical_condition_other', '')
        physical_data = {
            'physical_condition_choice': physical_choice,
            'physical_condition_other': physical_other
        }
        cleaned_data['physical_condition'] = json.dumps(physical_data, ensure_ascii=False)

        # 處理領養條件
        adoptcondition_choice = self.data.getlist('adoption_condition_choice')
        adoptcondition_other = cleaned_data.get('adoption_condition_other', '')
        adoptcondition_data = {
            'adoption_condition_choice': adoptcondition_choice,
            'adoption_condition_other': adoptcondition_other
        }
        cleaned_data['adoption_condition'] = json.dumps(adoptcondition_data, ensure_ascii=False)

        # 種類
        species = cleaned_data.get('species') or ''
        species_other = cleaned_data.get('species_other') or ''
        if not species:
            self.add_error('species', "請選擇寵物種類！")
        elif species == '其他':
            if not species_other.strip():
                self.add_error('species_other', "請填寫自訂種類！")
            else:
                cleaned_data['species'] = species_other.strip()

        # 品種
        breed = cleaned_data.get('breed') or ''
        breed_other = cleaned_data.get('breed_other') or ''
        if not breed:
            self.add_error('breed', "請選擇寵物品種！")
        elif breed == '其他':
            if not breed_other.strip():
                self.add_error('breed_other', "請填寫自訂品種！")
            else:
                cleaned_data['breed'] = breed_other.strip()

        # 疫苗
        vaccine = cleaned_data.get('vaccine') or ''
        vaccine_other = cleaned_data.get('vaccine_other') or ''
        if not vaccine:
            self.add_error('vaccine', "請選擇寵物施打過的疫苗！")
        elif vaccine == '其他':
            if not vaccine_other.strip():
                self.add_error('vaccine_other', "請填寫寵物施打過的疫苗！")
            else:
                cleaned_data['vaccine'] = vaccine_other.strip()

        return cleaned_data

    def clean_my_pet_id(self):
        """驗證選擇的寵物是否可以用於領養"""
        # 這個驗證會在視圖中處理，因為需要 request 對象
        return self.data.get('my_pet_id')

class TransferRequestForm(forms.ModelForm):
    """更改飼主請求表單"""
    
    class Meta:
        model = TransferRequest
        fields = ['to_email', 'to_phone']
        labels = {
            'to_email': '新飼主信箱',
            'to_phone': '新飼主手機號碼',
        }
        widgets = {
            'to_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'to_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_to_phone(self):
        phone = self.cleaned_data.get('to_phone')
        if not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")
        return phone

# ===== 特殊排班例外表單 =====
# VetScheduleExceptionForm 已註解停用 (2025-10-24)
# class VetScheduleExceptionForm(forms.ModelForm):
#     """獸醫師特殊排班例外表單"""
    
#     class Meta:
#         model = VetScheduleException
#         fields = [
#             'exception_type', 'start_date', 'end_date', 
#             'start_time', 'end_time', 'alternative_start_time', 
#             'alternative_end_time', 'reason'
#         ]
#         labels = {
#             'exception_type': '例外類型',
#             'start_date': '開始日期',
#             'end_date': '結束日期',
#             'start_time': '開始時間',
#             'end_time': '結束時間',
#             'alternative_start_time': '替代開始時間',
#             'alternative_end_time': '替代結束時間',
#             'reason': '原因說明',
#         }
#         widgets = {
#             'exception_type': forms.Select(attrs={'class': 'form-control'}),
#             'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
#             'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
#             'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
#             'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
#             'alternative_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
#             'alternative_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
#             'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#         }
    
#     def clean(self):
#         cleaned_data = super().clean()
#         start_date = cleaned_data.get('start_date')
#         end_date = cleaned_data.get('end_date')
#         start_time = cleaned_data.get('start_time')
#         end_time = cleaned_data.get('end_time')
#         alt_start_time = cleaned_data.get('alternative_start_time')
#         alt_end_time = cleaned_data.get('alternative_end_time')
        
        # 日期驗證
#         if start_date and end_date and start_date > end_date:
#             raise forms.ValidationError('結束日期不能早於開始日期')
        
        # 時間驗證
#         if start_time and end_time and start_time >= end_time:
#             raise forms.ValidationError('結束時間必須晚於開始時間')
            
        # 替代時間驗證
#         if alt_start_time and alt_end_time and alt_start_time >= alt_end_time:
#             raise forms.ValidationError('替代結束時間必須晚於替代開始時間')
        
#         return cleaned_data

