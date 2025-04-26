from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import RegisterForm, PetForm
from .models import Pet

# 首頁
def home(request):
    return render(request, 'home.html')

# 使用者註冊
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '註冊成功，請登入。')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'account/register.html', {'form': form})

# 登出成功頁面
def logout_success(request):
    return render(request, 'account/logout_success.html')

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
