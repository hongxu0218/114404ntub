# petapp/views.py 

from collections import defaultdict
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Profile, Pet, DailyRecord, VetAppointment, VaccineRecord, DewormRecord, Report, VetAvailableTime, MedicalRecord,PetLocation,ServiceType, PetType,BusinessHours
from .forms import EditProfileForm, SocialSignupExtraForm, PetForm, TemperatureEditForm, WeightEditForm, VetAppointmentForm, VaccineRecordForm, DewormRecordForm, ReportForm, VetAvailableTimeForm, MedicalRecordForm
from allauth.account.views import SignupView
from allauth.socialaccount.views import SignupView as SocialSignupView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods ,require_GET
from datetime import date, datetime, timedelta, time
from django.core.mail import send_mail  # 新增：匯入發信功能
import json
from django.db.models import Q

from calendar import monthrange
import calendar
from django.utils.timezone import localtime
from .utils import get_temperature_data, get_weight_data
from dateutil.relativedelta import relativedelta
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone



# 首頁

def home(request):
    return render(request, 'pages/index.html')  # 渲染首頁

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
    return render(request, 'pet_info/pet_list.html')

# 獸醫主控台（需審核通過）
@login_required
def vet_dashboard(request):
    profile = request.user.profile
    if not profile.is_verified_vet:
        messages.warning(request, "您的獸醫帳號尚未通過管理員驗證。請稍後再試。")
        return redirect('home')
    return render(request, 'vet_pages/vet_home.html')

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
        return redirect('pet_list.html')
    elif profile.account_type == 'vet':
        return redirect('vet_home.html')
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
from datetime import date as dt_date
@login_required
def add_pet(request):
    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES)
        if form.is_valid():
            pet = form.save(commit=False)  # 不馬上存進資料庫
            pet.owner = request.user  # 指定目前登入使用者為飼主
            pet.save()  # 現在儲存到資料庫

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
    return render(request, 'pet_info/add_pet.html', {
        'form': form,
    })


# 寵物列表
def pet_list(request):
    pets = Pet.objects.filter(owner=request.user)
    today = date.today()
    now = datetime.now()

    # 預約資料
    for pet in pets:
        pet.future_appointments = VetAppointment.objects.filter(pet=pet, date__gte=today).order_by('date', 'time')

    # 明天內尚未過時的預約
    tomorrow = today + timedelta(days=1)
    if request.user.is_authenticated:
        tomorrow_appointments = VetAppointment.objects.filter(
            owner=request.user,
            date=tomorrow,
        ).filter(
            time__gt=now.time() if tomorrow == today else time(0, 0)
        ).order_by('time')
    else:
        tomorrow_appointments = []
    
    appointment_digest = "|".join([
        f"{appt.date.isoformat()}_{appt.time.strftime('%H:%M')}_{appt.vet_id}_{appt.pet_id}"
        for appt in tomorrow_appointments
    ])

    notif_count = len(tomorrow_appointments)

    return render(request, 'pet_info/pet_list.html', {
        'pets': pets,
        'tomorrow_appointments': tomorrow_appointments,
        'notif_count': notif_count,
        'appointment_digest': appointment_digest,
    })


# 編輯寵物
def edit_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES, instance=pet)
        if form.is_valid():
            form.save()
            messages.info(request, f"寵物 {pet.name} 資料已更新。")
            return redirect('pet_list')
    else:
        form = PetForm(instance=pet)
    return render(request, 'pet_info/edit_pet.html', {'form': form, 'pet': pet})

# 刪除寵物

def delete_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    if request.method == 'POST':
        pet.delete()
        messages.success(request, f"寵物 {pet.name} 資料已刪除。")
        return redirect('pet_list')
    return render(request, 'pet_info/delete_pet.html', {'pet': pet})

# 健康紀錄列表
def health_rec(request):
    # 撈出 飼主 所擁有的所有寵物
    pets = Pet.objects.filter(owner=request.user).prefetch_related(
        'vaccine_records', 'deworm_records', 'reports'
    )

    # 健康記錄 撈資料
    #records = DailyRecord.objects.select_related('pet').order_by('date')
    records = DailyRecord.objects.filter(pet__in=pets).select_related('pet').order_by('date')
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
        'pets':pets
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



# 新增預約
@login_required
def create_vet_appointment(request):
    pet_id = request.GET.get('pet_id')
    if not pet_id:
        return HttpResponseBadRequest("缺少寵物 ID")

    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        print("🔥 POST")
        form = VetAppointmentForm(request.POST, user=request.user)
        print("🧪 POST data:", request.POST.dict())

        if form.is_valid():
            print("✅ 表單驗證通過")
            appointment = form.save(commit=False)
            appointment.pet = pet
            appointment.owner = request.user
            appointment.vet = form.cleaned_data['vet']

            # 時間欄位安全轉型
            try:
                appointment.time = datetime.strptime(form.cleaned_data['time'], "%H:%M:%S").time()
            except ValueError:
                form.add_error('time', '時間格式錯誤')
                return render(request, 'appointments/create_appointment.html', {'form': form, 'pet': pet})

            # 日期邏輯驗證
            today = date.today()
            if appointment.date < today:
                form.add_error('date', '預約日期不可早於今天')
            elif appointment.date == today:
                form.add_error('date', '預約日期需至少提前一天')
            elif VetAppointment.objects.filter(vet=appointment.vet, date=appointment.date, time=appointment.time).exists():
                form.add_error('time', '此時段已被其他飼主預約，請選擇其他時間')
            else:
                appointment.save()

                # 發送 Email 給獸醫
                vet_user = appointment.vet.user
                vet_email = vet_user.email
                pet_name = pet.name
                owner_name = f"{request.user.last_name}{request.user.first_name}" or request.user.username
                clinic = appointment.vet.clinic_name or "您的診所"

                subject = f"【毛日好】您有新的預約：{pet_name}"
                message = f"""親愛的 {vet_user.last_name} 醫師您好：

您有一筆新的預約記錄：

🐾 寵物名稱：{pet_name}
👤 飼主：{owner_name}
📅 日期：{appointment.date}
🕒 時間：{appointment.time.strftime('%H:%M')}
🏥 診所：{clinic}
📌 理由：{appointment.reason or '（無填寫）'}

請至後台確認詳細資訊。謝謝您的使用！

— 毛日好（Paw&Day）團隊"""

                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [vet_email], fail_silently=False)
                return render(request, 'appointments/appointment_success.html', {'appointment': appointment})

        else:
            print("❌ 表單驗證失敗")
            print("❌ 錯誤內容：", form.errors)

    else:
        form = VetAppointmentForm(
            user=request.user,
            initial={
                'pet': pet,
                'date': date.today() + timedelta(days=1),
            }
        )

    return render(request, 'appointments/create_appointment.html', {'form': form, 'pet': pet})

# 取消預約
@require_POST
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(VetAppointment, id=appointment_id, owner=request.user)
    appointment.delete()
    messages.success(request, "預約已取消")
    return redirect('pet_list')

# 獸醫查看預約狀況
@login_required
def vet_appointments(request):
    # 確保是獸醫帳號
    profile = request.user.profile
    if not profile.is_verified_vet:
        return render(request, 'pages/403.html', status=403)

    # 取得該獸醫的所有預約
    today = date.today()
    now_time = datetime.now().time()

    show_history = request.GET.get('history') == '1'

    if show_history:
        # 顯示已看診紀錄（今天以前，或今天但時間已過）
        appointments = VetAppointment.objects.filter(
            vet=profile
        ).filter(
            (Q(date__lt=today)) |
            (Q(date=today) & Q(time__lt=now_time))
        )
    else:
        # 顯示尚未看診
        appointments = VetAppointment.objects.filter(
            vet=profile
        ).filter(
            (Q(date__gt=today)) |
            (Q(date=today) & Q(time__gte=now_time))
        )

    appointments = appointments.order_by('date', 'time')
    return render(request, 'vet_pages/vet_appointments.html', {'appointments': appointments, 'show_history': show_history})


@require_POST
@login_required
def vet_cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(VetAppointment, id=appointment_id)

    # 確認使用者是該名獸醫
    if appointment.vet.user != request.user:
        messages.error(request, "您無權限取消此預約。")
        return redirect('vet_appointments')

    # 取得取消原因
    cancel_reason = request.POST.get('cancel_reason', '').strip()
    if not cancel_reason:
        messages.error(request, "請輸入取消原因。")
        return redirect('vet_appointments')

    # 蒐集資料
    owner_email = appointment.owner.email
    pet_name = appointment.pet.name
    date = appointment.date
    time = appointment.time
    vet_name = f"{request.user.last_name}{request.user.first_name}" or request.user.username

    # 建立信件內容
    subject = "【毛日好】預約取消通知"
    message = f"""親愛的飼主您好：

您為寵物「{pet_name}」所預約的看診（{date} {time.strftime('%H:%M')}）已由獸醫（{vet_name}）取消。
📌 取消原因：{cancel_reason}

如需看診請重新預約，造成不便敬請見諒。

— 毛日好（Paw&Day）系統
"""

    # 刪除預約後寄信
    appointment.delete()

    print("寄信前：", owner_email)
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [owner_email],
        fail_silently=False
    )
    print("寄信成功")

    messages.success(request, "已成功取消預約，並通知飼主。")
    return redirect('vet_appointments')



@login_required
def vet_availability_settings(request):
    # 確保是獸醫帳號
    profile = request.user.profile
    if not profile.is_verified_vet:
        return render(request, 'pages/403.html', status=403)

    if request.method == 'POST':
        form = VetAvailableTimeForm(request.POST)
        if form.is_valid():
            new_time = form.save(commit=False)
            new_time.vet = profile
            new_time.save()
            messages.success(request, "已新增排班時段")
            return redirect('vet_availability_settings')
    else:
        form = VetAvailableTimeForm()

    schedules = VetAvailableTime.objects.filter(vet=profile).order_by('weekday', 'time_slot')
    return render(request, 'vet_pages/vet_availability_settings.html', {
        'form': form,
        'schedules': schedules,
    })
# 顯示「我的看診寵物」
@login_required
def my_patients(request):
    profile = request.user.profile
    if not profile.is_verified_vet:
        return render(request, 'pages/403.html', status=403)

    # 原始清單（該獸醫曾看診過的所有寵物，避免重複）
    pets = Pet.objects.filter(vetappointment__vet=profile).distinct()

    # 取得搜尋關鍵字
    q = request.GET.get('q', '')

    if q:
        pets = pets.filter(
            Q(name__icontains=q) |
            Q(owner__first_name__icontains=q) |
            Q(owner__last_name__icontains=q)
        )

    # 最後加上 prefetch_related 提升效能
    pets = pets.prefetch_related('vaccine_records', 'deworm_records', 'reports')

    return render(request, 'vet_pages/my_patients.html', {
        'pets': pets,
        'query': q,
    })

@login_required
def vet_pet_detail(request, pet_id):
    profile = request.user.profile
    if not profile.is_verified_vet:
        return render(request, 'pages/403.html', status=403)

    pet = get_object_or_404(Pet, id=pet_id)
    # 選擇是否限制：只能看自己看診過的寵物
    if not pet.vetappointment_set.filter(vet=profile).exists():
        return render(request, 'pages/403.html', status=403)

    medical_records = pet.medicalrecord_set.order_by('-visit_date')
    vaccine_records = pet.vaccine_records.all().order_by('-date')
    deworm_records = pet.deworm_records.all().order_by('-date')
    reports = pet.reports.all().order_by('-date_uploaded')

    return render(request, 'vet_pages/pet_detail.html', {
        'pet': pet,
        'medical_records': medical_records,
        'vaccine_records': vaccine_records,
        'deworm_records': deworm_records,
        'reports': reports,
    })


# 新增指定寵物的病例
@login_required
def add_medical_record(request, pet_id):
    # TODO: 為指定寵物新增病例
    return render(request, 'vet_pages/create_medical_record.html')

# 修改指定寵物的病例
@login_required
def edit_medical_record(request, pet_id, record_id):
    record = get_object_or_404(MedicalRecord, id=record_id, pet_id=pet_id)

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save(commit=False)
            record.pet = record.pet  # 保險設定
            record.save()
            return redirect('my_patients')
    else:
        form = MedicalRecordForm(instance=record)

    return render(request, 'vet_pages/edit_medical_record.html', {
        'form': form,
        'pet': record.pet
    })
# 刪除指定寵物的病例
@login_required
def delete_medical_record(request, record_id):
    record = get_object_or_404(MedicalRecord, id=record_id)
    record.delete()
    return redirect('my_patients')


# 飼主取消預約通知獸醫
@require_POST
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(VetAppointment, id=appointment_id, owner=request.user)

    # 寄信資料
    vet_user = appointment.vet.user
    vet_email = vet_user.email
    pet_name = appointment.pet.name
    owner_name = f"{request.user.last_name}{request.user.first_name}" or request.user.username
    clinic = appointment.vet.clinic_name or "您的診所"
    date = appointment.date
    time = appointment.time

    subject = f"【毛日好】預約取消通知：{pet_name}"
    message = f"""親愛的 {vet_user.last_name} 醫師您好：

飼主 {owner_name} 已取消以下預約：

🐾 寵物名稱：{pet_name}
📅 日期：{date}
🕒 時間：{time.strftime('%H:%M')}
🏥 診所：{clinic}

請您留意行程更新，謝謝您的配合！

— 毛日好（Paw&Day）系統"""

    # 刪除資料
    appointment.delete()

    # 發送通知 Email 給獸醫
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [vet_email], fail_silently=False)

    messages.success(request, "預約已取消，並已通知獸醫。")
    return redirect('pet_list')




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
    today = dt_date.today()   #抓取今天的日期
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

# 新增疫苗
@login_required
def add_vaccine(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        form = VaccineRecordForm(request.POST)
        if form.is_valid():
            vaccine = form.save(commit=False)
            vaccine.pet = pet
            vaccine.vet = request.user.profile  # 登入獸醫
            vaccine.save()
            return redirect('my_patients')
    else:
        form = VaccineRecordForm()
    return render(request, 'vaccine&deworm/add_vaccine.html', {
        'form': form,
        'pet': pet
    })
from django.http import HttpResponseForbidden

@login_required
def edit_vaccine(request, pet_id, vaccine_id):
    pet = get_object_or_404(Pet, id=pet_id)
    vaccine = get_object_or_404(VaccineRecord, id=vaccine_id, pet=pet)

    # 權限檢查：只能編輯自己建立的疫苗紀錄
    if vaccine.vet != request.user.profile:
        return HttpResponseForbidden("你沒有權限編輯這筆疫苗紀錄。")

    if request.method == 'POST':
        form = VaccineRecordForm(request.POST, instance=vaccine)
        if form.is_valid():
            edited_vaccine = form.save(commit=False)
            edited_vaccine.vet = request.user.profile  # 保持原獸醫資訊
            edited_vaccine.save()
            return redirect('my_patients')
    else:
        form = VaccineRecordForm(instance=vaccine)

    return render(request, 'vaccine&deworm/edit_vaccine.html', {
        'form': form,
        'pet': pet,
        'vaccine': vaccine,
    })


# 刪除疫苗紀錄
@login_required
def delete_vaccine(request, vaccine_id):
    vaccine = get_object_or_404(VaccineRecord, id=vaccine_id)

    # 確保只有該紀錄的獸醫或具權限者能刪除（可自定邏輯）
    if request.user.profile == vaccine.vet:
        pet_id = vaccine.pet.id
        vaccine.delete()
        return redirect('my_patients')  # 或導回特定 pet 的健康紀錄頁面
    else:
        return redirect('permission_denied')  # 可自定一個拒絕頁面


# 新增疫苗
@login_required
def add_deworm(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        form = DewormRecordForm(request.POST)
        if form.is_valid():
            deworms = form.save(commit=False)
            deworms.pet = pet
            deworms.vet = request.user.profile  # 登入獸醫
            deworms.save()
            return redirect('my_patients')
    else:
        form = DewormRecordForm()

    return render(request, 'vaccine&deworm/add_deworm.html', {
        'form': form,
        'pet': pet
    })


@login_required
def edit_deworm(request, pet_id, deworm_id):
    pet = get_object_or_404(Pet, id=pet_id)
    deworm = get_object_or_404(DewormRecord, id=deworm_id, pet=pet)

    # 權限檢查：只能編輯自己建立的疫苗紀錄
    if deworm.vet != request.user.profile:
        return HttpResponseForbidden("你沒有權限編輯這筆疫苗紀錄。")

    if request.method == 'POST':
        form = DewormRecordForm(request.POST, instance=deworm)
        if form.is_valid():
            edited_deworm = form.save(commit=False)
            edited_deworm.vet = request.user.profile  # 保持原獸醫資訊
            edited_deworm.save()
            return redirect('my_patients')
    else:
        form = DewormRecordForm(instance=deworm)

    return render(request, 'vaccine&deworm/edit_deworm.html', {
        'form': form,
        'pet': pet,
        'deworm': deworm,
    })

# 刪除疫苗紀錄
@login_required
def delete_deworm(request, deworm_id):
    deworm = get_object_or_404(DewormRecord, id=deworm_id)

    # 確保只有該紀錄的獸醫或具權限者能刪除（可自定邏輯）
    if request.user.profile == deworm.vet:
        pet_id = deworm.pet.id
        deworm.delete()
        return redirect('my_patients')  # 或導回特定 pet 的健康紀錄頁面
    else:
        return redirect('permission_denied')  # 可自定一個拒絕頁面

# 新增報告
@login_required
def add_report(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.pet = pet
            report.vet = request.user.profile  # 登入的獸醫
            report.save()
            return redirect('my_patients')
    else:
        form = ReportForm()

    return render(request, 'vaccine&deworm/add_report.html', {
        'form': form,
        'pet': pet
    })
# 刪除報告
@login_required
def delete_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)

    # 確保只有該紀錄的獸醫或具權限者能刪除（可自定邏輯）
    if request.user.profile == report.vet:
        pet_id = report.pet.id
        report.delete()
        return redirect('my_patients')  # 或導回特定 pet 的健康紀錄頁面
    else:
        return redirect('permission_denied')  # 可自定一個拒絕頁面

# 獸醫編輯可預約時段
@login_required
def edit_vet_schedule(request, schedule_id):
    schedule = get_object_or_404(VetAvailableTime, id=schedule_id, vet=request.user.profile)

    if request.method == 'POST':
        form = VetAvailableTimeForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, "排班時段已更新")
            return redirect('vet_availability_settings')
    else:
        form = VetAvailableTimeForm(instance=schedule)

    return render(request, 'vet_pages/edit_schedule.html', {'form': form})

# 獸醫刪除可預約時段
@login_required
def delete_vet_schedule(request, schedule_id):
    schedule = get_object_or_404(VetAvailableTime, id=schedule_id, vet=request.user.profile)
    schedule.delete()
    messages.success(request, "排班時段已刪除")
    return redirect('vet_availability_settings')

@require_GET
@login_required
def get_available_times(request):
    vet_id = request.GET.get('vet_id')
    date_val = request.GET.get('date')

    if not vet_id or not date_val:
        return JsonResponse({'error': '缺少參數'}, status=400)


    print("🟢 收到 AJAX 請求：", request.GET.dict())
    try:
        parsed_date = datetime.strptime(date_val, "%Y-%m-%d").date()
        weekday = parsed_date.weekday()

        slots = VetAvailableTime.objects.filter(vet_id=vet_id, weekday=weekday)

        valid_times = []
        for slot in slots:
            current = datetime.combine(date.today(), slot.start_time)
            end = datetime.combine(date.today(), slot.end_time)
            while current.time() < end.time():
                valid_times.append(current.time())
                current += timedelta(minutes=30)

        booked = VetAppointment.objects.filter(vet_id=vet_id, date=parsed_date).values_list('time', flat=True)
        available = [t for t in valid_times if t not in booked]

        time_choices = [(t.strftime("%H:%M:%S"), t.strftime("%H:%M")) for t in available]
        return JsonResponse({'times': time_choices}, encoder=DjangoJSONEncoder)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
def create_medical_record(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    profile = request.user.profile

    if profile.account_type != 'vet':
        return render(request, 'unauthorized.html')  # 非獸醫導向未授權頁

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.pet = pet
            record.vet = profile
            record.clinic_location = profile.clinic_name  # 自動填入診所地點
            record.save()
            return redirect('my_patients')  # 統一導向與 add_vaccine 相同
    else:
        form = MedicalRecordForm(initial={'pet': pet, 'clinic_location': profile.clinic_name})

    return render(request, 'vet_pages/create_medical_record.html', {
        'form': form,
        'pet': pet
    })

# 通知
@login_required
def get_notification_count(request):
    user = request.user
    tomorrow = timezone.now().date() + timedelta(days=1)
    count = 0

    if hasattr(user, 'profile'):
        account_type = user.profile.account_type
        if account_type == 'owner':
            count = VetAppointment.objects.filter(owner=user, date=tomorrow).count()
        elif account_type == 'vet':
            count = VetAppointment.objects.filter(vet=user.profile, date=tomorrow).count()

    return JsonResponse({'count': count})

# 通知頁面邏輯
@login_required
def notification_page(request):
    user = request.user
    tomorrow = timezone.now().date() + timedelta(days=1)

    appointments = []
    role = None

    if hasattr(user, 'profile'):
        role = user.profile.account_type
        if role == 'owner':
            appointments = VetAppointment.objects.filter(owner=user, date=tomorrow)
        elif role == 'vet':
            appointments = VetAppointment.objects.filter(vet=user.profile, date=tomorrow)

    return render(request, 'pages/notifications.html', {
        'appointments': appointments,
        'role': role,
        'tomorrow': tomorrow,
    })

###############################地圖############################

pet_types = PetType.objects.filter(is_active=True).order_by('name')

def map_home(request):
    """地圖首頁"""
    # 取得所有可用的城市，用於篩選器
    cities = PetLocation.objects.values_list('city', flat=True).distinct().order_by('city')
    cities = [city for city in cities if city]  # 過濾空值
    
    # 從資料庫取得寵物類型並加上圖標
    pet_types_raw = PetType.objects.filter(is_active=True).order_by('name')
    
    # 為寵物類型添加圖標（這應該在模型中定義，或使用字典映射）
    PET_TYPE_ICONS = {
        'small_dog': '🐕‍',
        'medium_dog': '🐕',
        'large_dog': '🦮',
        'cat': '🐈',
        'bird': '🦜',
        'rodent': '🐹',
        'reptile': '🦎',
        'other': '🦝'
    }
    
    pet_types = []
    for pet_type in pet_types_raw:
        pet_types.append({
            'code': pet_type.code,
            'name': pet_type.name,
            'icon': PET_TYPE_ICONS.get(pet_type.code, '🐾')
        })
    
    context = {
        'cities': cities,
        'pet_types': pet_types,
    }
    return render(request, 'petmap/map.html', context)


def api_locations(request):
    """簡化版地點資料 API - 專注於解決篩選問題"""
    try:
        print("🔍 API 請求開始...")
        print(f"所有 GET 參數: {dict(request.GET)}")
        
        # 取得查詢參數
        location_type = request.GET.get('type', None)
        city = request.GET.get('city', None)
        search = request.GET.get('search', None)
        
        # 處理寵物類型篩選參數
        pet_type_codes = []
        for param_name, param_value in request.GET.items():
            if param_name.startswith('support_') and param_value == 'true':
                pet_code = param_name.replace('support_', '')
                pet_type_codes.append(pet_code)
        
        print(f"📊 篩選條件:")
        print(f"  - 服務類型: {location_type}")
        print(f"  - 城市: {city}")
        print(f"  - 搜尋: {search}")
        print(f"  - 寵物類型: {pet_type_codes}")
        
        # 基本查詢 - 只選擇有座標的地點
        query = PetLocation.objects.filter(
            lat__isnull=False, 
            lon__isnull=False
        ).prefetch_related('service_types', 'pet_types')
        
        initial_count = query.count()
        print(f"📍 初始查詢結果: {initial_count} 個有座標的地點")
        
        # 服務類型篩選
        if location_type:
            print(f"🏥 應用服務類型篩選: {location_type}")
            
            # 檢查這個服務類型是否存在
            service_exists = ServiceType.objects.filter(code=location_type, is_active=True).exists()
            print(f"服務類型 '{location_type}' 是否存在: {service_exists}")
            
            if service_exists:
                filtered_query = query.filter(
                    service_types__code=location_type,
                    service_types__is_active=True
                ).distinct()
                
                filtered_count = filtered_query.count()
                print(f"篩選後結果: {filtered_count} 個地點")
                
                if filtered_count > 0:
                    query = filtered_query
                else:
                    print("⚠️ 篩選後沒有結果，但仍會返回空列表")
            else:
                print(f"❌ 服務類型 '{location_type}' 不存在")
                query = query.none()  # 返回空查詢集
        
        # 城市篩選
        if city:
            before_count = query.count()
            query = query.filter(city=city)
            after_count = query.count()
            print(f"🏙️ 城市篩選 ({city}): {before_count} -> {after_count}")
        
        # 搜尋篩選
        if search:
            before_count = query.count()
            query = query.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search)
            ).distinct()
            after_count = query.count()
            print(f"🔍 搜尋篩選 ({search}): {before_count} -> {after_count}")
        
        # 寵物類型篩選
        if pet_type_codes:
            print(f"🐾 應用寵物類型篩選: {pet_type_codes}")
            
            # 檢查有效的寵物類型代碼
            valid_pet_codes = list(PetType.objects.filter(
                code__in=pet_type_codes, 
                is_active=True
            ).values_list('code', flat=True))
            
            print(f"有效的寵物類型代碼: {valid_pet_codes}")
            
            if valid_pet_codes:
                before_count = query.count()
                pet_filtered_query = query.filter(
                    pet_types__code__in=valid_pet_codes,
                    pet_types__is_active=True
                ).distinct()
                
                pet_filtered_count = pet_filtered_query.count()
                print(f"寵物類型篩選: {before_count} -> {pet_filtered_count}")
                
                # 如果沒有地點明確支援這些寵物類型，不篩選（顯示所有地點）
                if pet_filtered_count > 0:
                    query = pet_filtered_query
                else:
                    print("⚠️ 沒有地點明確支援指定寵物類型，顯示所有符合其他條件的地點")
        
        # 限制結果數量並執行查詢
        max_results = 200
        final_locations = list(query[:max_results])
        final_count = len(final_locations)
        
        print(f"📊 最終結果: {final_count} 個地點")
        
        # 轉換為 GeoJSON 格式
        features = []
        
        for i, location in enumerate(final_locations):
            try:
                # 獲取關聯資料
                service_types = list(location.service_types.all())
                pet_types = list(location.pet_types.all())
                
                service_names = [st.name for st in service_types]
                pet_names = [pt.name for pt in pet_types]
                
                # 建立寵物支援屬性
                pet_support = {}
                for pt in pet_types:
                    pet_support[f'support_{pt.code}'] = True
                
                properties = {
                    'id': location.id,
                    'name': location.name or '未命名',
                    'address': location.address or '',
                    'phone': location.phone or '',
                    'city': location.city or '',
                    'district': location.district or '',
                    'rating': float(location.rating) if location.rating else None,
                    'rating_count': location.rating_count or 0,
                    'has_emergency': location.has_emergency,
                    'service_types': service_names,
                    'supported_pet_types': pet_names,
                    **pet_support
                }
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [float(location.lon), float(location.lat)]
                    },
                    'properties': properties
                }
                features.append(feature)
                
                # 每處理 20 個地點輸出一次進度
                if (i + 1) % 20 == 0:
                    print(f"🔄 已處理 {i + 1}/{final_count} 個地點")
                    
            except Exception as e:
                print(f"❌ 處理地點 {location.id} 時發生錯誤: {e}")
                continue
        
        geojson_response = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        print(f"✅ API 處理完成，返回 {len(features)} 個地點特徵")
        print(f"回應大小: {len(str(geojson_response))} 字元")
        
        return JsonResponse(geojson_response)
        
    except Exception as e:
        print(f"💥 API 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'error': 'Internal server error',
            'message': str(e),
            'type': 'server_error'
        }, status=500)
                        
@login_required
def manage_business_hours(request, location_id):
    """管理地點營業時間"""
    location = get_object_or_404(PetLocation, id=location_id)
    
    if request.method == 'POST':
        # 處理營業時間的新增/修改
        pass
    
    # 取得現有營業時間
    business_hours = BusinessHours.objects.filter(location=location).order_by('day_of_week', 'period_order')
    
    return render(request, 'petmap/manage_business_hours.html', {
        'location': location,
        'business_hours': business_hours
    })

@login_required  
def add_location(request):
    """新增地點"""
    if request.method == 'POST':
        # 處理地點新增邏輯
        pass
    
    service_types = ServiceType.objects.filter(is_active=True)
    pet_types = PetType.objects.filter(is_active=True)
    
    return render(request, 'petmap/add_location.html', {
        'service_types': service_types,
        'pet_types': pet_types
    })

def api_stats(request):
    """統計資料 API（可選）"""
    # 按服務類型統計
    service_stats = {}
    for service_type in ServiceType.objects.filter(is_active=True):
        count = service_type.locations.count()
        service_stats[service_type.code] = {
            'name': service_type.name,
            'count': count
        }

###############################地圖############################