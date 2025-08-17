# petapp/models.py
# 匯入 Django 所需模組
from django.db import models
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

import requests
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone

# ===== 全域常數定義
WEEKDAYS = [
    (0, "星期一"),
    (1, "星期二"),
    (2, "星期三"),
    (3, "星期四"),
    (4, "星期五"),
    (5, "星期六"),
    (6, "星期日"),
]

TIME_SLOTS = [
    ("morning", "早上"),
    ("afternoon", "下午"),
    ("evening", "晚上"),
]


class VetClinic(models.Model):
    """獸醫院/診所模型 - 加強農委會API驗證"""
    
    # 基本資訊
    clinic_name = models.CharField(max_length=100, verbose_name='診所名稱')
    license_number = models.CharField(max_length=50, unique=True, verbose_name='開業執照字號')
    clinic_phone = models.CharField(max_length=20, verbose_name='診所電話')
    clinic_address = models.CharField(max_length=255, verbose_name='診所地址')
    clinic_email = models.EmailField(verbose_name='診所信箱')
    
    # 驗證狀態
    is_verified = models.BooleanField(default=False, verbose_name='已通過農委會驗證')
    verification_date = models.DateTimeField(null=True, blank=True, verbose_name='驗證日期')
    
    # 農委會API驗證資料
    moa_county = models.CharField(max_length=20, blank=True, verbose_name='縣市')
    moa_status = models.CharField(max_length=20, blank=True, verbose_name='開業狀態')
    moa_responsible_vet = models.CharField(max_length=50, blank=True, verbose_name='負責獸醫')
    moa_issue_date = models.DateField(null=True, blank=True, verbose_name='發照日期')
    
    # 預約設定
    default_appointment_duration = models.IntegerField(default=30, verbose_name='預設預約時長(分鐘)')
    advance_booking_days = models.IntegerField(default=30, verbose_name='可提前預約天數')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '獸醫院'
        verbose_name_plural = '獸醫院'
    
    def __str__(self):
        return f"{self.clinic_name} ({self.license_number})"
    
    def verify_with_moa_api(self):
        """透過農委會API驗證診所執照"""
        try:
            import requests  
            from datetime import datetime
            
            api_url = "https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=078"
            print(f"🔍 開始驗證診所: {self.clinic_name} - {self.license_number}")
            
            response = requests.get(api_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 API回應資料筆數: {len(data)}")
                
                for clinic_data in data:
                    # 比對診所名稱和執照字號
                    api_license = clinic_data.get('字號', '').strip()
                    api_name = clinic_data.get('機構名稱', '').strip()
                    
                    print(f"比對中: API字號='{api_license}', API名稱='{api_name}'")
                    print(f"用戶輸入: 字號='{self.license_number}', 名稱='{self.clinic_name}'")
                    
                    if (api_license == self.license_number and 
                        api_name == self.clinic_name):
                        
                        print(f"✅ 找到匹配的診所: {clinic_data}")
                        
                        # 更新農委會資料
                        self.moa_county = clinic_data.get('縣市', '')
                        self.moa_status = clinic_data.get('狀態', '')
                        self.moa_responsible_vet = clinic_data.get('負責獸醫', '')
                        
                        # 轉換發照日期 (YYYYMMDD -> date)
                        issue_date_str = clinic_data.get('發照日期', '')
                        if issue_date_str and len(issue_date_str) == 8:
                            try:
                                self.moa_issue_date = datetime.strptime(issue_date_str, '%Y%m%d').date()
                            except ValueError:
                                pass
                        
                        # 檢查開業狀態
                        status = clinic_data.get('狀態', '').strip()
                        if status == '開業':
                            self.is_verified = True
                            self.verification_date = timezone.now()  # 使用 timezone.now()
                            self.save()
                            return True, "驗證成功！診所資料已更新。"
                        else:
                            return False, f"診所狀態為「{status}」，無法註冊。"
                
                print("❌ 未找到匹配的診所")
                return False, "農委會資料庫中找不到對應的診所資料，請確認診所名稱和執照字號是否正確。"
            else:
                return False, f"無法連接農委會API (狀態碼: {response.status_code})"
                
        except requests.Timeout:
            return False, "連接農委會API逾時，請稍後再試。"
        except requests.RequestException as e:
            print(f"網路連接錯誤: {e}")
            return False, f"網路連接錯誤：{str(e)}"
        except Exception as e:
            print(f"驗證過程發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False, f"驗證過程發生錯誤：{str(e)}"


class VetDoctor(models.Model):
    """獸醫師模型 - 支援雙重身份"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vet_profile')
    clinic = models.ForeignKey(VetClinic, on_delete=models.CASCADE, related_name='doctors')
    
    # 🎯 獸醫師驗證資訊（核心欄位）
    vet_license_number = models.CharField(max_length=50, blank=True, verbose_name='獸醫師執照號碼')
    license_verified_with_moa = models.BooleanField(default=False, verbose_name='農委會執照驗證')
    verification_date = models.DateTimeField(null=True, blank=True, verbose_name='執照驗證時間')
    
    # 🆕 從農委會API取得的關鍵資料
    moa_license_type = models.CharField(max_length=20, blank=True, verbose_name='執照類別')
    moa_clinic_name = models.CharField(max_length=100, blank=True, verbose_name='診所名稱')
    
    # 個人資訊
    specialization = models.CharField(max_length=100, blank=True, verbose_name='專科領域')
    years_of_experience = models.IntegerField(default=0, verbose_name='執業年資')
    bio = models.TextField(blank=True, verbose_name='個人簡介')
    
    # 🔄 改進：支援雙重身份的權限欄位
    is_active_veterinarian = models.BooleanField(default=True, verbose_name='獸醫師身份啟用')
    is_active_admin = models.BooleanField(default=False, verbose_name='管理員身份啟用')
    
    # 狀態
    is_active = models.BooleanField(default=True, verbose_name='帳號啟用狀態')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 🔒 改進的權限屬性
    @property
    def is_clinic_admin(self):
        """是否為診所管理員 - 基於專門的管理員欄位"""
        return self.is_active and self.is_active_admin
    
    @property
    def is_veterinarian(self):
        """是否為執業獸醫師 - 基於執照驗證和獸醫師身份"""
        return (self.is_active and 
                self.is_active_veterinarian and 
                self.license_verified_with_moa)
    
    @property
    def is_verified(self):
        #\"\"\"是否已驗證\"\"\"
        # 診所管理員如果有執照驗證，視為已驗證
        if self.is_clinic_admin and self.license_verified_with_moa:
            return True
        # 一般獸醫師需要執照驗證
        elif not self.is_clinic_admin and self.license_verified_with_moa:
            return True
        # 診所管理員沒有執照驗證的話，暫時也允許（但不能填寫醫療記錄）
        elif self.is_clinic_admin:
            return True
        else:
            return False

    @property
    def can_manage_appointments(self):
        """能否管理預約 - 獸醫師和管理員都可以"""
        return self.is_veterinarian or self.is_clinic_admin
    
    @property
    def can_manage_doctors(self):
        """能否管理其他醫師 - 只有管理員可以"""
        return self.is_clinic_admin
    
    @property
    def can_write_medical_records(self):
        """能否填寫醫療記錄 - 只有有執照驗證的獸醫師才能寫"""
        return self.is_veterinarian
    
    @property
    def can_manage_schedules(self):
        """能否管理排程 - 管理員可以管理所有，獸醫師只能管理自己的"""
        return self.is_veterinarian or self.is_clinic_admin
    
    @property
    def can_view_clinic_data(self):
        """能否查看診所數據 - 管理員可以看全部，獸醫師只能看相關的"""
        return self.is_clinic_admin or self.is_veterinarian
    
    @property
    def roles(self):
        """取得所有啟用的角色"""
        roles = []
        if self.is_veterinarian:
            roles.append('veterinarian')
        if self.is_clinic_admin:
            roles.append('clinic_admin')
        return roles
    
    @property
    def role_display(self):
        """角色顯示名稱"""
        roles = []
        if self.is_veterinarian:
            roles.append('獸醫師')
        if self.is_clinic_admin:
            roles.append('診所管理員')
        return ' / '.join(roles) if roles else '無啟用角色'

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{name} ({self.role_display})"

    class Meta:
        verbose_name = "獸醫師"
        verbose_name_plural = "獸醫師"


class BusinessHoursRecord(models.Model):
    clinic = models.OneToOneField(VetClinic, on_delete=models.CASCADE, related_name='business_hours_record')
    hours_data = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '診所營業時間'
        verbose_name_plural = '診所營業時間'

class VetSchedule(models.Model):
    """獸醫師排班表"""
    
    WEEKDAY_CHOICES = [
        (0, '週一'), (1, '週二'), (2, '週三'), (3, '週四'),
        (4, '週五'), (5, '週六'), (6, '週日'),
    ]
    
    doctor = models.ForeignKey(VetDoctor, on_delete=models.CASCADE, related_name='schedules')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, verbose_name='星期')
    start_time = models.TimeField(verbose_name='開始時間')
    end_time = models.TimeField(verbose_name='結束時間')
    
    # 排班設定
    is_active = models.BooleanField(default=True, verbose_name='啟用排班')
    appointment_duration = models.IntegerField(default=30, verbose_name='預約時長(分鐘)')
    max_appointments_per_slot = models.IntegerField(default=1, verbose_name='每時段最大預約數')
    
    # 備註
    notes = models.TextField(blank=True, verbose_name='備註')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '獸醫師排班'
        verbose_name_plural = '獸醫師排班'
        unique_together = ['doctor', 'weekday', 'start_time']
    
    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('結束時間必須晚於開始時間')
    
    def __str__(self):
        doctor_name = self.doctor.user.get_full_name() or self.doctor.user.username
        return f"{doctor_name} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"
        
    @property
    def duration_hours(self):
        """計算排班時長（小時）"""
        if self.start_time and self.end_time:
            start_seconds = self.start_time.hour * 3600 + self.start_time.minute * 60
            end_seconds = self.end_time.hour * 3600 + self.end_time.minute * 60
            duration_seconds = end_seconds - start_seconds
            return round(duration_seconds / 3600, 1)
        return 0
    
    @property
    def duration_minutes(self):
        """計算排班時長（分鐘）"""
        if self.start_time and self.end_time:
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            return end_minutes - start_minutes
        return 0
    
    @property
    def total_slots(self):
        """計算可生成的時段數"""
        if self.duration_minutes and self.appointment_duration:
            return self.duration_minutes // self.appointment_duration
        return 0
    
    @property
    def time_display(self):
        """格式化時間顯示"""
        if self.start_time and self.end_time:
            return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
        return "未設定"
    
    @property
    def period_display(self):
        """顯示時段（早上/下午/晚上）"""
        if self.start_time:
            hour = self.start_time.hour
            if 6 <= hour < 12:
                return "早上"
            elif 12 <= hour < 18:
                return "下午"
            elif 18 <= hour < 22:
                return "晚上"
            else:
                return "其他"
        return "未設定"
    
class VetScheduleException(models.Model):
    """獸醫師排班例外（請假、特殊排班等）"""
    
    EXCEPTION_TYPE_CHOICES = [
        ('leave', '請假'),
        ('holiday', '休假'),
        ('special', '特殊排班'),
        ('unavailable', '暫停預約'),
    ]
    
    doctor = models.ForeignKey(VetDoctor, on_delete=models.CASCADE, related_name='schedule_exceptions')
    exception_type = models.CharField(max_length=20, choices=EXCEPTION_TYPE_CHOICES, verbose_name='例外類型')
    
    # 日期範圍
    start_date = models.DateField(verbose_name='開始日期')
    end_date = models.DateField(verbose_name='結束日期')
    
    # 時間範圍（可選，如果整天請假則不填）
    start_time = models.TimeField(null=True, blank=True, verbose_name='開始時間')
    end_time = models.TimeField(null=True, blank=True, verbose_name='結束時間')
    
    # 替代排班（特殊排班時使用）
    alternative_start_time = models.TimeField(null=True, blank=True, verbose_name='替代開始時間')
    alternative_end_time = models.TimeField(null=True, blank=True, verbose_name='替代結束時間')
    
    reason = models.TextField(blank=True, verbose_name='原因')
    is_active = models.BooleanField(default=True, verbose_name='啟用')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='建立者')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '排班例外'
        verbose_name_plural = '排班例外'
    
    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError('結束日期不能早於開始日期')
        
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('結束時間必須晚於開始時間')
    
    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.get_exception_type_display()} ({self.start_date} ~ {self.end_date})"


class AppointmentSlot(models.Model):
    """預約時段模型"""
    
    clinic = models.ForeignKey(VetClinic, on_delete=models.CASCADE)
    doctor = models.ForeignKey(VetDoctor, on_delete=models.CASCADE)
    date = models.DateField(verbose_name='日期')
    start_time = models.TimeField(verbose_name='開始時間')
    end_time = models.TimeField(verbose_name='結束時間')
    
    # 可用性
    is_available = models.BooleanField(default=True, verbose_name='可預約')
    max_bookings = models.IntegerField(default=1, verbose_name='最大預約數')
    current_bookings = models.IntegerField(default=0, verbose_name='目前預約數')
    
    # 來源
    source = models.CharField(max_length=20, choices=[
        ('schedule', '排班生成'),
        ('manual', '手動新增'),
        ('exception', '例外排班'),
    ], default='schedule')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '預約時段'
        verbose_name_plural = '預約時段'
        unique_together = ['doctor', 'date', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"
    
    @property
    def is_fully_booked(self):
        return self.current_bookings >= self.max_bookings
    
    def can_book(self):
        """檢查是否可以預約"""
        return self.is_available and not self.is_fully_booked


class VetAppointment(models.Model):
    """預約記錄模型"""
    
    STATUS_CHOICES = [
        ('pending', '待確認'),
        ('confirmed', '已確認'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('no_show', '未到診'),
    ]
    
    # 關聯
    pet = models.ForeignKey('Pet', on_delete=models.CASCADE, verbose_name="預約寵物")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="飼主")
    slot = models.ForeignKey(AppointmentSlot, on_delete=models.CASCADE, verbose_name="預約時段")
    
    # 預約資訊
    reason = models.TextField(verbose_name="預約原因", blank=True)
    notes = models.TextField(verbose_name="備註", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    
    # 聯絡資訊
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name="聯絡電話")
    contact_email = models.EmailField(blank=True, verbose_name="聯絡信箱")
    booking_type = models.CharField(max_length=20, choices=[
        ('online', '線上預約'),
        ('phone', '電話預約'),
        ('walkin', '現場預約'),
    ], default='online')

    # 通知狀態
    clinic_notified = models.BooleanField(default=False, verbose_name='已通知診所')
    reminder_sent = models.BooleanField(default=False, verbose_name='已發送提醒')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
  

    class Meta:
        verbose_name = '預約記錄'
        verbose_name_plural = '預約記錄'
    
    def __str__(self):
        return f"{self.pet.name} - {self.slot.doctor.user.get_full_name()} ({self.slot.date} {self.slot.start_time})"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # 新預約時更新時段的預約數量
        if is_new:
            self.slot.current_bookings += 1
            self.slot.save()
    
    def delete(self, *args, **kwargs):
        # 刪除預約時減少時段的預約數量
        self.slot.current_bookings -= 1
        self.slot.save()
        super().delete(*args, **kwargs)
    
    def send_clinic_notification(self):
        """發送通知給診所"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"【毛日好】新預約通知 - {self.pet.name}"
        message = f"""
{self.slot.clinic.clinic_name} 您好：

您有一筆新的預約：

🐾 寵物姓名：{self.pet.name}
👤 飼主：{self.owner.get_full_name() or self.owner.username}
📅 預約日期：{self.slot.date}
🕒 預約時間：{self.slot.start_time} - {self.slot.end_time}
📞 聯絡電話：{getattr(self.owner.profile, 'phone_number', '未提供')}
📝 預約原因：{self.reason or '未填寫'}

請確認此預約並準備相關事宜。

— 毛日好 Paw&Day 系統
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.slot.clinic.clinic_email],
                fail_silently=False
            )
            self.clinic_notified = True
            self.save()
            return True
        except Exception as e:
            print(f"發送診所通知失敗: {e}")
            return False


class Profile(models.Model):
    """使用者檔案模型 - 調整為新架構"""
    
    ACCOUNT_TYPE_CHOICES = [
        ('owner', '飼主'),
        ('clinic_admin', '診所管理員'),# 可能是助手或獸醫師
        ('veterinarian', '獸醫師'),# 純粹看診獸醫師
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_type = models.CharField(max_length=15, choices=ACCOUNT_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name='手機號碼')
    
    
    def __str__(self):
        return f"{self.user.username} ({self.get_account_type_display()})"

# 工具類別：排班管理器
class ScheduleManager:
    """排班管理工具"""
    
    @staticmethod
    def generate_weekly_slots(doctor, start_date, end_date):
        """為指定醫師生成指定日期範圍的預約時段"""
        generated_slots = []
        current_date = start_date
        
        while current_date <= end_date:
            weekday = current_date.weekday()
            
            # 取得該醫師當天的排班
            schedules = VetSchedule.objects.filter(
                doctor=doctor,
                weekday=weekday,
                is_active=True
            )
            
            for schedule in schedules:
                # 檢查是否有例外排班
                exception = VetScheduleException.objects.filter(
                    doctor=doctor,
                    start_date__lte=current_date,
                    end_date__gte=current_date,
                    is_active=True
                ).first()
                
                if exception:
                    if exception.exception_type in ['leave', 'holiday', 'unavailable']:
                        # 跳過這天的排班
                        continue
                    elif exception.exception_type == 'special':
                        # 使用特殊排班時間
                        if exception.alternative_start_time and exception.alternative_end_time:
                            slots = ScheduleManager._create_slots_for_time_range(
                                doctor, current_date,
                                exception.alternative_start_time,
                                exception.alternative_end_time,
                                schedule.appointment_duration
                            )
                            generated_slots.extend(slots)
                        continue
                
                # 一般排班
                slots = ScheduleManager._create_slots_for_time_range(
                    doctor, current_date,
                    schedule.start_time,
                    schedule.end_time,
                    schedule.appointment_duration
                )
                generated_slots.extend(slots)
            
            current_date += timedelta(days=1)
        
        return generated_slots
    
    @staticmethod
    def _create_slots_for_time_range(doctor, date, start_time, end_time, duration_minutes):
        """為指定時間範圍創建預約時段"""
        slots = []
        current_time = datetime.combine(date, start_time)
        end_datetime = datetime.combine(date, end_time)
        
        while current_time < end_datetime:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            if slot_end.time() <= end_time:
                # 檢查是否已存在
                existing_slot = AppointmentSlot.objects.filter(
                    doctor=doctor,
                    date=date,
                    start_time=current_time.time()
                ).first()
                
                if not existing_slot:
                    slot = AppointmentSlot.objects.create(
                        clinic=doctor.clinic,
                        doctor=doctor,
                        date=date,
                        start_time=current_time.time(),
                        end_time=slot_end.time(),
                        source='schedule'
                    )
                    slots.append(slot)
            
            current_time = slot_end
        
        return slots
    
    @staticmethod
    def get_available_slots(doctor, date):
        """取得指定醫師指定日期的可用預約時段"""
        return AppointmentSlot.objects.filter(
            doctor=doctor,
            date=date,
            is_available=True,
            current_bookings__lt=models.F('max_bookings')
        ).order_by('start_time')
        
# 使用者註冊表單擴充，加上 email 欄位
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

# 以下為各種 Enum 選單：種類、絕育、性別
class Species(models.TextChoices):
    DOG = 'dog','狗'
    CAT = 'cat','貓'
    OTHER = 'other','其他'

class SterilizationStatus(models.TextChoices):
    YES = 'sterilized','已絕育'
    NO = 'not_sterilized','未絕育'
    UNKNOWN = 'unknown', '未知'

class Gender(models.TextChoices):
    MALE = 'male', '公'
    FEMALE = 'female', '母'
    UNKNOWN = 'unknown', '未知'

# 寵物基本資料
class Pet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pets', verbose_name='飼主')
    species = models.CharField(max_length=10, choices=Species.choices)
    breed = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    sterilization_status = models.CharField(max_length=20, choices=SterilizationStatus.choices)
    chip = models.CharField(max_length=100, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    weight = models.FloatField(null=True, blank=True)
    feature = models.TextField(blank=True)
    picture = models.ImageField(upload_to='pet_pictures/', blank=True, null=True)

    def __str__(self):
        return self.name

# 寵物的每日生活紀錄
class DailyRecord(models.Model):
    CATEGORY_CHOICES = [
        ('diet', '飲食習慣'),
        ('exercise', '運動習慣'),
        ('allergen', '過敏源'),
        ('other', '其他'),
        ('temperature', '體溫'),
        ('weight', '體重'),
    ]
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    content = models.TextField(blank=True)

    def __str__(self):
        return f"{self.pet.name} 的生活記錄（{self.date}）"


# 疫苗與驅蟲紀錄（含施打獸醫、地點）
class VaccineRecord(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='vaccine_records', verbose_name='寵物')
    name = models.CharField(max_length=100, verbose_name='疫苗品牌')
    date = models.DateField(verbose_name='施打日期')
    location = models.CharField(max_length=200, verbose_name='施打地點')
    vet = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, verbose_name='施打醫師') # SET_NULL：避免醫師帳號刪除時連同歷史疫苗紀錄也被刪除（資料應保留）。

    def __str__(self):
        return f"{self.pet.name} - {self.name}（{self.date}）"

class DewormRecord(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='deworm_records', verbose_name='寵物')
    name = models.CharField(max_length=100, verbose_name='驅蟲品牌')
    date = models.DateField(verbose_name='施打日期')
    location = models.CharField(max_length=200, verbose_name='施打地點')
    vet = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, verbose_name='施打醫師')

    def __str__(self):
        return f"{self.pet.name} - {self.name}（{self.date}）"

# 健康報告（上傳 PDF 給寵物與飼主）
class Report(models.Model):
    pet = models.ForeignKey('Pet', on_delete=models.CASCADE, related_name='reports')
    vet = models.ForeignKey(Profile, on_delete=models.CASCADE, limit_choices_to={'account_type': 'vet'})
    title = models.CharField(max_length=200)    # 報告標題
    pdf = models.FileField(upload_to='reports/')    # 上傳 PDF
    date_uploaded = models.DateTimeField(auto_now_add=True) # 上傳日期

# 看診紀錄（含診斷與治療內容）
class MedicalRecord(models.Model):
    pet = models.ForeignKey('Pet', on_delete=models.CASCADE, verbose_name="寵物")
    
    # 新增這些欄位：
    attending_vet = models.ForeignKey(
        VetDoctor, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='attended_records',
        limit_choices_to={'license_verified_with_moa': True},
        verbose_name="看診獸醫師"
    )
    recorded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="記錄填寫者"
    )
    
    visit_date = models.DateField(auto_now_add=True, verbose_name="看診日期")
    clinic_location = models.CharField(max_length=100, verbose_name="看診地點")
    diagnosis = models.TextField(verbose_name="診斷結果")
    treatment = models.TextField(verbose_name="治療內容")
    notes = models.TextField(blank=True, verbose_name="備註")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    @property
    def is_self_recorded(self):
        return self.attending_vet and self.attending_vet.user == self.recorded_by
    
    @property
    def recorder_role(self):
        if self.is_self_recorded:
            return "獸醫師本人"
        elif self.recorded_by:
            try:
                profile = self.recorded_by.profile
                if profile.account_type == 'clinic_admin':
                    return "診所管理員代填"
                else:
                    return "其他獸醫師代填"
            except:
                return "未知"
        return "系統記錄"

    def __str__(self):
        return f"{self.pet.name} - {self.visit_date} ({self.attending_vet.user.get_full_name() if self.attending_vet else '未指定獸醫師'})"

# 獸醫的可看診排班時段（支援開始/結束時間與唯一排班組合）
class VetAvailableTime(models.Model):
    vet = models.ForeignKey(Profile, on_delete=models.CASCADE, limit_choices_to={"account_type": "vet"}, verbose_name="獸醫")
    weekday = models.IntegerField(choices=WEEKDAYS, verbose_name="星期")
    time_slot = models.CharField(max_length=10, choices=TIME_SLOTS, verbose_name="時段")
    start_time = models.TimeField(verbose_name="看診開始時間")
    end_time = models.TimeField(verbose_name="看診結束時間")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")

    class Meta:
        unique_together = ('vet', 'weekday', 'time_slot')
        verbose_name = "獸醫排班時段"
        verbose_name_plural = "獸醫排班時段"

    def __str__(self):
        return f"{self.vet.user.username} - {dict(WEEKDAYS).get(self.weekday)} {dict(TIME_SLOTS).get(self.time_slot)} {self.start_time}~{self.end_time}"

#################寵物地點模型#######################
class ServiceType(models.Model):
    """服務類型表"""
    name = models.CharField(max_length=50, verbose_name='服務名稱')
    code = models.CharField(max_length=20, unique=True, verbose_name='服務代碼')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')

    class Meta:
        verbose_name = '服務類型'
        verbose_name_plural = '服務類型'
        db_table = 'pet_service_types'

    def __str__(self):
        return self.name

class PetType(models.Model):
    """寵物類型表"""
    name = models.CharField(max_length=50, verbose_name='寵物類型名稱')
    code = models.CharField(max_length=20, unique=True, verbose_name='寵物代碼')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')

    class Meta:
        verbose_name = '寵物類型'
        verbose_name_plural = '寵物類型'
        db_table = 'pet_types'

    def __str__(self):
        return self.name

class PetLocation(models.Model):
    """寵物相關地點模型"""
    
    # 基本資訊
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name='名稱')
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name='地址')
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name='電話')
    website = models.TextField(blank=True, null=True, verbose_name='網站')
    
    # 地理資訊
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='城市')
    district = models.CharField(max_length=100, blank=True, null=True, verbose_name='地區')
    lat = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True, verbose_name='緯度')
    lon = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True, verbose_name='經度')
    
    # 評分資訊
    rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, verbose_name='評分')
    rating_count = models.IntegerField(blank=True, null=True, verbose_name='評分數量')
    
    # 醫院特有屬性
    has_emergency = models.BooleanField(default=False, verbose_name='提供24小時急診')
    
    # 多對多關聯
    service_types = models.ManyToManyField(ServiceType, blank=True, 
                                         related_name='locations', verbose_name='服務類型')
    pet_types = models.ManyToManyField(PetType, blank=True, 
                                     related_name='locations', verbose_name='支援寵物類型')
    
    # 保留 business_hours JSONField（過渡期間）
    business_hours = models.JSONField(blank=True, null=True, verbose_name='營業時間')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        db_table = 'pet_locations'
        verbose_name = '寵物地點'
        verbose_name_plural = '寵物地點'
        indexes = [
            models.Index(fields=['city', 'district'], name='city_district_idx'),
            models.Index(fields=['has_emergency'], name='emergency_idx'),
            models.Index(fields=['lat', 'lon'], name='location_idx'),
        ]

    def __str__(self):
        services = [st.name for st in self.service_types.all()]
        service_text = f" ({', '.join(services)})" if services else ""
        return f"{self.name or '未命名'}{service_text}"
    
    def get_services_list(self):
        """取得提供的服務列表"""
        return [st.name for st in self.service_types.filter(is_active=True)]
        
    def has_service(self, service_code):
        """檢查是否提供特定服務"""
        return self.service_types.filter(code=service_code, is_active=True).exists()
    
    def supports_pet_type(self, pet_type_code):
        """檢查是否支援特定寵物類型"""
        return self.pet_types.filter(code=pet_type_code, is_active=True).exists()
    
    def get_business_hours_formatted(self):
        """格式化營業時間顯示"""
        business_hours = {}
        
        # 預設所有天都是未提供
        for day_num in range(7):
            day_name = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][day_num]
            business_hours[day_name] = '未提供'
        
        try:
            # 從 BusinessHours 表格取得資料
            for day_num in range(7):
                day_name = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][day_num]
                periods = self.business_hours_detail.filter(day_of_week=day_num).order_by('period_order')
                
                if periods.exists():
                    time_periods = []
                    for period in periods:
                        if period.open_time and period.close_time:
                            try:
                                open_str = period.open_time.strftime('%H:%M')
                                close_str = period.close_time.strftime('%H:%M')
                                time_periods.append(f"{open_str}-{close_str}")
                            except:
                                continue
                    
                    if time_periods:
                        business_hours[day_name] = '、'.join(time_periods)
                    else:
                        business_hours[day_name] = '休息'
                        
        except Exception as e:
            # 如果出現任何錯誤，返回預設值
            pass
        
        return business_hours
    
    def is_open_now(self):
        """判斷現在是否營業中"""
        from django.utils import timezone
        
        now = timezone.localtime()
        current_weekday = now.weekday()  # 0=週一, 6=週日
        current_time = now.time()
        
        periods = self.business_hours_detail.filter(day_of_week=current_weekday)
        
        for period in periods:
            if (period.open_time and period.close_time and 
                period.open_time <= current_time <= period.close_time):
                return True
        
        return False
    
    def get_full_address(self):
        """取得完整地址"""
        return self.address if self.address else None

class BusinessHours(models.Model):
    """營業時間表 - 支援一天多個時段"""
    WEEKDAY_CHOICES = [
        (0, '週一'), (1, '週二'), (2, '週三'), (3, '週四'),
        (4, '週五'), (5, '週六'), (6, '週日'),
    ]
    
    location = models.ForeignKey(PetLocation, on_delete=models.CASCADE, 
                               related_name='business_hours_detail', verbose_name='地點')
    day_of_week = models.IntegerField(choices=WEEKDAY_CHOICES, verbose_name='星期')
    open_time = models.TimeField(null=True, blank=True, verbose_name='開始時間')
    close_time = models.TimeField(null=True, blank=True, verbose_name='結束時間')
    period_order = models.PositiveIntegerField(default=1, verbose_name='時段順序')
    period_name = models.CharField(max_length=20, blank=True, null=True, verbose_name='時段名稱')

    class Meta:
        unique_together = ('location', 'day_of_week', 'period_order')
        verbose_name = '營業時間'
        verbose_name_plural = '營業時間'
        ordering = ['day_of_week', 'period_order']
        db_table = 'pet_business_hours'
        indexes = [
            models.Index(fields=['location', 'day_of_week'], name='business_hours_idx'),
        ]

    def __str__(self):
        if not self.open_time or not self.close_time:
            return f"{self.location.name} - {self.get_day_of_week_display()} (休息)"
        period_text = f" ({self.period_name})" if self.period_name else f" (時段{self.period_order})"
        return f"{self.location.name} - {self.get_day_of_week_display()}{period_text} {self.open_time}-{self.close_time}"
    
