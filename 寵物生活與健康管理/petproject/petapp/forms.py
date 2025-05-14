from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Pet
import datetime
from datetime import date

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


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
            'species': '種類',
            'breed': '品種',
            'name': '名字',
            'sterilization_status': '絕育狀態',
            'chip': '晶片號碼',
            'gender': '性別',
            'weight': '體重（公斤）',
            'feature': '特徵',
            'picture': '圖片',
            'year_of_birth': '年',
            'month_of_birth': '月',
            'day_of_birth': '日'
        }
        widgets = {
            'chip': forms.NumberInput(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'feature': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'year_of_birth': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '年'}),
            'month_of_birth': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '月'}),
            'day_of_birth': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '日'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['picture'].required = True
        for field_name in ['breed', 'name', 'chip', 'weight', 'feature']:
            self.fields[field_name].required = True

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is None:
            raise forms.ValidationError("請輸入體重")
        if weight <= 0:
            raise forms.ValidationError("數字過小，請重新輸入（1000公斤以內）")
        if weight > 1000:
            raise forms.ValidationError("數字過大，請重新輸入（1000公斤以內）")
        return weight

    def clean_year_of_birth(self):
        year = self.cleaned_data.get('year_of_birth')
        if year is None:
            raise forms.ValidationError("請輸入出生年份")
        if year < 1900 or year > date.today().year:
            raise forms.ValidationError("請輸入有效年份")
        return year

    def clean_month_of_birth(self):
        month = self.cleaned_data.get('month_of_birth')
        if month is None:
            raise forms.ValidationError("請輸入出生月份")
        if month < 1 or month > 12:
            raise forms.ValidationError("請輸入有效月份")
        return month

    def clean_day_of_birth(self):
        day = self.cleaned_data.get('day_of_birth')
        if day is None:
            raise forms.ValidationError("請輸入出生日期")
        if day < 1 or day > 31:
            raise forms.ValidationError("請輸入有效日期")
        return day

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get('year_of_birth')
        month = cleaned_data.get('month_of_birth')
        day = cleaned_data.get('day_of_birth')

        # 如果三個都填了，再驗證組合起來是否為合法的日期
        if year and month and day:
            try:
                dob = date(year, month, day)
            except ValueError:
                raise forms.ValidationError('請輸入正確的出生日期')
            if dob > date.today():
                raise forms.ValidationError('出生日期不能是未來')

        return cleaned_data
