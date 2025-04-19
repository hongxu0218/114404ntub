from django.shortcuts import render

# Create your views here.
from django.shortcuts import redirect
from .forms import RegisterForm
from django.contrib import messages

def home(request):
    return render(request, 'home.html')

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '註冊成功，請登入。')
            return redirect('login')  # 須先設定 login 頁面或內建 login URL
    else:
        form = RegisterForm()
    return render(request, 'account/register.html', {'form': form})

def logout_success(request):
    return render(request, 'account/logout_success.html')