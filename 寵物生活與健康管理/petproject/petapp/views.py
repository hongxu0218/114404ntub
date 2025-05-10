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
from allauth.socialaccount.views import SignupView as SocialSignupView  # 新增


def home(request):
    return render(request, 'pages/home.html')

class CustomSignupView(SignupView):
    def get(self, request, *args, **kwargs):
        if 'signup_redirect_message' in request.session:
            del request.session['signup_redirect_message']
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user

        print("[DEBUG] session account_type =", self.request.session.get('account_type'))
        print("[DEBUG] session phone_number =", self.request.session.get('phone_number'))

        account_type = self.request.session.pop('account_type', None)
        phone_number = self.request.session.pop('phone_number', None)
        vet_license_city = self.request.session.pop('vet_license_city', '')
        vet_license_name = self.request.session.pop('vet_license_name', None)
        vet_license_content = self.request.session.pop('vet_license_content', None)

        profile, created = Profile.objects.update_or_create(
            user=user,
            defaults={
                'account_type': account_type or self.request.POST.get('account_type'),
                'phone_number': phone_number,
                'vet_license_city': vet_license_city,
            }
        )
        print("[DEBUG] 建立或更新 Profile：", profile, "建立狀態：", created)

        if vet_license_name and vet_license_content:
            from django.core.files.base import ContentFile
            profile.vet_license.save(
                vet_license_name,
                ContentFile(vet_license_content.encode('ISO-8859-1'))
            )
            print("[DEBUG] 已上傳檔案到 profile.vet_license：", vet_license_name)

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

            Profile.objects.create(
                user=user,
                account_type=form.cleaned_data['account_type'],
                phone_number=form.cleaned_data['phone_number'],
                vet_license_city=form.cleaned_data.get('vet_license_city'),
                vet_license=form.cleaned_data.get('vet_license'),
            )

            # 加上 success_url
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
    profile = request.user.profile
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            request.user.refresh_from_db()
            messages.success(request, '帳號資料已更新')
            return redirect('home')
    else:
        form = EditProfileForm(instance=profile, user=request.user)
        form.user = request.user
    return render(request, 'account/edit.html', {'form': form})


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