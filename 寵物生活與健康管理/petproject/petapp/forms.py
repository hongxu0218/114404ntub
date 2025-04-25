from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Pet
from datetime import date

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = [
                    'species', 'breed', 'name', 'sterilization_status', 'chip',
                    'date_of_birth', 'gender', 'weight', 'feature', 'picture'
                ]

        labels = {
            'species': '種類',
            'breed': '品種',
            'name': '名字',
            'sterilization_status': '絕育狀態',
            'chip': '晶片號碼',
            'date_of_birth': '出生日期',
            'gender': '性別',
            'weight': '體重（公斤）',
            'feature': '特徵',
            'picture': '圖片',


        }
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': date.today().strftime('%Y-%m-%d'),
                'required': 'required',
                'placeholder': '年/月/日'
            }),
            'chip': forms.NumberInput(attrs={'class': 'form-control', 'required': 'required'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'required': 'required'}),
            'feature': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': 'required'}),
            'picture': forms.ClearableFileInput(attrs={'class': 'form-control'})
            }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 確保圖片欄位為必填
        self.fields['picture'].required = True

        def clean_picture(self):
            picture = self.cleaned_data.get('picture')
            if not picture and self.instance.picture is None:
                raise forms.ValidationError("請選擇圖片")
            return picture

        for field_name in ['breed', 'name', 'chip', 'weight', 'feature']:
            self.fields[field_name].required = True
            self.fields[field_name].widget.attrs.update({'required': 'required'})

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise forms.ValidationError("不能選擇未來日期")
        return dob

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is None:
            raise forms.ValidationError("請輸入體重")
        if weight <= 0:
            raise forms.ValidationError("數字過小，請重新輸入（1000公斤以內）")
        if weight > 1000:
            raise forms.ValidationError("數字過大，請重新輸入（1000公斤以內）")
        return weight
