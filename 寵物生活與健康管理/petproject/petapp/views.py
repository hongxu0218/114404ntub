from django.shortcuts import render, redirect
from .forms import PetForm

# Create your views here.
from django.shortcuts import redirect, render, get_object_or_404
from .forms import RegisterForm
from django.contrib import messages
from .forms import PetForm
from .models import Pet
from datetime import date
import os

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

# 新增寵物資料
def add_pet(request):
    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('pet_list')  # 假設你有寵物列表頁
    else:
        form = PetForm()
    return render(request, 'pet_info/add_pet.html', {'form': form})

# 飼養者主頁，顯示寵物資料
def pet_list(request):
    pets = Pet.objects.all()
    return render(request, 'pet_info/pet_list.html', {'pets': pets})

# 編輯寵物資料
def edit_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES, instance=pet)

        if form.is_valid():
            # 檢查是否需要移除圖片
            if 'remove_picture' in request.POST:
                if pet.picture:
                    pet.picture.delete()  # 刪除圖片文件
                pet.picture = None  # 清除圖片欄位
                pet.save()

            form.save()  # 保存表單
            return redirect('pet_list')  # 假設你有一個 'pet_list' 頁面
    else:
        form = PetForm(instance=pet)

    return render(request, 'pet_info/edit_pet.html', {'form': form, 'pet': pet})

# 刪除寵物資料
def delete_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        pet.delete()
        return redirect('pet_list')

    return render(request, 'pet_info/delete_pet.html', {'pet': pet})