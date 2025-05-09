# petapp/forms.py

# 載入 Django 表單相關模組
from django import forms
from django.contrib.auth.models import User  # 使用者模型
from django.contrib.auth.forms import UserCreationForm  # 使用者註冊表單
from django.contrib.auth import login  # 登入函式
from .models import Profile  # 匯入自定義的使用者 Profile 模型
from allauth.account.forms import SignupForm  # allauth 的註冊表單基底
import re  # 正規表示式模組，用來驗證手機與檔案格式等

class CustomSignupForm(SignupForm):
    # 帳號類型選項（飼主或獸醫）
    ACCOUNT_TYPE_CHOICES = [
        ('owner', '飼主'),
        ('vet', '獸醫'),
    ]

    # 帳號類型與手機號碼欄位
    account_type = forms.ChoiceField(choices=ACCOUNT_TYPE_CHOICES, label="帳號類型")
    phone_number = forms.CharField(max_length=20, label="手機號碼", required=True)

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^09\d{8}$', phone):
            raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")
        return phone

    def save(self, request):
        user = super().save(request)
        account_type = self.cleaned_data['account_type']
        phone_number = self.cleaned_data['phone_number']

        # 建立對應的 Profile
        Profile.objects.create(
            user=user,
            account_type=account_type,
            phone_number=phone_number,
        )

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        return user

class EditProfileForm(forms.ModelForm):
    # 顯示基本資料欄位：使用者名稱、名字、姓氏
    username = forms.CharField(max_length=150, label='使用者名稱')
    first_name = forms.CharField(max_length=30, label='名字', required=False)
    last_name = forms.CharField(max_length=30, label='姓氏', required=False)

    # 可選的縣市選單（用於獸醫執照所在地）
    CITY_CHOICES = [
        ('台北市', '台北市'),
        ('新北市', '新北市'),
        ('桃園市', '桃園市'),
        ('台中市', '台中市'),
        ('台南市', '台南市'),
        ('高雄市', '高雄市'),
        ('基隆市', '基隆市'),
        ('新竹市', '新竹市'),
        ('嘉義市', '嘉義市'),
        ('新竹縣', '新竹縣'),
        ('苗栗縣', '苗栗縣'),
        ('彰化縣', '彰化縣'),
        ('南投縣', '南投縣'),
        ('雲林縣', '雲林縣'),
        ('嘉義縣', '嘉義縣'),
        ('屏東縣', '屏東縣'),
        ('宜蘭縣', '宜蘭縣'),
        ('花蓮縣', '花蓮縣'),
        ('台東縣', '台東縣'),
        ('澎湖縣', '澎湖縣'),
        ('金門縣', '金門縣'),
        ('連江縣', '連江縣'),
    ]

    # 執業執照縣市（可選填）
    vet_license_city = forms.ChoiceField(choices=CITY_CHOICES, label='執業執照縣市', required=False)

    # 獸醫證照上傳欄位（可選填）
    vet_license = forms.FileField(label='獸醫證照', required=False, widget=forms.FileInput)

    class Meta:
        model = Profile
        fields = ['account_type', 'phone_number', 'vet_license_city', 'vet_license']
        labels = {
            'account_type': '帳號類型',
            'phone_number': '手機號碼',
            'vet_license': '獸醫證照',
            'vet_license_city': '執業執照縣市',
        }

    def __init__(self, *args, **kwargs):
        # 接收傳入的 user 物件
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 若有傳入 user，則預設填入對應資料
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # 使用正規表示式驗證手機格式（台灣手機格式為 09 開頭 + 8 碼數字）
            if not re.match(r'^09\d{8}$', phone):
                raise forms.ValidationError("請輸入有效的台灣手機號碼（格式：09xxxxxxxx）")
        return phone

    def clean_vet_license(self):
        file = self.cleaned_data.get('vet_license')
        if file:
            # 驗證檔案副檔名是否為允許的格式
            ext = file.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                raise forms.ValidationError("請上傳 PDF、JPG、JPEG 或 PNG 格式的檔案")
            # 驗證檔案大小是否超過 5MB
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("檔案大小不得超過 5MB")
        return file

    def save(self, commit=True):
        # 儲存 Profile 表單欄位資料，但先不 commit 到資料庫
        profile = super().save(commit=False)
        if commit:
            # 儲存 profile 資料
            profile.save()

            # 同步更新 User 模型中的基本資料欄位
            if self.user:
                self.user.username = self.cleaned_data['username']
                self.user.first_name = self.cleaned_data['first_name']
                self.user.last_name = self.cleaned_data['last_name']
                self.user.save()
        return profile
