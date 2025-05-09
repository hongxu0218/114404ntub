# petapp/views.py
from django.shortcuts import render

# Create your views here.
from django.shortcuts import redirect
from .models import Profile
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django import forms
from .forms import EditProfileForm
from allauth.account.views import SignupView
from allauth.socialaccount.providers.google.views import OAuth2LoginView


def home(request):
    return render(request, 'pages/home.html')

class CustomSignupView(SignupView):
    def get(self, request, *args, **kwargs):
        if 'signup_redirect_message' in request.session:
            del request.session['signup_redirect_message']
        return super().get(request, *args, **kwargs)
    def form_valid(self, form):
        # 呼叫原本的邏輯完成註冊 + 自動登入
        response = super().form_valid(form)
        # 取得 account_type 並建立 Profile
        account_type = self.request.POST.get('account_type')
        Profile.objects.update_or_create(user=self.user, defaults={'account_type': account_type})
        return redirect('home')

@login_required
def dashboard_redirect(request):
    try:
        if request.user.is_staff:
            return redirect('admin:index')  # 管理員導向 admin
        profile = request.user.profile
        if not profile.account_type:
            return redirect('select_account_type')
        elif profile.account_type == 'vet':
            if not profile.is_verified_vet:
                return render(request, 'pages/pending_verification.html')
            return redirect('vet_dashboard')
        else:
            return redirect('owner_dashboard')
    except ObjectDoesNotExist:
        messages.error(request, "此帳號尚未設定身分資料，請聯繫管理員。")
        return redirect('home')


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
        return redirect('/accounts/google/login/?next=/accounts/signup/')  # Allauth 內建 Google 起始點
    return render(request, 'pages/select_account_type.html')