# petapp/forms.py 
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import (
    VetClinic, VetDoctor, Profile, Pet, Species, SterilizationStatus, 
    Gender, DailyRecord, VaccineRecord, DewormRecord, Report, 
    MedicalRecord, VetSchedule, AppointmentSlot, VetAppointment,VetScheduleException
)
from allauth.account.forms import SignupForm
import re
import requests
from datetime import date, time, datetime, timedelta
from django.db import transaction

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
class VetClinicRegistrationForm(forms.Form):
    """診所註冊表單"""
    
    # 診所基本資訊
    clinic_name = forms.CharField(
        max_length=100,
        label='診所名稱',
        help_text='請填寫與農委會登記完全相同的診所名稱',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：台北市愛心動物醫院'
        })
    )
    
    license_number = forms.CharField(
        max_length=50,
        label='開業執照字號',
        help_text='請填寫與農委會登記完全相同的執照字號',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：北市動字第1234567號'
        })
    )
    
    clinic_phone = forms.CharField(
        max_length=20,
        label='診所電話',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：02-12345678'
        })
    )
    
    clinic_email = forms.EmailField(
        label='診所信箱',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '例：clinic@example.com'
        })
    )
    
    clinic_address = forms.CharField(
        max_length=255,
        label='診所地址',
        help_text='請填寫與農委會登記完全相同的診所地址',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：台北市中正區重慶南路一段122號'
        })
    )
    
    # 管理員帳號資訊
    admin_username = forms.CharField(
        max_length=30,
        label='管理員帳號',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '英文、數字或底線，3-30個字元'
        })
    )
    
    admin_email = forms.EmailField(
        label='管理員信箱',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '例：admin@example.com'
        })
    )
    
    admin_password = forms.CharField(
        min_length=8,
        label='管理員密碼',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '至少8個字元，建議包含大小寫字母、數字'
        })
    )
    
    admin_password_confirm = forms.CharField(
        label='確認密碼',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '請再次輸入密碼'
        })
    )
    
    admin_real_name = forms.CharField(
        max_length=20,
        label='管理員真實姓名',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：王小明'
        })
    )
    
    admin_phone = forms.CharField(
        max_length=15,
        label='管理員電話',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：0912345678'
        })
    )
    
    # 驗證確認
    verification_confirmed = forms.BooleanField(
        label='確認接受農委會驗證',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean_admin_username(self):
        """驗證管理員帳號"""
        username = self.cleaned_data['admin_username']
        
        # 檢查是否已存在
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('此使用者名稱已被使用')
        
        # 檢查格式
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError('帳號只能包含英文、數字和底線')
        
        return username
    
    def clean_admin_email(self):
        """驗證管理員信箱"""
        email = self.cleaned_data['admin_email']
        
        # 檢查是否已存在
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('此電子郵件已被使用')
        
        return email
    
    def clean_license_number(self):
        """驗證執照字號"""
        license_number = self.cleaned_data['license_number']
        
        # 檢查是否已存在
        if VetClinic.objects.filter(license_number=license_number).exists():
            raise forms.ValidationError('此執照字號已被註冊')
        
        return license_number
    
    def clean(self):
        """全表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證密碼確認
        password = cleaned_data.get('admin_password')
        password_confirm = cleaned_data.get('admin_password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError('密碼確認不符')
        
        return cleaned_data
    
    def verify_with_moa_api(self, clinic_name, license_number):
        """即時驗證農委會API"""
        try:
            import requests
            
            api_url = "https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=078"
            print(f"🔍 開始驗證: {clinic_name} - {license_number}")
            
            response = requests.get(api_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 API回應資料筆數: {len(data)}")
                
                for clinic_data in data:
                    # 精確比對診所名稱和執照字號
                    api_license = clinic_data.get('字號', '').strip()
                    api_name = clinic_data.get('機構名稱', '').strip()
                    
                    if api_license == license_number and api_name == clinic_name:
                        print(f"✅ 找到匹配的診所: {clinic_data}")
                        
                        # 檢查開業狀態
                        status = clinic_data.get('狀態', '').strip()
                        if status != '開業':
                            return False, f"診所狀態為「{status}」，無法註冊"
                        
                        # 儲存驗證資料到表單實例
                        self.moa_data = clinic_data
                        return True, "農委會資料驗證成功"
                
                return False, "農委會資料庫中找不到對應的診所資訊，請確認診所名稱和執照字號是否與農委會登記完全相同"
            else:
                return False, f"無法連接農委會API (HTTP {response.status_code})"
                
        except Exception as e:
            print(f"💥 驗證過程發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False, f"驗證過程發生錯誤：{str(e)}"

    def save(self):
        """保存診所和管理員資料"""
        from django.contrib.auth.models import User
        from django.db import transaction
        from .models import VetClinic, VetDoctor, Profile
        from django.utils import timezone
        from datetime import datetime
        
        cleaned_data = self.cleaned_data
        
        # 先進行農委會驗證
        clinic_name = cleaned_data['clinic_name']
        license_number = cleaned_data['license_number']
        
        success, message = self.verify_with_moa_api(clinic_name, license_number)
        if not success:
            raise forms.ValidationError(f'農委會驗證失敗：{message}')
        
        with transaction.atomic():
            # 建立診所實例
            clinic = VetClinic(
                clinic_name=cleaned_data['clinic_name'],
                license_number=cleaned_data['license_number'],
                clinic_phone=cleaned_data['clinic_phone'],
                clinic_email=cleaned_data['clinic_email'],
                clinic_address=cleaned_data['clinic_address']
            )
            
            # 填入農委會驗證資料
            if hasattr(self, 'moa_data'):
                moa_data = self.moa_data
                clinic.moa_county = moa_data.get('縣市', '')
                clinic.moa_status = moa_data.get('狀態', '')
                clinic.moa_responsible_vet = moa_data.get('負責獸醫', '')
                
                # 轉換發照日期
                issue_date_str = moa_data.get('發照日期', '')
                if issue_date_str and len(issue_date_str) == 8:
                    try:
                        clinic.moa_issue_date = datetime.strptime(issue_date_str, '%Y%m%d').date()
                    except ValueError:
                        pass
                
                clinic.is_verified = True
                clinic.verification_date = timezone.now()
            
            clinic.save()
            
            # 建立管理員使用者
            admin_user = User.objects.create_user(
                username=cleaned_data['admin_username'],
                email=cleaned_data['admin_email'],
                password=cleaned_data['admin_password'],
                first_name=cleaned_data['admin_real_name']
            )
            
            # 建立使用者檔案
            profile = Profile.objects.create(
                user=admin_user,
                account_type='clinic_admin',
                phone_number=cleaned_data['admin_phone']
            )
            
            # 建立獸醫師檔案（診所管理員）
            vet_doctor = VetDoctor.objects.create(
                user=admin_user,
                clinic=clinic,
                is_active=True
            )
            
            return clinic

# ===== 獸醫師表單 =====
class VetDoctorForm(forms.ModelForm):
    """獸醫師新增表單 """
    
    username = forms.CharField(
        max_length=150, 
        label='使用者帳號',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '英文、數字或底線，3-30個字元'
        }),
        help_text='英文、數字或底線，3-30個字元'
    )
    email = forms.EmailField(
        label='電子信箱',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '例：doctor@example.com'
        }),
        help_text='將作為登入帳號和通知信箱'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '至少8個字元'
        }), 
        label='密碼',
        min_length=8,
        help_text='至少8個字元，建議包含大小寫字母、數字'
    )
    first_name = forms.CharField(
        max_length=30, 
        label='真實姓名',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：王小明'
        }),
        help_text='醫師的真實姓名'
    )
    phone_number = forms.CharField(
        max_length=20, 
        label='聯絡電話',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '09xxxxxxxx'
        }),
        help_text='台灣手機號碼格式'
    )
    
    class Meta:
        model = VetDoctor
        fields = [
            'vet_license_number', 'specialization', 'years_of_experience', 'bio'
        ]
        labels = {
            'vet_license_number': '獸醫師執照號碼',
            'specialization': '專科領域',
            'years_of_experience': '執業年資',
            'bio': '個人簡介',
        }
        widgets = {
            'vet_license_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例：94府農畜字第13273號'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例：小動物內科、外科、皮膚科'
            }),
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 0, 
                'max': 50,
                'placeholder': '0'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '可包含專業背景、治療理念、特殊專長等資訊'
            }),
        }
        help_texts = {
            'vet_license_number': '可稍後填寫，需通過農委會驗證後才能填寫醫療記錄',
            'specialization': '例如：小動物內科、外科、皮膚科等',
            'years_of_experience': '以年為單位',
            'bio': '可包含專業背景、治療理念、特殊專長等',
        }
    
    def __init__(self, *args, **kwargs):
        self.clinic = kwargs.pop('clinic', None)
        super().__init__(*args, **kwargs)
        
        # 設定預設值
        if not self.instance.pk:
            self.fields['years_of_experience'].initial = 0
    
    def clean_username(self):
        username = self.cleaned_data['username']
        
        # 檢查格式
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
            raise forms.ValidationError('帳號只能包含英文、數字和底線，長度3-30個字元')
        
        # 檢查是否已存在
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('此使用者名稱已被使用')
        
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        
        # 檢查是否已存在
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('此信箱已被註冊')
        
        return email
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError('請輸入有效的台灣手機號碼（格式：09xxxxxxxx）')
        return phone
    
    def clean_years_of_experience(self):
        years = self.cleaned_data.get('years_of_experience')
        if years is not None and (years < 0 or years > 50):
            raise forms.ValidationError('執業年資應在0-50年之間')
        return years
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        if len(password) < 8:
            raise forms.ValidationError('密碼至少需要8個字元')
        
        # 可以加入更多密碼強度檢查
        return password

class VetLicenseVerificationForm(forms.ModelForm):
    """獸醫師執照驗證表單 - 僅執照號碼"""
    
    class Meta:
        model = VetDoctor
        fields = ['vet_license_number']
        labels = {
            'vet_license_number': '獸醫師執照號碼',
        }
        widgets = {
            'vet_license_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入完整執照號碼，例如：94府農畜字第13273號'
            }),
        }
        help_texts = {
            'vet_license_number': '將自動透過農委會API驗證執照有效性'
        }
    
    def clean_vet_license_number(self):
        license_number = self.cleaned_data.get('vet_license_number')
        
        if not license_number:
            raise forms.ValidationError('請輸入執照號碼')
        
        # 🎯 檢查是否已被其他獸醫使用
        existing_vet = VetDoctor.objects.filter(
            vet_license_number=license_number,
            license_verified_with_moa=True
        ).exclude(pk=self.instance.pk if self.instance else None).first()
        
        if existing_vet:
            raise forms.ValidationError(f'此執照號碼已被 {existing_vet.user.get_full_name()} 驗證使用')
        
        return license_number
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        if len(password) < 8:
            raise forms.ValidationError('密碼至少需要8個字元')
        
        # 可以加入更多密碼強度檢查
        return password


class EditDoctorForm(forms.ModelForm):
    """編輯醫師表單 - 支援雙重身份"""
    
    # 基本資訊
    first_name = forms.CharField(
        label='姓名',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入醫師姓名'
        })
    )
    
    email = forms.EmailField(
        label='電子郵件',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'doctor@example.com'
        })
    )
    
    phone_number = forms.CharField(
        label='聯絡電話',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09xxxxxxxx'
        })
    )
    
    # 🔄 改進：分離的身份權限欄位
    is_active_veterinarian = forms.BooleanField(
        label='啟用獸醫師身份',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='允許此帳號執行獸醫師相關功能（需要通過執照驗證）'
    )
    
    is_active_admin = forms.BooleanField(
        label='啟用管理員身份',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='允許此帳號管理診所設定和其他醫師'
    )

    class Meta:
        model = VetDoctor
        fields = [
            'vet_license_number', 'specialization', 'years_of_experience', 
            'bio', 'is_active_veterinarian', 'is_active_admin'
        ]
        widgets = {
            'vet_license_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如：**府農**字第****號'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如：小動物內科、外科等'
            }),
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 50
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'maxlength': 500,
                'placeholder': '醫師的專業背景和治療理念介紹...'
            }),
        }

    """編輯獸醫師表單 """
    
    # 額外的 User 和 Profile 欄位
    first_name = forms.CharField(
        max_length=30, 
        label='真實姓名',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：王小明'
        })
    )
    email = forms.EmailField(
        label='電子信箱',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '例：doctor@example.com'
        })
    )
    phone_number = forms.CharField(
        max_length=20, 
        label='聯絡電話',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '09xxxxxxxx'
        })
    )
    
    class Meta:
        model = VetDoctor
        fields = [
            'vet_license_number', 'specialization', 'years_of_experience', 'bio'
        ]
        labels = {
            'vet_license_number': '獸醫師執照號碼',
            'specialization': '專科領域',
            'years_of_experience': '執業年資',
            'bio': '個人簡介',
        }
        widgets = {
            'vet_license_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例：94府農畜字第13273號'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例：小動物內科、外科、皮膚科'
            }),
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 0, 
                'max': 50
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '可包含專業背景、治療理念、特殊專長等資訊'
            }),
        }
        help_texts = {
            'vet_license_number': '需通過農委會驗證後才能填寫醫療記錄',
            'specialization': '例如：小動物內科、外科、皮膚科等',
            'years_of_experience': '以年為單位',
            'bio': '可包含專業背景、治療理念、特殊專長等',
        }
    
    def clean_email(self):
        email = self.cleaned_data['email']
        # 檢查 email 是否被其他使用者使用（排除目前編輯的使用者）
        current_user = self.instance.user if self.instance else None
        if User.objects.exclude(pk=current_user.pk if current_user else None).filter(email=email).exists():
            raise forms.ValidationError('此信箱已被其他使用者使用')
        return email
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError('請輸入有效的台灣手機號碼（格式：09xxxxxxxx）')
        return phone
    
    def clean_years_of_experience(self):
        years = self.cleaned_data.get('years_of_experience')
        if years is not None and (years < 0 or years > 50):
            raise forms.ValidationError('執業年資應在0-50年之間')
        return years

# ===== 獸醫師排班表單 =====
class VetScheduleForm(forms.ModelForm):
    """獸醫師排班表單"""
    
    class Meta:
        model = VetSchedule
        fields = [
            'weekday', 'start_time', 'end_time', 
            'appointment_duration', 'max_appointments_per_slot', 'notes'
        ]
        labels = {
            'weekday': '星期',
            'start_time': '開始時間',
            'end_time': '結束時間',
            'appointment_duration': '預約時長（分鐘）',
            'max_appointments_per_slot': '每時段最大預約數',
            'notes': '備註'
        }
        widgets = {
            'weekday': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'appointment_duration': forms.Select(choices=[
                (15, '15分鐘'), (20, '20分鐘'), (30, '30分鐘'), 
                (45, '45分鐘'), (60, '60分鐘')
            ], attrs={'class': 'form-control'}),
            'max_appointments_per_slot': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'max': 5
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        }
    
    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        
        # 設定預設值
        if not self.instance.pk:
            self.fields['appointment_duration'].initial = 30
            self.fields['max_appointments_per_slot'].initial = 1
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        weekday = cleaned_data.get('weekday')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError('結束時間必須晚於開始時間')
            
            # 檢查時間重疊
            if self.doctor:
                overlapping = VetSchedule.objects.filter(
                    doctor=self.doctor,
                    weekday=weekday,
                    is_active=True
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                for schedule in overlapping:
                    if (start_time < schedule.end_time and end_time > schedule.start_time):
                        raise forms.ValidationError(
                            f'與現有排班時間重疊：{schedule.start_time.strftime("%H:%M")}-{schedule.end_time.strftime("%H:%M")}'
                        )
        
        return cleaned_data
        

# ===== 排班例外表單 =====
class VetScheduleExceptionForm(forms.ModelForm):
    """獸醫師排班例外表單"""
    
    class Meta:
        model = VetScheduleException
        fields = [
            'exception_type', 'start_date', 'end_date',
            'start_time', 'end_time', 'alternative_start_time', 
            'alternative_end_time', 'reason'
        ]
        labels = {
            'exception_type': '例外類型',
            'start_date': '開始日期',
            'end_date': '結束日期',
            'start_time': '開始時間（可選）',
            'end_time': '結束時間（可選）',
            'alternative_start_time': '替代開始時間',
            'alternative_end_time': '替代結束時間',
            'reason': '原因'
        }
        widgets = {
            'exception_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'alternative_start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'alternative_end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設定最小日期為今天
        today = date.today().isoformat()
        self.fields['start_date'].widget.attrs['min'] = today
        self.fields['end_date'].widget.attrs['min'] = today
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        exception_type = cleaned_data.get('exception_type')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('結束日期不能早於開始日期')
        
        # 特殊排班必須填寫替代時間
        if exception_type == 'special':
            alt_start = cleaned_data.get('alternative_start_time')
            alt_end = cleaned_data.get('alternative_end_time')
            
            if not alt_start or not alt_end:
                raise forms.ValidationError('特殊排班必須填寫替代時間')
            
            if alt_start >= alt_end:
                raise forms.ValidationError('替代結束時間必須晚於替代開始時間')
        
        return cleaned_data




# ===== 飼主預約表單 =====
class AppointmentBookingForm(forms.Form):
    """飼主預約表單 - 診所→醫師→時段流程"""
    
    clinic = forms.ModelChoiceField(
        queryset=VetClinic.objects.filter(is_verified=True),
        label='選擇診所',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'onchange': 'loadDoctors(this.value)'
        }),
        empty_label='請選擇診所'
    )
    
    doctor = forms.ModelChoiceField(
        queryset=VetDoctor.objects.none(),
        label='選擇醫師',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'onchange': 'loadAvailableSlots()'
        }),
        empty_label='任何醫師'
    )
    
    appointment_date = forms.DateField(
        label='預約日期',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': (date.today() + timedelta(days=1)).isoformat(),
            'onchange': 'loadAvailableSlots()'
        })
    )
    
    time_slot = forms.ModelChoiceField(
        queryset=AppointmentSlot.objects.none(),
        label='預約時段',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='請先選擇日期'
    )
    
    reason = forms.CharField(
        label='預約原因',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '請簡述預約原因，如：定期健檢、疫苗接種、身體不適等'
        }),
        max_length=500,
        required=False
    )
    
    notes = forms.CharField(
        label='備註',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': '其他需要診所知道的資訊'
        }),
        max_length=300,
        required=False
    )
    
    # 聯絡資訊
    contact_phone = forms.CharField(
        label='聯絡電話',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09xxxxxxxx'
        }),
        help_text='如需變更預約時的聯絡電話'
    )
    
    def __init__(self, *args, **kwargs):
        # 處理自定義參數
        self.pet = kwargs.pop('pet', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 設定預設聯絡電話
        if self.user and hasattr(self.user, 'profile') and self.user.profile.phone_number:
            self.fields['contact_phone'].initial = self.user.profile.phone_number
        
        # 動態載入醫師選項
        if 'clinic' in self.data:
            try:
                clinic_id = int(self.data.get('clinic'))
                self.fields['doctor'].queryset = VetDoctor.objects.filter(
                    clinic_id=clinic_id, is_active=True
                ).order_by('user__first_name')
            except (ValueError, TypeError):
                pass
        
        # 動態載入時段選項
        if all(k in self.data for k in ['clinic', 'appointment_date']):
            try:
                clinic_id = int(self.data.get('clinic'))
                appointment_date = datetime.strptime(self.data.get('appointment_date'), '%Y-%m-%d').date()
                doctor_id = self.data.get('doctor')
                
                slots_query = AppointmentSlot.objects.filter(
                    clinic_id=clinic_id,
                    date=appointment_date,
                    is_available=True
                ).filter(current_bookings__lt=models.F('max_bookings'))
                
                if doctor_id:
                    slots_query = slots_query.filter(doctor_id=doctor_id)
                
                self.fields['time_slot'].queryset = slots_query.order_by('start_time')
                
            except (ValueError, TypeError):
                pass
    
    def clean_contact_phone(self):
        phone = self.cleaned_data.get('contact_phone')
        if phone and not re.match(r'^09\d{8}$', phone):
            raise ValidationError('請輸入有效的台灣手機號碼（格式：09xxxxxxxx）')
        return phone
    
    def clean_appointment_date(self):
        appointment_date = self.cleaned_data['appointment_date']
        
        # 不能預約今天或過去的日期
        if appointment_date <= date.today():
            raise ValidationError('預約日期必須是明天以後')
        
        # 不能預約太遠的未來（例如60天後）
        max_future_date = date.today() + timedelta(days=60)
        if appointment_date > max_future_date:
            raise ValidationError('預約日期不能超過60天後')
        
        return appointment_date
    
    def clean(self):
        cleaned_data = super().clean()
        clinic = cleaned_data.get('clinic')
        doctor = cleaned_data.get('doctor')
        appointment_date = cleaned_data.get('appointment_date')
        time_slot = cleaned_data.get('time_slot')
        
        if time_slot:
            # 驗證時段是否仍可預約
            if not time_slot.can_book():
                raise ValidationError('此時段已被預約，請重新選擇')
            
            # 如果指定了醫師，確認時段屬於該醫師
            if doctor and time_slot.doctor != doctor:
                raise ValidationError('所選時段不屬於指定醫師')
            
            # 驗證時段日期
            if time_slot.date != appointment_date:
                raise ValidationError('時段日期不符')
            
            # 檢查該用戶在同一時段是否已有預約
            if self.user:
                existing_appointment = VetAppointment.objects.filter(
                    owner=self.user,
                    slot=time_slot,
                    status__in=['pending', 'confirmed']
                ).exists()
                
                if existing_appointment:
                    raise ValidationError('您在此時段已有預約')
        
        return cleaned_data

def verify_with_moa_api(self, clinic_name, license_number):
    """即時驗證農委會API"""
    try:
        import requests
        import re
        
        api_url = "https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=078"
        print(f"🔍 開始驗證: {clinic_name} - {license_number}")
        
        response = requests.get(api_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 API回應資料筆數: {len(data)}")
            
            for clinic_data in data:
                # 精確比對診所名稱和執照字號
                api_license = clinic_data.get('字號', '').strip()
                api_name = clinic_data.get('機構名稱', '').strip()
                
                print(f"比對中: API字號='{api_license}', API名稱='{api_name}'")
                print(f"用戶輸入: 字號='{license_number}', 名稱='{clinic_name}'")
                
                if api_license == license_number and api_name == clinic_name:
                    print(f"✅ 找到匹配的診所: {clinic_data}")
                    
                    # 檢查開業狀態
                    status = clinic_data.get('狀態', '').strip()
                    if status != '開業':
                        return False, f"診所狀態為「{status}」，無法註冊"
                    
                    # 儲存驗證資料
                    self.moa_data = clinic_data
                    return True, "農委會資料驗證成功"
            
            # 如果沒找到，提供更詳細的錯誤訊息
            print(f"❌ 未找到匹配的診所")
            print(f"請檢查以下資料是否與農委會登記完全一致：")
            print(f"- 診所名稱：{clinic_name}")
            print(f"- 執照字號：{license_number}")
            
            return False, "農委會資料庫中找不到對應的診所資訊，請確認診所名稱和執照字號是否與農委會登記完全相同"
        else:
            return False, f"無法連接農委會API (HTTP {response.status_code})"
            
    except Exception as e:
        print(f"💥 驗證過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False, f"驗證過程發生錯誤：{str(e)}"
        

    def save(self, commit=True):
        """儲存診所和管理員資料"""
        clinic = super().save(commit=False)
        
        if commit:
            # 填入農委會驗證資料
            if hasattr(self, 'moa_data'):
                moa_data = self.moa_data
                clinic.moa_county = moa_data.get('縣市', '')
                clinic.moa_status = moa_data.get('狀態', '')
                clinic.moa_responsible_vet = moa_data.get('負責獸醫', '')
                
                # 轉換發照日期
                issue_date_str = moa_data.get('發照日期', '')
                if issue_date_str and len(issue_date_str) == 8:
                    try:
                        clinic.moa_issue_date = datetime.strptime(issue_date_str, '%Y%m%d').date()
                    except ValueError:
                        pass
                
                clinic.is_verified = True
                clinic.verification_date = datetime.now()
            
            clinic.save()
            
            # 建立管理員帳號
            user = User.objects.create_user(
                username=self.cleaned_data['admin_username'],
                email=self.cleaned_data['admin_email'],
                password=self.cleaned_data['admin_password'],
                first_name=self.cleaned_data['admin_real_name']
            )
            
            # 建立 Profile
            profile = Profile.objects.create(
                user=user,
                account_type='clinic_admin',
                phone_number=self.cleaned_data['admin_phone']
            )
            
            # 建立 VetDoctor 記錄（管理員身分）
            vet_doctor = VetDoctor.objects.create(
                user=user,
                clinic=clinic,
                vet_license_number='',  # 管理員可能不是獸醫
                is_active=True
            )
        
        return clinic

    def clean(self):
        """表單層級驗證 - 農委會API驗證"""
        cleaned_data = super().clean()
        clinic_name = cleaned_data.get('clinic_name')
        license_number = cleaned_data.get('license_number')
        
        print(f"🔍 準備驗證: 診所={clinic_name}, 執照={license_number}")
        
        if clinic_name and license_number:
            # 暫時跳過API驗證，直接通過
            print("⚠️ 暫時跳過農委會驗證（除錯模式）")
            # success, message = self.verify_with_moa_api(clinic_name, license_number)
            # if not success:
            #     raise ValidationError(f"農委會驗證失敗：{message}")
        
        return cleaned_data

# ===== 飼主註冊表單 =====
class CustomSignupForm(SignupForm):
    """飼主註冊表單（僅支援飼主註冊，獸醫院另外註冊）"""
    
    phone_number = forms.CharField(max_length=20, label="手機號碼", required=True)
    last_name = forms.CharField(label="姓氏", max_length=30, required=False)
    first_name = forms.CharField(label="名字", max_length=30, required=False)

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")
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
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        user.save()

        login(request, user)
        return user


# ===== 保留：原有表單（稍作調整） =====

# 編輯個人資料用表單（簡化版，移除獸醫相關欄位）
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

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")
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

# Google 註冊後補資料表單
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

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")
        return phone

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("此使用者名稱已被使用")
        return username

# 一般註冊表單（含 email）
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

# 寵物資料管理用表單
class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = [
            'species', 'breed', 'name', 'sterilization_status', 'chip',
            'gender', 'weight', 'feature', 'picture','birth_date',
        ]
        labels = {
            'species': '種類', 'breed': '品種', 'name': '名字',
            'sterilization_status': '絕育狀態', 'chip': '晶片號碼',
            'gender': '性別', 'weight': '體重（公斤）', 'feature': '特徵',
            'picture': '圖片', 'birth_date': '出生日期',
        }
        widgets = {
            'breed': forms.TextInput(attrs={'maxlength': 50}),
            'name': forms.TextInput(attrs={'maxlength': 50}),
            'chip': forms.NumberInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'feature': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        self.fields['picture'].required = True
        for field_name in ['breed', 'name', 'chip', 'weight', 'feature','birth_date']:
            self.fields[field_name].required = True
        if not self.initial.get('date'):
            self.initial['date'] = date.today()

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
            qs = Pet.objects.filter(name=name, owner=self.owner)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)  # 編輯時排除自己
            if qs.exists():
                raise forms.ValidationError("已有這個寵物的資料")
        if len(name) > 20:
            raise forms.ValidationError("名字最多只能輸入 50 個字元。")
        return name

    def clean_breed(self):
        breed = self.cleaned_data.get('breed')
        if len(breed) > 30:
            raise forms.ValidationError("品種最多只能輸入 50 個字元。")
        return breed

# 健康紀錄輸入表單
class DailyRecordForm(forms.ModelForm):
    class Meta:
        model = DailyRecord
        fields = ['date', 'category', 'content']
        labels = {'date': '日期', 'category': '類別', 'content': '內容'}
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('date'):
            self.initial['date'] = date.today()

    def clean_date(self):
        record_date = self.cleaned_data.get('date')
        if record_date and record_date > date.today():
            raise forms.ValidationError("日期不能是未來")
        return record_date

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if not content:
            raise forms.ValidationError("請填寫內容")
        return content

# 體溫編輯表單
class TemperatureEditForm(forms.Form):
    date = forms.DateField(label='紀錄時間',
        widget=forms.DateInput(attrs={'type': 'date'}),input_formats=['%Y-%m-%d'])
    temperature = forms.FloatField(label='體溫 (°C)')
    
    def clean_date(self):
        selected_date = self.cleaned_data['date']
        if selected_date > date.today():
            raise forms.ValidationError("日期不能超過今天")
        return selected_date

# 體重編輯表單
class WeightEditForm(forms.Form):
    date = forms.DateField(label='紀錄時間',
            widget=forms.DateInput(attrs={'type': 'date'}),input_formats=['%Y-%m-%d'])
    weight = forms.FloatField(label='體重 (公斤)')
    def clean_date(self):
        selected_date = self.cleaned_data['date']
        if selected_date > date.today():
            raise forms.ValidationError("日期不能超過今天")
        return selected_date

# 疫苗表單
class VaccineRecordForm(forms.ModelForm):
    class Meta:
        model = VaccineRecord
        fields = ['name', 'date', 'location']
        labels = {'name':'疫苗品牌', 'date':'施打日期', 'location':'施打地點'}
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date','class': 'form-control',
                                           'max': date.today().isoformat()
            },format='%Y-%m-%d'),
        }
    
    def clean_date(self):
        vaccination_date = self.cleaned_data['date']
        if vaccination_date > date.today():
            raise forms.ValidationError("疫苗接種日期不能是未來")
        return vaccination_date

# 驅蟲表單
class DewormRecordForm(forms.ModelForm):
    class Meta:
        model = DewormRecord
        fields = ['name', 'date', 'location']
        labels = {'name':'驅蟲品牌', 'date':'施打日期', 'location':'施打地點'}
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control',
                                           'max': date.today().isoformat()
                }, format='%Y-%m-%d'),
        }
    
    def clean_date(self):
        deworm_date = self.cleaned_data['date']
        if deworm_date > date.today():
            raise forms.ValidationError("驅蟲日期不能是未來")
        return deworm_date

# 報告表單
class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['title', 'pdf']
        labels = {'title':'標題', 'pdf':'pdf檔案'}
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '請輸入報告標題'}),
        }

    def clean_pdf(self):
        pdf_file = self.cleaned_data.get('pdf')
        if pdf_file:
            # 檢查副檔名
            if not pdf_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError('請上傳 PDF 格式的檔案。')
            # 檢查 MIME 類型（可選）
            if pdf_file.content_type != 'application/pdf':
                raise forms.ValidationError('檔案格式無效，請確認為 PDF。')
            # 檢查檔案大小（上限：5MB）
            max_size = 5 * 1024 * 1024  # 5MB in bytes
            if pdf_file.size > max_size:
                raise forms.ValidationError('檔案太大，請上傳小於 5MB 的 PDF 檔案。')
        return pdf_file

# 獸醫填寫診斷與治療資訊    
class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ['pet', 'clinic_location', 'diagnosis', 'treatment', 'notes']
        widgets = {
            'pet': forms.HiddenInput(),
            'clinic_location': forms.TextInput(attrs={'placeholder': '預設會自動填入'}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
