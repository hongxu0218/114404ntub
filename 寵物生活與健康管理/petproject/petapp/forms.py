# petapp/forms.py 
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Profile, Pet, DailyRecord, VetAppointment, VaccineRecord, DewormRecord, Report, VetAvailableTime, \
    WEEKDAYS, TIME_SLOTS, MedicalRecord, AdoptionPet, Species, SterilizationStatus, Gender, TransferRequest, \
    REGION_CHOICES
from allauth.account.forms import SignupForm
import re,json
from datetime import date, time, datetime, timedelta
from django.core.exceptions import ValidationError
from .utils import get_species_choices
from .choices import  (FEATURE_CHOICES, PHYSICAL_CHOICES, ADOPTCONDITION_CHOICES, DOG_CHOICES, CAT_CHOICES,
                       DOGVACCINE_CHOICES,CATVACCINE_CHOICES)


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

# 看診時段選項
AVAILABLE_TIME_CHOICES = [
    (time(9, 30), "上午 09:30"),
    (time(10, 0), "上午 10:00"),
    (time(10, 30), "上午 10:30"),
    (time(11, 0), "上午 11:00"),
    (time(11, 30), "上午 11:30"),
    (time(13, 30), "下午 13:30"),
    (time(14, 0), "下午 14:00"),
    (time(14, 30), "下午 14:30"),
    (time(15, 0), "下午 15:00"),
    (time(15, 30), "下午 15:30"),
    (time(16, 0), "下午 16:00"),
    (time(16, 30), "下午 16:30"),
    (time(18, 0), "晚上 18:00"),
    (time(18, 30), "晚上 18:30"),
    (time(19, 0), "晚上 19:00"),
    (time(19, 30), "晚上 19:30"),
    (time(20, 0), "晚上 20:00"),
    (time(20, 30), "晚上 20:30"),
]


# 註冊表單（含帳號類型與手機驗證）
class CustomSignupForm(SignupForm):
    ACCOUNT_TYPE_CHOICES = [('owner', '飼主'), ('vet', '獸醫')]

    account_type = forms.ChoiceField(choices=ACCOUNT_TYPE_CHOICES, label="帳號類型")
    phone_number = forms.CharField(max_length=20, label="手機號碼", required=True)
    last_name = forms.CharField(label="姓氏", max_length=30, required=False)
    first_name = forms.CharField(label="名字", max_length=30, required=False)
    vet_license_city = forms.ChoiceField(choices=[('', '請選擇縣市')] + CITY_CHOICES, label='執業執照縣市', required=False)
    vet_license = forms.FileField(label='獸醫證照', required=False,
        widget = forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}))
    clinic_name = forms.CharField(label="醫院／診所名稱", max_length=100, required=False)
    clinic_address = forms.CharField(label="醫院／診所地址", max_length=255, required=False)


    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")
        return phone

    def save(self, request):
        user = super().save(request)
        account_type = self.cleaned_data['account_type']
        phone_number = self.cleaned_data['phone_number']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']
        vet_license_city = self.cleaned_data.get('vet_license_city')
        vet_license = self.cleaned_data.get('vet_license')
        clinic_name = self.cleaned_data.get('clinic_name')
        clinic_address = self.cleaned_data.get('clinic_address')

        profile = Profile.objects.create(
            user=user,
            account_type=account_type,
            phone_number=phone_number,
            vet_license_city=vet_license_city,
            vet_license=vet_license,
            clinic_name=clinic_name,
            clinic_address=clinic_address,
        )

        if account_type == 'vet':
            from django.core.mail import send_mail
            from django.conf import settings
            subject = "[系統通知] 有新獸醫帳號註冊待審核"
            message = f"""
您好，系統管理員：

有使用者完成一般註冊並選擇了「獸醫帳號」。
🔹 使用者名稱：{user.username}
🔹 Email：{user.email}

請盡快登入後台進行審核：
http://127.0.0.1:8000/admin/petapp/profile/
"""
            send_mail(subject, message, '毛日好(Paw&Day) <{}>'.format(settings.DEFAULT_FROM_EMAIL),
                      [settings.ADMIN_EMAIL], fail_silently=False)

        user.first_name = first_name
        user.last_name = last_name
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        user.save()

        login(request, user)
        return user

# 編輯個人資料用表單（同步 User 與 Profile）
class EditProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, label='使用者名稱')
    first_name = forms.CharField(max_length=30, label='名字', required=False)
    last_name = forms.CharField(max_length=30, label='姓氏', required=False)
    vet_license_city = forms.ChoiceField(choices=CITY_CHOICES, label='執業執照縣市', required=False)
    vet_license = forms.FileField(label='獸醫證照', required=False, widget=forms.FileInput)
    clinic_name = forms.CharField(label='醫院／診所名稱', max_length=100, required=False)
    clinic_address = forms.CharField(label='醫院／診所地址', max_length=255, required=False)

    class Meta:
        model = Profile
        fields = ['account_type', 'phone_number', 'vet_license_city', 'vet_license', 'clinic_name', 'clinic_address']
        labels = {
            'account_type': '帳號類型',
            'phone_number': '手機號碼',
            'vet_license': '獸醫證照',
            'vet_license_city': '執業執照縣市',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
        if self.instance:
            self.fields['clinic_name'].initial = self.instance.clinic_name
            self.fields['clinic_address'].initial = self.instance.clinic_address

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")
        return phone

    def clean_vet_license(self):
        file = self.cleaned_data.get('vet_license')
        if file:
            ext = file.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                raise forms.ValidationError("請上傳 PDF、JPG、JPEG 或 PNG 格式的檔案")
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("檔案大小不得超過 5MB")
        return file
    
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('account_type') == 'vet':
            if not cleaned_data.get('clinic_name'):
                self.add_error('clinic_name', '請填寫醫院／診所名稱')
            if not cleaned_data.get('clinic_address'):
                self.add_error('clinic_address', '請填寫醫院／診所地址')
        return cleaned_data


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
    account_type = forms.ChoiceField(choices=[('owner', '飼主'), ('vet', '獸醫')], label='帳號類型')
    username = forms.CharField(label='使用者名稱', max_length=150, required=True)
    phone_number = forms.CharField(label='手機號碼', required=True, max_length=20)
    vet_license_city = forms.ChoiceField(choices=[('', '請選擇縣市')] + CITY_CHOICES, label='執業執照縣市', required=False)
    vet_license = forms.FileField(label='獸醫證照', required=False,
    widget = forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}))
    clinic_name = forms.CharField(label="醫院／診所名稱", max_length=100, required=False)
    clinic_address = forms.CharField(label="醫院／診所地址", max_length=255, required=False)


    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('account_type') == 'vet':
            if not cleaned_data.get('clinic_name'):
                self.add_error('clinic_name', '請填寫醫院／診所名稱')
            if not cleaned_data.get('clinic_address'):
                self.add_error('clinic_address', '請填寫醫院／診所地址')
        return cleaned_data


# 一般註冊表單（含 email）
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


# 寵物資料管理用表單
class PetForm(forms.ModelForm):
    widget_attrs = {
        'class': 'form-control auto-grow-textarea',
        'rows': 1,
    }
    feature = forms.CharField(
        max_length=1000,
        widget=forms.Textarea(attrs={**widget_attrs,
            'id': 'id_feature_other',
            'class': 'form-control auto-grow-textarea',
            'placeholder': '請輸入個性特徵'})
    )
    species_other = forms.CharField(
        required=False,
        label="其他種類",
        widget=forms.TextInput(attrs={'id': 'id_species_other', 'placeholder': '請輸入寵物的種類'})
    )
    breed_other = forms.CharField(
        required=False,
        label="其他品種",
        widget=forms.TextInput(attrs={'id': 'id_breed_other', 'placeholder': '請輸入寵物的品種'})
    )
    class Meta:
        model = Pet
        fields = [
            'species', 'breed', 'breed_other','species_other','name', 'sterilization_status', 'chip',
            'gender', 'weight', 'feature', 'birth_date','picture',
        ]
        labels = {
            'species': '種類', 'breed': '品種', 'name': '名字',
            'sterilization_status': '絕育狀態', 'chip': '晶片號碼',
            'gender': '性別', 'weight': '體重（公斤）', 'feature': '個性特徵',
             'birth_date': '出生日期','picture': '圖片',
        }
        widgets = {
            'species': forms.HiddenInput(),
            'breed': forms.HiddenInput(),
            'name': forms.TextInput(attrs={'maxlength': 50}),
            'chip': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)

        # 🔧 設定 hidden input 的初始值
        self.fields['species'].widget = forms.HiddenInput()
        self.fields['breed'].widget = forms.HiddenInput()
        if self.instance and self.instance.pk:
            self.fields['species'].initial = self.instance.species
            self.fields['breed'].initial = self.instance.breed

        # 設定必填欄位
        for f in ['name', 'chip', 'weight', 'feature', 'birth_date', 'picture', 'sterilization_status', 'gender']:
            self.fields[f].required = True

        # 設定下拉選單
        self.fields['sterilization_status'].choices = [('', '請選擇')] + list(SterilizationStatus.choices)
        self.fields['gender'].choices = [('', '請選擇')] + list(Gender.choices)


    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is None or weight <= 0 or weight > 1000:
            raise forms.ValidationError("請輸入合理的體重（1~1000公斤）")
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
            raise forms.ValidationError("名字最多只能輸入 20 個字元。")
        return name

    def clean_chip(self):
        chip = self.cleaned_data.get('chip')
        if chip:
            # 排除自己（編輯時）
            qs = Pet.objects.filter(chip=chip)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            # 檢查是否已存在
            if qs.exists():
                raise forms.ValidationError("此晶片號碼已被其他寵物使用！")
        return chip

    def clean(self):
        cleaned_data = super().clean()
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

        return cleaned_data


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
#  體溫 編輯表單
class TemperatureEditForm(forms.Form):
    date = forms.DateField(label='紀錄時間',
        widget=forms.DateInput(attrs={'type': 'date'}),input_formats=['%Y-%m-%d'])
    temperature = forms.FloatField(label='體溫 (°C)')
    
    def clean_date(self):
        selected_date = self.cleaned_data['date']
        if selected_date > date.today():
            raise forms.ValidationError("日期不能超過今天")
        return selected_date

# 體重 編輯表單
class WeightEditForm(forms.Form):
    date = forms.DateField(label='紀錄時間',
            widget=forms.DateInput(attrs={'type': 'date'}),input_formats=['%Y-%m-%d'])
    weight = forms.FloatField(label='體重 (公斤)')
    def clean_date(self):
        selected_date = self.cleaned_data['date']
        if selected_date > date.today():
            raise forms.ValidationError("日期不能超過今天")
        return selected_date

# 獸醫 設定看診時段
class VetAppointmentForm(forms.ModelForm):
    time = forms.CharField(
        label="時間",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = VetAppointment
        fields = ['pet', 'vet', 'date', 'time', 'reason']
        widgets = {
            'pet': forms.HiddenInput(),
            'vet': forms.Select(attrs={'class': 'form-control searchable-select'}),
            'date': forms.DateInput(attrs={'type': 'date','class': 'form-control','min': date.today().isoformat()}),  # 限制最小可選日期為今天
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['vet'].queryset = Profile.objects.filter(account_type='vet')
            self.fields['pet'].queryset = Pet.objects.filter(owner=self.user)
        

# 疫苗表單
class VaccineRecordForm(forms.ModelForm):
    class Meta:
        model = VaccineRecord
        fields = ['name', 'date', 'location']  # 不含 pet
        labels = {'name':'疫苗品牌', 'date':'施打時間', 'location':'施打日期'},
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date','class': 'form-control',
                                           'max': date.today().isoformat()
            },format='%Y-%m-%d'),

        }
    def clean_date(self):
        date = self.cleaned_data['date']
        if date > date.today():
            raise forms.ValidationError("疫苗接種日期不能是未來")
        return date


# 驅蟲表單
class DewormRecordForm(forms.ModelForm):
    class Meta:
        model = DewormRecord
        fields = ['name', 'date', 'location']  # ✅ 不含 pet
        labels = {'name':'驅蟲品牌', 'date':'施打時間', 'location':'施打日期'},
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control',
                                           'max': date.today().isoformat()
                }, format='%Y-%m-%d'),
            }
        def clean_date(self):
            date = self.cleaned_data['date']
            if date > date.today():
                raise forms.ValidationError("驅蟲日期不能是未來")
            return date

# 報告表單
class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['title', 'pdf']
        labels = {'title':'標題', 'pdf':'pdf檔案'},
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

# 獸醫設定看診時段
class VetAvailableTimeForm(forms.ModelForm):
    class Meta:
        model = VetAvailableTime
        fields = ['weekday', 'time_slot', 'start_time', 'end_time']
        labels = {
            'weekday': '星期',
            'time_slot': '時段',
            'start_time': '開始時間',
            'end_time': '結束時間',
        }
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.vet = kwargs.pop('vet', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.vet:
            instance.vet = self.vet.profile
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        if start and end and start >= end:
            raise forms.ValidationError("結束時間必須晚於開始時間")
        return cleaned_data

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


#二手領養
class AdoptionForm(forms.ModelForm):
    widget_attrs = {
        'class': 'form-control auto-grow-textarea',
        'rows': 1,
    }
    feature_choice = forms.ChoiceField(
        choices=FEATURE_CHOICES,
        widget=forms.Select(attrs={'id': 'id_feature_choice','class': 'form-control',}),
        required=True,
        label="個性特徵"
    )
    feature_other = forms.CharField(
        required=False,
        label="其他個性",
        max_length=1000,
        widget=forms.Textarea(attrs={**widget_attrs,
            'id': 'id_feature_other',
            'class': 'form-control auto-grow-textarea',
            'placeholder': '請輸入個性特徵'})
    )
    physical_condition_choice = forms.ChoiceField(
        choices=PHYSICAL_CHOICES,
        widget=forms.Select(attrs={'id': 'id_physical_condition_choice', 'class': 'form-control'}),
        required=True,
        label="健康狀況"
    )
    physical_condition_other = forms.CharField(
        required=False,
        label="其他健康狀況",
        max_length=1000,
        widget=forms.Textarea(attrs={**widget_attrs,
            'id': 'id_physical_condition_other',
            'class': 'form-control auto-grow-textarea',
            'placeholder': '請輸入其他健康狀況'})
    )
    adoption_condition_choice = forms.ChoiceField(
        choices=ADOPTCONDITION_CHOICES,
        widget=forms.Select(attrs={'id': 'id_adoption_condition_choice', 'class': 'form-control'}),
        required=True,
        label="領養條件"
    )
    adoption_condition_other = forms.CharField(
        required=False,
        label="其他領養條件",
        max_length=1000,
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
        max_length=100,
        widget=forms.TextInput(attrs={'id': 'id_vaccine_other', 'placeholder': '請輸入其他疫苗'})
    )
    adopt_picture1 = forms.ImageField(
        required=False,  # 必填
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})  # 樣式
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
        fields = ['species', 'breed', 'breed_other','species_other','vaccine_other',
                  'name', 'sterilization_status', 'chip',
                    'gender', 'weight', 'vaccine','feature','birth_date',
                  'physical_condition','adoption_condition','adopt_place',
                  'phone', 'line_id',
                  'adopt_picture1','adopt_picture2','adopt_picture3','adopt_picture4',
                  "health_certificate", "vaccine_certificate",
                  ]
        widgets = {
            'species': forms.HiddenInput(),
            'breed': forms.HiddenInput(),
            "vaccine": forms.HiddenInput(),
            'name': forms.TextInput(attrs={'maxlength': 20,'placeholder':'請填寫寵物的名字','autocomplete': 'name'}),
            'chip': forms.TextInput(attrs={'class': 'form-control','maxlength': '15','placeholder':'請填寫寵物的晶片號碼','autocomplete': 'off'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'autocomplete': 'off'}, format='%Y-%m-%d'),
            'gender' : forms.Select(attrs={'class': 'form-select', 'autocomplete': 'off'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control','maxlength': 5,'placeholder':'請填寫寵物的重量（公斤/kg）','autocomplete': 'off'}),
            'feature': forms.Textarea(attrs={'class': 'form-control','maxlength': 300, 'placeholder':'請填寫寵物的個性特征'}),
            'physical_condition': forms.Textarea(attrs={'class': 'form-control','maxlength': 300, 'placeholder':'請填寫寵物的健康狀況'}),
            'adoption_condition': forms.Textarea(attrs={'class': 'form-control','maxlength': 300, 'placeholder':'請填寫寵物的領養條件'}),
            'adopt_place': forms.Select(attrs={'class': 'form-select','autocomplete': 'street-address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder':'請填寫手機號碼或line_id','autocomplete': 'tel'}),
            'line_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder':'請填寫手機號碼或line_id','autocomplete': 'off'}),

        }
        labels = {
            'species': '種類', 'breed': '品種', 'name': '名字',
            'sterilization_status': '絕育狀態', 'chip': '晶片號碼',
            'gender': '性別', 'weight': '體重（公斤）','vaccine':'疫苗', 'feature': '個性特徵',
            'birth_date': '出生日期','physical_condition': '健康狀況','adoption_condition': '領養條件',
            'adopt_place':'領養地點',
            'adopt_picture1': '圖片1',
            'adopt_picture2': '圖片2','adopt_picture3': '圖片3',
            'adopt_picture4': '圖片4',
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)

        # 🔧 設定 hidden input 的初始值
        self.fields['species'].widget = forms.HiddenInput()
        self.fields['breed'].widget = forms.HiddenInput()
        self.fields['vaccine'].widget = forms.HiddenInput()
        if self.instance and self.instance.pk:
            self.fields['species'].initial = self.instance.species
            self.fields['breed'].initial = self.instance.breed
            self.fields['vaccine'].initial = self.instance.vaccine


        # 🔧 不直接顯示模型欄位但仍要儲存
        self.fields['feature'].required = False
        self.fields['feature'].widget = forms.HiddenInput()
        self.fields['physical_condition'].required = False
        self.fields['physical_condition'].widget = forms.HiddenInput()
        self.fields['adoption_condition'].required = False
        self.fields['adoption_condition'].widget = forms.HiddenInput()

        for field_name in ['name', 'chip', 'weight', 'birth_date',
                           'adopt_place']:
            self.fields[field_name].required = True

        # 為 ChoiceField 手動插入空白選項
        self.fields['sterilization_status'].choices = [('', '請選擇')] + list(SterilizationStatus.choices)
        self.fields['gender'].choices = [('', '請選擇')] + list(Gender.choices)
        self.fields['feature_choice'].choices = [('', '請選擇')] + FEATURE_CHOICES
        self.fields['physical_condition_choice'].choices = [('', '請選擇')] + PHYSICAL_CHOICES
        self.fields['adoption_condition_choice'].choices = [('', '請選擇')] + ADOPTCONDITION_CHOICES
        self.fields['adopt_place'].choices = [('', '請選擇')] + REGION_CHOICES


        # 預設 feature_choice 和 feature_other 從 JSON 解析
        if self.instance and self.instance.feature:
            try:
                data = json.loads(self.instance.feature)
                if isinstance(data, dict):
                    self.initial['feature_choice'] = data.get('feature_choice', '')
                    self.initial['feature_other'] = data.get('feature_other', '')
                else:
                    # 若非 dict，當作其他
                    self.initial['feature_choice'] = '其他'
                    self.initial['feature_other'] = self.instance.feature
            except (json.JSONDecodeError, TypeError):
                self.initial['feature_choice'] = '其他'
                self.initial['feature_other'] = self.instance.feature


        # 回填 physical_condition_choice
        if self.instance and self.instance.physical_condition:
            try:
                condition_data = json.loads(self.instance.physical_condition)
                if isinstance(condition_data, dict):
                    self.initial['physical_condition_choice'] = condition_data.get('physical_condition_choice', '')
                    self.initial['physical_condition_other'] = condition_data.get('physical_condition_other', '')
                else:
                    # 如果不是 dict（可能只是單一字串），退回預設值
                    self.initial['physical_condition_choice'] = ''
                    self.initial['physical_condition_other'] = ''
            except (json.JSONDecodeError, TypeError):
                self.initial['physical_condition_choice'] = ''
                self.initial['physical_condition_other'] = ''

        # 回填 adoption_condition_choice
        if self.instance and self.instance.adoption_condition:
            try:
                condition_data = json.loads(self.instance.adoption_condition)
                if isinstance(condition_data, dict):
                    self.initial['adoption_condition_choice'] = condition_data.get('adoption_condition_choice',
                                                                                   '')
                    self.initial['adoption_condition_other'] = condition_data.get('adoption_condition_other',
                                                                                  '')
                else:
                    # 如果不是 dict（可能只是單一字串），退回預設值
                    self.initial['adoption_condition_choice'] = ''
                    self.initial['adoption_condition_other'] = ''
            except (json.JSONDecodeError, TypeError):
                self.initial['adoption_condition_choice'] = ''
                self.initial['adoption_condition_other'] = ''

        # 設定 date 預設為今天（僅在初次載入表單時）
        if not self.initial.get('birth_date'):
            self.initial['birth_date'] = date.today()

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is None or weight <= 0 or weight > 1000:
            raise forms.ValidationError("請輸入合理的體重（1~1000公斤）")
        return weight

    def clean_birth_date(self):
        record_date = self.cleaned_data.get('birth_date')
        if record_date and record_date > date.today():
            raise forms.ValidationError("日期不能是未來")
        return record_date

    def clean_chip(self):
        chip = self.cleaned_data.get('chip')
        if chip:
            # 排除自己（編輯時）
            qs = AdoptionPet.objects.filter(chip=chip)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            # 檢查是否已存在
            if qs.exists():
                raise forms.ValidationError("此晶片號碼已被其他寵物使用！")
        return chip

    def clean_adopt_picture1(self):
        picture = self.cleaned_data.get('adopt_picture1')
        # 從前端 hidden field 取得是否使用「從我的寵物帶入」
        use_pet_image = self.data.get("use_pet_image")  # "1" 表示使用
        my_pet_id = self.data.get("my_pet_id")

        # 如果編輯模式已有舊圖可以直接用
        if self.instance and self.instance.pk and (picture or self.instance.adopt_picture1):
            return picture or self.instance.adopt_picture1

        # 新增模式：沒有上傳檔案，也沒有從我的寵物帶入圖片 → 驗證失敗
        if not picture and not (use_pet_image == "1" and my_pet_id):
            raise forms.ValidationError("請上傳檔案")

        return picture

    def clean(self):
        cleaned_data = super().clean()

        # ✅ 電話或 LINE 檢查
        phone = cleaned_data.get('phone')
        line_id = cleaned_data.get('line_id')
        if not phone and not line_id:
            self.add_error('phone', "請填寫手機號碼或 LINE ID 至少一項")
            self.add_error('line_id', "請填寫 LINE ID 或手機號碼至少一項")

        # ✅ 特徵處理
        feature_choice = cleaned_data.get('feature_choice')
        feature_other = cleaned_data.get('feature_other', '')

        if not feature_choice:
            self.add_error('feature_choice', "這個欄位是必須的。")
            feature_data  = {'feature_choice': '', 'feature_other': ''}
        elif feature_choice == '其他':
            if not feature_other:
                self.add_error('feature_other', "請輸入其他特徵描述")
            feature_data = {
                'feature_choice': '其他',
                'feature_other': feature_other
            }
        else:
            feature_data = {
                'feature_choice': feature_choice,
                'feature_other': ''
            }
        #  不論是否有錯都先寫入（確保不報錯）
        cleaned_data['feature'] = json.dumps(feature_data, ensure_ascii=False)

        # ✅健康狀況處理
        physical_choice = cleaned_data.get('physical_condition_choice')
        physical_other = cleaned_data.get('physical_condition_other', '')

        if not physical_choice:
            self.add_error('physical_condition_choice', "這個欄位是必須的。")
            physical_data = {'physical_condition_choice': '', 'physical_condition_other': ''}
        elif physical_choice == '其他':
            if not physical_other:
                self.add_error('physical_condition_other', "請輸入其他健康狀況描述")
            physical_data = {
                'physical_condition_choice': '其他',
                'physical_condition_other': physical_other
            }
        else:
            physical_data = {
                'physical_condition_choice': physical_choice,
                'physical_condition_other': ''
            }
        # 檢查是否為字串，不是 dict 就不覆蓋
        if not isinstance(physical_data, dict):
            physical_data = {
                'physical_condition_choice': '',
                'physical_condition_other': ''
            }
        cleaned_data['physical_condition'] = json.dumps(physical_data, ensure_ascii=False)


        # ✅領養條件處理
        adoption_condition_choice = cleaned_data.get('adoption_condition_choice')
        adoption_condition_other = cleaned_data.get('adoption_condition_other', '')

        if not adoption_condition_choice:
            self.add_error('adoption_condition_choice', "這個欄位是必須的。")
            adoptcondition_data = {'adoption_condition_choice': '', 'adoption_condition_other': ''}
        elif adoption_condition_choice == '其他':
            if not adoption_condition_other:
                self.add_error('adoption_condition_other', "請輸入其他領養條件描述")
            adoptcondition_data = {
                'adoption_condition_choice': '其他',
                'adoption_condition_other': adoption_condition_other
            }
        else:
            adoptcondition_data = {
                'adoption_condition_choice': adoption_condition_choice,
                'adoption_condition_other': ''
            }
        # 檢查是否為字串，不是 dict 就不覆蓋
        if not isinstance(adoptcondition_data, dict):
            adoptcondition_data = {
                'adoption_condition_choice': '',
                'adoption_condition_other': ''
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



# 更改飼主
class TransferRequestForm(forms.Form):
    to_email = forms.EmailField(label='新飼主的郵箱',max_length=30)
    to_phone = forms.CharField(label='新飼主的手機號碼', max_length=10)

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user

    def clean(self):
        cleaned_data = super().clean()
        to_email = cleaned_data.get('to_email')
        to_phone = cleaned_data.get('to_phone')

        if self.current_user:
            # 檢查 email
            if to_email and to_email == self.current_user.email:
                self.add_error('to_email', '不能填寫自己的郵箱。')

            # 檢查手機號碼
            user_phone = None
            try:
                user_phone = self.current_user.profile.phone_number
            except Profile.DoesNotExist:
                user_phone = None

            if to_phone and user_phone and to_phone == user_phone:
                self.add_error('to_phone', '不能填寫自己的手機號碼。')

        return cleaned_data