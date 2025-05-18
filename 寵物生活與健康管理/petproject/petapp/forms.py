# petapp/forms.py 
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Profile, Pet, DailyRecord, VetAppointment
from allauth.account.forms import SignupForm
import re
from datetime import date, time, datetime 

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
    year_of_birth = forms.IntegerField(required=True, label='出生年')
    month_of_birth = forms.IntegerField(required=True, label='出生月')
    day_of_birth = forms.IntegerField(required=True, label='出生日')

    class Meta:
        model = Pet
        fields = [
            'species', 'breed', 'name', 'sterilization_status', 'chip',
            'gender', 'weight', 'feature', 'picture',
            'year_of_birth', 'month_of_birth', 'day_of_birth'
        ]
        labels = {
            'species': '種類', 'breed': '品種', 'name': '名字',
            'sterilization_status': '絕育狀態', 'chip': '晶片號碼',
            'gender': '性別', 'weight': '體重（公斤）', 'feature': '特徵',
            'picture': '圖片', 'year_of_birth': '年', 'month_of_birth': '月', 'day_of_birth': '日'
        }
        widgets = {
            'chip': forms.NumberInput(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'feature': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'year_of_birth': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '年'}),
            'month_of_birth': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '月'}),
            'day_of_birth': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '日'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['picture'].required = True
        for field_name in ['breed', 'name', 'chip', 'weight', 'feature']:
            self.fields[field_name].required = True

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is None or weight <= 0 or weight > 1000:
            raise forms.ValidationError("請輸入合理的體重（1~1000公斤）")
        return weight

    def clean_year_of_birth(self):
        year = self.cleaned_data.get('year_of_birth')
        if year is None or year < 1900 or year > date.today().year:
            raise forms.ValidationError("請輸入有效年份")
        return year

    def clean_month_of_birth(self):
        month = self.cleaned_data.get('month_of_birth')
        if month is None or month < 1 or month > 12:
            raise forms.ValidationError("請輸入有效月份")
        return month

    def clean_day_of_birth(self):
        day = self.cleaned_data.get('day_of_birth')
        if day is None or day < 1 or day > 31:
            raise forms.ValidationError("請輸入有效日期")
        return day

    def clean(self):
        cleaned_data = super().clean()
        try:
            dob = date(
                cleaned_data['year_of_birth'],
                cleaned_data['month_of_birth'],
                cleaned_data['day_of_birth']
            )
            if dob > date.today():
                raise forms.ValidationError('出生日期不能是未來')
        except Exception:
            raise forms.ValidationError('請輸入正確的出生日期')
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
    

class VetAppointmentForm(forms.ModelForm):
    time = forms.ChoiceField(
        choices=[(t.strftime("%H:%M:%S"), label) for t, label in AVAILABLE_TIME_CHOICES],
        label="時間",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = VetAppointment
        fields = ['vet', 'date', 'time', 'reason']
        labels = {
            'pet': '寵物',
            'vet': '預約獸醫',
            'date': '日期',
            'time': '時間',
            'reason': '預約原因'
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_time(self):
        raw_time = self.cleaned_data['time']
        allowed = [t.strftime("%H:%M:%S") for t, _ in AVAILABLE_TIME_CHOICES]
        if raw_time not in allowed:
            raise forms.ValidationError("請選擇有效時段")
        return raw_time


    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # 只列出使用者自己的寵物
            self.fields['pet'].queryset = Pet.objects.filter(owner=user)
        # 只列出已驗證的獸醫
        self.fields['vet'].label_from_instance = lambda obj: f"{obj.clinic_name or '未填診所'}（{obj.user.last_name}{obj.user.first_name}）"
        self.fields['vet'].widget.attrs.update({'class': 'form-control searchable-select'})
        self.fields['vet'].queryset = Profile.objects.filter(account_type='vet', is_verified_vet=True)

        # 根據前端提交值即時過濾已被預約的時段
        vet_id = self.data.get('vet') or self.initial.get('vet')
        date_val = self.data.get('date') or self.initial.get('date')

        try:
            if vet_id and date_val:
                # 轉為 date 物件
                parsed_date = datetime.strptime(date_val, "%Y-%m-%d").date()
                
                booked_times = VetAppointment.objects.filter(
                    vet_id=vet_id,
                    date=parsed_date
                ).values_list('time', flat=True)

                self.fields['time'].choices = [
                    (t.strftime("%H:%M:%S"), label)
                    for t, label in AVAILABLE_TIME_CHOICES
                    if t not in booked_times
                ]
            else:
                self.fields['time'].choices = [
                    (t.strftime("%H:%M:%S"), label)
                    for t, label in AVAILABLE_TIME_CHOICES
                ]
        except Exception as e:
            print("預約時段載入錯誤：", e)
            self.fields['time'].choices = [
                (t.strftime("%H:%M:%S"), label)
                for t, label in AVAILABLE_TIME_CHOICES
            ]
