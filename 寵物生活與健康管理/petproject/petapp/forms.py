# petapp/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Profile
from allauth.account.forms import SignupForm
import re

class CustomSignupForm(SignupForm):
    ACCOUNT_TYPE_CHOICES = [
        ('owner', '飼主'),
        ('vet', '獸醫'),
    ]
    account_type = forms.ChoiceField(choices=ACCOUNT_TYPE_CHOICES, label="帳號類型")

    def save(self, request):
        user = super().save(request)
        account_type = self.cleaned_data['account_type']
        Profile.objects.create(user=user, account_type=account_type)
        login(request, user)    # 自動登入
        return user

class EditProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, label='使用者名稱')
    first_name = forms.CharField(max_length=30, label='名字', required=False)
    last_name = forms.CharField(max_length=30, label='姓氏', required=False)

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

    vet_license_city = forms.ChoiceField(choices=CITY_CHOICES, label='執業執照縣市', required=False)
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
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            if not re.match(r'^09\d{8}$', phone):
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
