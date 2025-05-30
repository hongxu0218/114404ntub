# petapp/forms.py 
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Profile, Pet, DailyRecord, VetAppointment, VaccineRecord, DewormRecord, Report, VetAvailableTime, WEEKDAYS, TIME_SLOTS, MedicalRecord
from allauth.account.forms import SignupForm
import re
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
        super().__init__(*args, **kwargs)
        self.fields['picture'].required = True
        for field_name in ['breed', 'name', 'chip', 'weight', 'feature']:
            self.fields[field_name].required = True
            # 設定 date 預設為今天（僅在初次載入表單時）
        if not self.initial.get('date'):
            self.initial['date'] = date.today()

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
            qs = Pet.objects.filter(name=name)
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
