# petapp/views.py
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from .models import Profile
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django import forms
from .forms import EditProfileForm, SocialSignupExtraForm
from allauth.account.views import SignupView
from allauth.socialaccount.providers.google.views import OAuth2LoginView
from allauth.socialaccount.views import SignupView as SocialSignupView  
from django.http import JsonResponse

from django.shortcuts import get_object_or_404
from .models import Profile, Pet
from .forms import EditProfileForm, SocialSignupExtraForm, PetForm


def home(request):
    return render(request, 'pages/home.html')

class CustomSignupView(SignupView):
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        return redirect('/')


class CustomSocialSignupView(SocialSignupView):
    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user

        account_type = self.request.session.pop('account_type', None)
        phone_number = self.request.session.pop('phone_number', None)
        vet_license_city = self.request.session.pop('vet_license_city', '')
        vet_license_name = self.request.session.pop('vet_license_name', None)
        vet_license_content = self.request.session.pop('vet_license_content', None)

        profile, created = Profile.objects.update_or_create(
            user=user,
            defaults={
                'account_type': account_type,
                'phone_number': phone_number,
                'vet_license_city': vet_license_city,
            }
        )

        if vet_license_name and vet_license_content:
            from django.core.files.base import ContentFile
            profile.vet_license.save(
                vet_license_name,
                ContentFile(vet_license_content.encode('ISO-8859-1'))
            )
        return redirect('home')

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

            # 建立 Profile
            profile = Profile.objects.create(
                user=user,
                account_type=form.cleaned_data['account_type'],
                phone_number=form.cleaned_data['phone_number'],
                vet_license_city=form.cleaned_data.get('vet_license_city'),
                vet_license=form.cleaned_data.get('vet_license'),
            )

            # 寄信給管理員
            if profile.account_type == 'vet':
                from django.core.mail import send_mail
                from django.conf import settings

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
                send_mail(
                    subject,
                    message,
                    '毛日好(Paw&Day)" <{}>'.format(settings.DEFAULT_FROM_EMAIL),
                    [settings.ADMIN_EMAIL],
                    fail_silently=False
                )
                print("✅ 已寄出獸醫帳號通知信")

            # 🔚 Allauth 內建的完成註冊方法
            from allauth.account.utils import complete_signup
            from allauth.account import app_settings
            from django.conf import settings

            return complete_signup(
                request, user, app_settings.EMAIL_VERIFICATION, success_url=settings.LOGIN_REDIRECT_URL
            )

    else:
        form = SocialSignupExtraForm()

    return render(request, 'account/social_signup_extra.html', {'form': form})



@login_required
def select_account_type(request):
    if request.method == 'POST':
        account_type = request.POST.get('account_type')
        profile = request.user.profile
        profile.account_type = account_type
        profile.save()
        return redirect('dashboard')
    return render(request, 'pages/select_account_type.html')


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

    return render(request, 'account/edit.html', {
        'form': form,
    })

@login_required
def owner_dashboard(request):
    return render(request, 'dashboards/owner_dashboard.html')


@login_required
def vet_dashboard(request):
    profile = request.user.profile
    if not profile.is_verified_vet:
        messages.warning(request, "您的獸醫帳號尚未通過管理員驗證。請稍後再試。")
        return redirect('home')
    return render(request, 'dashboards/vet_dashboard.html')

def logout_success(request):
    return render(request, 'account/logout_success.html')

def select_type_then_social_login(request):
    if request.method == 'POST':
        request.session['pending_account_type'] = request.POST.get('account_type')
        return redirect('/accounts/google/login/?next=/accounts/social/signup/extra/')
    return render(request, 'pages/select_account_type.html')

def dashboard_redirect(request):
    profile = request.user.profile
    if profile.account_type == 'owner':
        return redirect('owner_dashboard')
    elif profile.account_type == 'vet':
        return redirect('vet_dashboard')
    else:
        return redirect('home')
    
def mark_from_signup_and_redirect(request):
    request.session['from_signup'] = True
    return redirect('/accounts/google/login/?next=/accounts/social/signup/extra/')

def clear_signup_message(request):
    request.session.pop('signup_redirect_message', None)
    return JsonResponse({'cleared': True})

# 新增寵物資料
def add_pet(request):
    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('pet_list')
    else:
        form = PetForm()
    return render(request, 'pet_info/add_pet.html', {'form': form})


# 顯示寵物列表
def pet_list(request):
    pets = Pet.objects.all()
    return render(request, 'pet_info/pet_list.html', {'pets': pets})

# 編輯寵物資料（圖片更新時，自動刪除舊圖由 django-cleanup 處理）
def edit_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES, instance=pet)
        if form.is_valid():
            form.save()
            return redirect('pet_list')
    else:
        form = PetForm(instance=pet)

    return render(request, 'pet_info/edit_pet.html', {'form': form, 'pet': pet})

# 刪除寵物資料（圖片由 django-cleanup 自動刪除）
def delete_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        pet.delete()
        return redirect('pet_list')

    return render(request, 'pet_info/delete_pet.html', {'pet': pet})
