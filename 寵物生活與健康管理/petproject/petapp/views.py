# petapp/views.py 

from collections import defaultdict
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from datetime import datetime,date
from calendar import monthrange
import calendar
from django.utils.timezone import localtime

from django.conf import settings
from .models import Profile, Pet, DailyRecord , PetLocation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import EditProfileForm, SocialSignupExtraForm, PetForm, TemperatureEditForm, WeightEditForm
from allauth.account.views import SignupView
from allauth.socialaccount.views import SignupView as SocialSignupView

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_http_methods
from .utils import get_temperature_data, get_weight_data
import json

from django.core.paginator import Paginator
from django.db.models import Q

from dateutil.relativedelta import relativedelta  # 需要安裝 python-dateutil

# 首頁

def home(request):
    return render(request, 'pages/home.html')  # 渲染首頁

# 使用者一般註冊流程覆寫
class CustomSignupView(SignupView):
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)  # 繼承原始邏輯

    def form_valid(self, form):
        response = super().form_valid(form)
        return redirect('/')  # 註冊成功導向首頁

# Google 社群註冊流程（含 session 取資料）
class CustomSocialSignupView(SocialSignupView):
    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user

        # 取出註冊階段儲存的 session 資料
        account_type = self.request.session.pop('account_type', None)
        phone_number = self.request.session.pop('phone_number', None)
        vet_license_city = self.request.session.pop('vet_license_city', '')
        vet_license_name = self.request.session.pop('vet_license_name', None)
        vet_license_content = self.request.session.pop('vet_license_content', None)

        # 建立或更新 Profile 資料
        profile, created = Profile.objects.update_or_create(
            user=user,
            defaults={
                'account_type': account_type,
                'phone_number': phone_number,
                'vet_license_city': vet_license_city,
            }
        )

        # 儲存獸醫證照檔案（若有）
        if vet_license_name and vet_license_content:
            from django.core.files.base import ContentFile
            profile.vet_license.save(
                vet_license_name,
                ContentFile(vet_license_content.encode('ISO-8859-1'))
            )

        return redirect('home')  # 註冊完成導向首頁

# Google 註冊補充資料表單

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

            # 建立 Profile 資料
            profile = Profile.objects.create(
                user=user,
                account_type=form.cleaned_data['account_type'],
                phone_number=form.cleaned_data['phone_number'],
                vet_license_city=form.cleaned_data.get('vet_license_city'),
                vet_license=form.cleaned_data.get('vet_license'),
                clinic_name=form.cleaned_data.get('clinic_name'),
                clinic_address=form.cleaned_data.get('clinic_address'),
            )

            # 寄信通知管理員（若為獸醫帳號）
            if profile.account_type == 'vet':
                from django.core.mail import send_mail

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
                send_mail(subject, message, '毛日好(Paw&Day) <{}>'.format(settings.DEFAULT_FROM_EMAIL),
                          [settings.ADMIN_EMAIL], fail_silently=False)

            from allauth.account.utils import complete_signup
            from allauth.account import app_settings

            return complete_signup(
                request, user, app_settings.EMAIL_VERIFICATION,
                success_url=settings.LOGIN_REDIRECT_URL
            )
    else:
        form = SocialSignupExtraForm()

    return render(request, 'account/social_signup_extra.html', {'form': form})

# 註冊後選擇帳號類型
@login_required
def select_account_type(request):
    if request.method == 'POST':
        account_type = request.POST.get('account_type')
        profile = request.user.profile
        profile.account_type = account_type
        profile.save()
        return redirect('dashboard')
    return render(request, 'pages/select_account_type.html')

# 編輯個人檔案資料
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

    return render(request, 'account/edit.html', {'form': form})

# 飼主主控台
@login_required
def owner_dashboard(request):
    return render(request, 'dashboards/owner_dashboard.html')

# 獸醫主控台（需審核通過）
@login_required
def vet_dashboard(request):
    profile = request.user.profile
    if not profile.is_verified_vet:
        messages.warning(request, "您的獸醫帳號尚未通過管理員驗證。請稍後再試。")
        return redirect('home')
    return render(request, 'dashboards/vet_dashboard.html')

# 登出成功頁面

def logout_success(request):
    return render(request, 'account/logout_success.html')

# Google 登入前選擇帳號類型

def select_type_then_social_login(request):
    if request.method == 'POST':
        request.session['pending_account_type'] = request.POST.get('account_type')
        return redirect('/accounts/google/login/?next=/accounts/social/signup/extra/')
    return render(request, 'pages/select_account_type.html')

# 根據帳號類型導向對應主控台

def dashboard_redirect(request):
    profile = request.user.profile
    if profile.account_type == 'owner':
        return redirect('owner_dashboard')
    elif profile.account_type == 'vet':
        return redirect('vet_dashboard')
    else:
        return redirect('home')

# 標記從註冊流程進入

def mark_from_signup_and_redirect(request):
    request.session['from_signup'] = True
    return redirect('/accounts/google/login/?next=/accounts/social/signup/extra/')

# 清除註冊提示訊息

def clear_signup_message(request):
    request.session.pop('signup_redirect_message', None)
    return JsonResponse({'cleared': True})

# 新增寵物資料
def add_pet(request):
    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES)
        if form.is_valid():
            pet = form.save()

            # 🔽 初始化 6 筆分類 DailyRecord（日期可為 today，content 可為空）
            categories = ['temperature', 'weight', 'diet', 'exercise', 'allergen', 'other']

            for cat in categories:
                DailyRecord.objects.create(
                    pet=pet,
                    category=cat,
                    content='',
                    date=date.today()
                )
            return redirect('pet_list')
    else:
        form = PetForm()
    return render(request, 'pet_info/add_pet.html', {'form': form})


# 寵物列表

def pet_list(request):
    pets = Pet.objects.all()
    return render(request, 'pet_info/pet_list.html', {'pets': pets})

# 編輯寵物

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

# 刪除寵物

def delete_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    if request.method == 'POST':
        pet.delete()
        return redirect('pet_list')
    return render(request, 'pet_info/delete_pet.html', {'pet': pet})

# 健康紀錄列表
def health_rec(request):
    records = DailyRecord.objects.select_related('pet').order_by('date')
    grouped_records = []
    pet_map = defaultdict(list)

    for record in records:
        pet_map[record.pet].append(record)

    for pet, recs in pet_map.items():
        grouped_records.append({
            'pet': pet,
            'records': recs,
        })

    pet_temperatures = {}
    pet_weights = {}

    # 取得當前月份以及過去 2 個月（共 3 個月）的體溫資料
    months = [datetime.now() - relativedelta(months=i) for i in range(3)]

    for pet in pet_map.keys():
        temp_by_month = {}
        weight_by_month = {}
        for dt in months:
            year, month = dt.year, dt.month
            key = f"{year}-{str(month).zfill(2)}"

            temp_records = get_temperature_data(pet, year, month)
            weight_records = get_weight_data(pet, year, month)

            temp_by_month[key] = [
                {'date': rec['date'], 'temperature': rec['temperature']}
                for rec in temp_records
            ]
            weight_by_month[key] = [
                {'date': rec['date'], 'weight': rec['weight']}
                for rec in weight_records
            ]
        pet_temperatures[pet.id] = temp_by_month
        pet_weights[pet.id] = weight_by_month

    return render(request, 'health_records/health_rec.html', {
        'grouped_records': grouped_records,
        'pet_temperatures': pet_temperatures,
        'pet_weights': pet_weights,
    })
    
# 新增每日健康紀錄
@require_POST
@csrf_exempt
def add_daily_record(request, pet_id):
    data = json.loads(request.body)
    category = data.get('category')
    content = data.get('content')
    if not category or not content:
        return JsonResponse({'success': False, 'message': '缺少欄位'})
    pet = get_object_or_404(Pet, id=pet_id)
    record = DailyRecord.objects.create(
        pet=pet,
        category=category,
        content=content,
        date=date.today()
    )
    return JsonResponse({
        'success': True,
        'record_id': record.id,
        'category': category,
        'content': content,
        'date': record.date.isoformat()
    })

# 儲存每日健康紀錄（非綁定 pet_id）
@csrf_exempt
@require_http_methods(["POST"])
def save_daily_record(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'})
    pet_id = data.get('pet_id')
    category = data.get('category')
    content = data.get('content')
    if not pet_id or not category or not content:
        return JsonResponse({'status': 'error', 'message': 'Missing required fields'})
    try:
        pet = Pet.objects.get(id=pet_id)
    except Pet.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Pet not found'})
    record = DailyRecord.objects.create(
        pet=pet,
        category=category,
        content=content,
        date=date.today()
    )
    return JsonResponse({
        'success': True,
        'record_id': record.id,
        'category': category,
        'content': content,
        'date': record.date.isoformat()
    })

# 刪除每日健康紀錄
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_daily_record(request, pet_id):
    try:
        data = json.loads(request.body)
        record_id = data['record_id']
        record = DailyRecord.objects.get(id=record_id, pet_id=pet_id)
        record.delete()
        return JsonResponse({'success': True})
    except DailyRecord.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Record not found'}, status=404)


# 體溫頁面
def tem_rec(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    # 預設為今天的年月
    today = datetime.today()
    year, month = today.year, today.month

    # 嘗試從網址取得指定月份
    month_str = request.GET.get('month')
    if month_str:
        try:
            year, month = map(int, month_str.split('-'))
        except ValueError:
            pass  # 若格式錯誤則維持今天年月

    is_current_month = (year == today.year and month == today.month)

    # 當月的起始與結束日期
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    # 篩選當月資料
    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='temperature',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    # 整理資料
    records = []
    for rec in raw_records:
        try:
            temp_value = float(rec.content)
        except ValueError:
            continue
        records.append({
            'id': rec.id,
            'date': rec.date.strftime('%Y-%m-%d'),
            'datetime': rec.date.strftime('%Y-%m-%d'),
            'recorded_date': rec.date.strftime('%Y-%m-%d'),
            'submitted_at': localtime(rec.created_at).strftime('%H:%M'),
            'temperature': temp_value,
            'raw_content': rec.content,
        })

    context = {
        'pet': pet,
        'records': records,
        'current_month': f"{year}-{month:02d}",
        'current_month_display': f"{year} 年 {month} 月",
        'is_current_month': is_current_month,
    }
    return render(request, 'health_records/tem_rec.html', context)


# 增加體溫資料
from datetime import date as dt_date
def add_tem(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    months = list(range(1, 13))
    today = dt_date.today()
    current_year = today.year
    if request.method == 'POST':
        try:
            month = int(request.POST.get('month'))
            day = int(request.POST.get('day'))
            temperature = request.POST.get('temperature', '').strip()
            if not temperature:
                messages.error(request, "請輸入體溫")
                raise ValueError("Missing temperature")
            record_date = dt_date(current_year, month, day)
            if record_date > today:
                messages.error(request, "日期不可超過今天")
                return redirect('add_tem', pet_id=pet.id)
            DailyRecord.objects.create(
                pet=pet,
                date=record_date,# date 欄位只顯示年月日，時間為儲存當下時間，使用者不見
                category='temperature',
                content=temperature
            )
            return redirect('tem_rec', pet_id=pet.id)
        except ValueError:
            messages.error(request, "日期格式錯誤，請重新輸入")
            return redirect('add_tem', pet_id=pet.id)
    context = {
        'pet': pet,
        'months': months,
        'month': today.month,
        'day': today.day,
        'temperature': '',
    }
    return render(request, 'health_records/add_tem.html', context)

# 修改體溫資料
def edit_tem(request, pet_id, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, pet_id=pet_id, category='temperature')

    if isinstance(record.date, datetime):
        record_date = record.date.date()
    else:
        record_date = record.date

    now = datetime.now()
    year = now.year

    # 取得預設月份與日
    default_month = record_date.month
    default_day = record_date.day

    # 使用 GET/POST 選擇的值（優先），否則用預設
    month = int(request.POST.get('month') or request.GET.get('month') or default_month)
    day = int(request.POST.get('day') or request.GET.get('day') or default_day)

    # 取得該月份所有天數，給前端用
    days_in_month = calendar.monthrange(year, month)[1]
    days = list(range(1, days_in_month + 1))
    months = list(range(1, 13))

    if request.method == 'POST' and 'temperature' in request.POST:
        temperature = request.POST.get('temperature')
        selected_date = datetime(year, month, day)
        combined_datetime = datetime.combine(selected_date, now.time())

        record.date = combined_datetime
        record.content = temperature
        record.save()
        return redirect('tem_rec', pet_id=pet_id)

    return render(request, 'health_records/edit_tem.html', {
        'pet_id': pet_id,
        'months': months,
        'days': days,
        'month': month,
        'day': day,
        'temperature': record.content,
    })
# 刪除體溫資料
def delete_tem(request, pet_id, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, pet_id=pet_id, category='temperature')
    record.delete()
    return redirect('tem_rec', pet_id=pet_id)

# （體溫）共用函式
def get_monthly_tem(request, pet_id, year, month):
    pet = get_object_or_404(Pet, id=pet_id)

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='temperature',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    result = []
    for rec in raw_records:
        try:
            temp = float(rec.content)
        except ValueError:
            continue
        result.append({
            'date': rec.date.strftime('%Y-%m-%d'),
            'temperature': temp,
        })
    return JsonResponse(result, safe=False)

# （體重）共用函式
def get_monthly_weight(request, pet_id, year, month):
    pet = get_object_or_404(Pet, id=pet_id)

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='weight',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    result = []
    for rec in raw_records:
        try:
            weight = float(rec.content)
        except ValueError:
            continue
        result.append({
            'date': rec.date.strftime('%Y-%m-%d'),
            'weight': weight,
        })
    return JsonResponse(result, safe=False)



# 體重頁面
def weight_rec(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    # 預設為今天的年月
    today = datetime.today()
    year, month = today.year, today.month

    # 取得目前選定月份
    month_str = request.GET.get('month')
    if month_str:
        try:
            year, month = map(int, month_str.split('-'))
        except ValueError:
            year, month = datetime.now().year, datetime.now().month
    else:
        year, month = datetime.now().year, datetime.now().month

    is_current_month = (year == today.year and month == today.month)

    # 當月的起始與結束日期
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    # 篩選當月資料
    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='weight',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    # 整理資料
    records = []
    for rec in raw_records:
        try:
            weight_value = float(rec.content)
        except ValueError:
            continue
        records.append({
            'id': rec.id,
            'date': rec.date.strftime('%Y-%m-%d'),
            'datetime': rec.date.strftime('%Y-%m-%d'),  # 使用者填的日期
            'recorded_date': rec.date.strftime('%Y-%m-%d'),  # ✅ 額外：使用者填的
            'submitted_at': localtime(rec.created_at).strftime('%H:%M'),
            'weight': weight_value,
            'raw_content': rec.content,
        })
    context = {
        'pet': pet,
        'records': records,
        'current_month': f"{year}-{month:02d}",
        'current_month_display': f"{year} 年 {month} 月",
        'is_current_month': is_current_month,
    }
    return render(request, 'health_records/weight_rec.html', context)


#  增加體重資料
from datetime import date as dt_date
def add_weight(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    months = list(range(1, 13))
    today = dt_date.today()
    current_year = today.year
    if request.method == 'POST':
        try:
            month = int(request.POST.get('month'))
            day = int(request.POST.get('day'))
            weight = request.POST.get('weight', '').strip()
            if not weight:
                messages.error(request, "請輸入體重")
                raise ValueError("Missing weight")
            record_date = dt_date(current_year, month, day)
            if record_date > today:
                messages.error(request, "日期不可超過今天")
                return redirect('add_weight', pet_id=pet.id)
            DailyRecord.objects.create(
                pet=pet,
                date=record_date,# date 欄位只顯示年月日，時間為儲存當下時間，使用者不見
                category='weight',
                content=weight
            )
            return redirect('weight_rec', pet_id=pet.id)
        except ValueError:
            messages.error(request, "日期格式錯誤，請重新輸入")
            return redirect('add_weight', pet_id=pet.id)
    context = {
        'pet': pet,
        'months': months,
        'month': today.month,
        'day': today.day,
        'weight': '',
    }
    return render(request, 'health_records/add_weight.html', context)

# 修改體重資料
def edit_weight(request, pet_id, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, pet_id=pet_id, category='weight')

    if isinstance(record.date, datetime):
        record_date = record.date.date()
    else:
        record_date = record.date

    now = datetime.now()
    year = now.year

    # 取得預設月份與日
    default_month = record_date.month
    default_day = record_date.day

    # 使用 GET/POST 選擇的值（優先），否則用預設
    month = int(request.POST.get('month') or request.GET.get('month') or default_month)
    day = int(request.POST.get('day') or request.GET.get('day') or default_day)

    # 取得該月份所有天數，給前端用
    days_in_month = calendar.monthrange(year, month)[1]
    days = list(range(1, days_in_month + 1))
    months = list(range(1, 13))

    if request.method == 'POST' and 'weight' in request.POST:
        weight = request.POST.get('weight')
        selected_date = datetime(year, month, day)
        combined_datetime = datetime.combine(selected_date, now.time())

        record.date = combined_datetime
        record.content = weight
        record.save()
        return redirect('weight_rec', pet_id=pet_id)

    return render(request, 'health_records/edit_weight.html', {
        'pet_id': pet_id,
        'months': months,
        'days': days,
        'month': month,
        'day': day,
        'weight': record.content,
    })


# 刪除體重資料
def delete_weight(request, pet_id, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, pet_id=pet_id, category='weight')
    record.delete()
    return redirect('weight_rec', pet_id=pet_id)


def map_home(request):
    """地圖首頁"""
    # 取得所有可用的城市和地點類型，用於篩選器
    cities = PetLocation.objects.values_list('city', flat=True).distinct().order_by('city')
    cities = [city for city in cities if city]  # 過濾空值
    
    # 新增：準備寵物支援類型資料
    pet_types = [
        {'code': 'support_small_dog', 'name': '小型犬', 'icon': '🐕‍'},
        {'code': 'support_medium_dog', 'name': '中型犬', 'icon': '🐕'},
        {'code': 'support_large_dog', 'name': '大型犬', 'icon': '🦮'},
        {'code': 'support_cat', 'name': '貓', 'icon': '🐈'},
        {'code': 'support_bird', 'name': '鳥類', 'icon': '🦜'},
        {'code': 'support_rodent', 'name': '嚙齒類/小動物', 'icon': '🐹'},
        {'code': 'support_reptile', 'name': '爬蟲類', 'icon': '🦎'},
        {'code': 'support_other', 'name': '其他寵物', 'icon': '🦝'},
    ]
    
    context = {
        'cities': cities,
        'pet_types': pet_types,
    }
    return render(request, 'petmap/map.html', context)


def api_locations(request):
    """地點資料 API - 清理版本（移除地址轉換相關功能）"""
    # 取得查詢參數
    location_type = request.GET.get('type', None)
    city = request.GET.get('city', None)
    search = request.GET.get('search', None)
    
    # 取得寵物支援類型篩選參數
    support_small_dog = request.GET.get('support_small_dog', None) == 'true'
    support_medium_dog = request.GET.get('support_medium_dog', None) == 'true'
    support_large_dog = request.GET.get('support_large_dog', None) == 'true'
    support_cat = request.GET.get('support_cat', None) == 'true'
    support_bird = request.GET.get('support_bird', None) == 'true'
    support_rodent = request.GET.get('support_rodent', None) == 'true'
    support_reptile = request.GET.get('support_reptile', None) == 'true'
    support_other = request.GET.get('support_other', None) == 'true'
    
    # 建立查詢
    query = PetLocation.objects.all()
    
    # 應用篩選條件
    if location_type:
        if location_type == 'restaurant':
            query = query.filter(
                Q(name__icontains='餐廳') | 
                Q(address__icontains='餐廳')
            )
        elif location_type == 'boarding':
            query = query.filter(is_boarding=1)
        elif location_type == 'shelter':
            query = query.filter(is_shelter=1)
        else:
            attr_name = f'is_{location_type}'
            if hasattr(PetLocation, attr_name):
                query = query.filter(**{attr_name: 1})
    
    if city:
        query = query.filter(city=city)
    
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(address__icontains=search) |
            Q(supported_pet_types__icontains=search)
        )
    
    # 寵物支援類型篩選
    pet_filters = {}
    if support_small_dog:
        pet_filters['support_small_dog'] = 1
    if support_medium_dog:
        pet_filters['support_medium_dog'] = 1
    if support_large_dog:
        pet_filters['support_large_dog'] = 1
    if support_cat:
        pet_filters['support_cat'] = 1
    if support_bird:
        pet_filters['support_bird'] = 1
    if support_rodent:
        pet_filters['support_rodent'] = 1
    if support_reptile:
        pet_filters['support_reptile'] = 1
    if support_other:
        pet_filters['support_other'] = 1
    
    # 如果有寵物類型篩選，使用智能推斷邏輯
    if pet_filters:
        filtered_query = query.filter(**pet_filters)
        if not filtered_query.exists():
            # 根據服務類型推斷支援的寵物
            service_based_query = Q()
            if support_small_dog or support_medium_dog or support_large_dog:
                service_based_query |= Q(is_hospital=1) | Q(is_cosmetic=1) | Q(is_live=1) | Q(is_boarding=1) | Q(is_park=1)
            if support_cat:
                service_based_query |= Q(is_hospital=1) | Q(is_cosmetic=1) | Q(is_live=1) | Q(is_boarding=1)
            if support_bird or support_rodent or support_reptile or support_other:
                service_based_query |= Q(is_product=1) | Q(is_hospital=1)
            
            query = query.filter(service_based_query)
        else:
            query = filtered_query
    
    # 限制結果數量
    query = query[:1000]
    
    # 轉換為 GeoJSON 格式
    features = []
    for location in query:
        # 解析營業時間 JSON
        business_hours_parsed = None
        if location.business_hours:
            try:
                business_hours_parsed = json.loads(location.business_hours) if isinstance(location.business_hours, str) else location.business_hours
            except (json.JSONDecodeError, TypeError):
                business_hours_parsed = None
        
        # 建立基本屬性
        properties = {
            'id': location.id,
            'name': location.name or '未命名',
            'type_display': location.get_services_list(),
            'address': location.address,  # 只返回address欄位
            'phone': location.phone,
            'website': location.website,
            'city': location.city,
            'district': location.district,
            'rating': float(location.rating) if location.rating else None,
            'rating_count': location.rating_count,
            'supported_pet_types': location.get_supported_pet_types_list(),
            'business_hours': business_hours_parsed,
            # 所有布爾屬性保持 0/1 格式
            'is_cosmetic': location.is_cosmetic,
            'is_funeral': location.is_funeral,
            'is_hospital': location.is_hospital,
            'is_live': location.is_live,
            'is_boarding': location.is_boarding,
            'is_park': location.is_park,
            'is_product': location.is_product,
            'is_shelter': location.is_shelter,
            # 寵物支援類型
            'support_small_dog': location.support_small_dog,
            'support_medium_dog': location.support_medium_dog,
            'support_large_dog': location.support_large_dog,
            'support_cat': location.support_cat,
            'support_bird': location.support_bird,
            'support_rodent': location.support_rodent,
            'support_reptile': location.support_reptile,
            'support_other': location.support_other,
        }
        
        # 只有當有座標時才建立 GeoJSON Feature
        if location.lat and location.lon:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(location.lon), float(location.lat)]
                },
                'properties': properties
            }
            features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return JsonResponse(geojson)

def api_stats(request):
    """統計資料 API"""
    # 按類型統計
    type_stats = {}
    for type_code, type_name in PetLocation.LOCATION_TYPES:
        count = PetLocation.objects.filter(location_type=type_code).count()
        type_stats[type_code] = {
            'name': type_name,
            'count': count
        }
    
    # 按城市統計
    city_stats = {}
    cities = PetLocation.objects.values_list('city', flat=True).distinct()
    for city in cities:
        if city:
            count = PetLocation.objects.filter(city=city).count()
            city_stats[city] = count
    
    # 總統計
    total_count = PetLocation.objects.count()
    with_coordinates = PetLocation.objects.filter(lat__isnull=False, lng__isnull=False).count()
    with_rating = PetLocation.objects.filter(rating__isnull=False).count()
    
    stats = {
        'total_locations': total_count,
        'with_coordinates': with_coordinates,
        'with_rating': with_rating,
        'by_type': type_stats,
        'by_city': city_stats,
    }
    
    return JsonResponse(stats)