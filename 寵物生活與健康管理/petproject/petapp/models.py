# petapp/models.py
# 匯入 Django 所需模組
from django.db import models
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

import requests
from datetime import datetime, timedelta, date
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


# ===== 全域常數定義
WEEKDAYS = [
    (0, '週一'), (1, '週二'), (2, '週三'), (3, '週四'),
    (4, '週五'), (5, '週六'), (6, '週日'),
]

TIME_SLOTS = [
    ("morning", "早上"),
    ("afternoon", "下午"),
    ("evening", "晚上"),
]

#===========🏥 獸醫診所模組===============#
class VetClinic(models.Model):
    """獸醫院/診所模型 - 加強農委會API驗證"""
    
    # 基本資訊
    clinic_name = models.CharField(max_length=100, verbose_name='診所名稱')
    license_number = models.CharField(max_length=50, unique=True, verbose_name='開業執照字號')
    clinic_phone = models.CharField(max_length=20, verbose_name='診所電話')
    clinic_address = models.CharField(max_length=255, verbose_name='診所地址')
    clinic_email = models.EmailField(verbose_name='診所信箱')
    
    clinic_admin = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="managed_clinic")
    
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
    
    # 診所模式 
    CLINIC_MODE_CHOICES = [
        ('single', '單一醫師模式'),
        ('multi', '多醫師模式'),
    ]

    clinic_mode = models.CharField(
        max_length=20,
        choices=CLINIC_MODE_CHOICES,
        default='single',
        verbose_name='診所模式'
    )

    class Meta:
        verbose_name = '獸醫院'
        verbose_name_plural = '獸醫院'
    
    def __str__(self):
        return self.clinic_name
    
    def verify_with_moa_api(self):
        """透過農委會API驗證診所執照"""
        try:
            import requests  
            from datetime import datetime
            
            api_url = "https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=078"
            print(f"INFO 開始驗證診所: {self.clinic_name} - {self.license_number}")
            
            response = requests.get(api_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"INFO API回應資料筆數: {len(data)}")
                
                for clinic_data in data:
                    # 比對診所名稱和執照字號
                    api_license = clinic_data.get('字號', '').strip()
                    api_name = clinic_data.get('機構名稱', '').strip()
                    
                    print(f"比對中: API字號='{api_license}', API名稱='{api_name}'")
                    print(f"用戶輸入: 字號='{self.license_number}', 名稱='{self.clinic_name}'")
                    
                    if (api_license == self.license_number and 
                        api_name == self.clinic_name):
                        
                        print(f"SUCCESS 找到匹配的診所: {clinic_data}")
                        
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
                
                print("ERROR 未找到匹配的診所")
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
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vet_profile")
    clinic = models.ForeignKey(VetClinic, on_delete=models.CASCADE, related_name='doctors')
    
    # 獸醫師驗證資訊（核心欄位）
    vet_license_number = models.CharField(max_length=50, blank=True, verbose_name='獸醫師執照號碼')
    license_verified_with_moa = models.BooleanField(default=False, verbose_name='農委會執照驗證')
    verification_date = models.DateTimeField(null=True, blank=True, verbose_name='執照驗證時間')
    
    # 從農委會API取得的關鍵資料
    moa_license_type = models.CharField(max_length=20, blank=True, verbose_name='執照類別')
    moa_clinic_name = models.CharField(max_length=100, blank=True, verbose_name='診所名稱')
    
    # 個人資訊
    specialization = models.CharField(max_length=100, blank=True, verbose_name='專科領域')
    years_of_experience = models.IntegerField(default=0, verbose_name='執業年資')
    bio = models.TextField(blank=True, verbose_name='個人簡介')
    
    # 支援雙重身份的權限欄位
    is_active_veterinarian = models.BooleanField(default=True, verbose_name='獸醫師身份啟用')
    is_clinic_admin = models.BooleanField(default=False, verbose_name='管理員身份啟用')
    
    # 狀態
    is_active = models.BooleanField(default=True, verbose_name='帳號啟用狀態')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def phone_number(self):
        """獲取醫師電話號碼（從 Profile 中取得）"""
        try:
            return self.user.profile.phone_number or ''
        except (AttributeError, Profile.DoesNotExist):
            return ''
    
    @phone_number.setter
    def phone_number(self, value):
        """設置醫師電話號碼（保存到 Profile 中）"""
        try:
            profile, created = Profile.objects.get_or_create(
                user=self.user,
                defaults={'account_type': 'vet'}
            )
            profile.phone_number = value
            profile.save()
        except Exception:
            pass
    
    @property
    def email(self):
        """獲取醫師 email"""
        return self.user.email
    
    @property
    def full_name(self):
        """獲取醫師全名"""
        return self.user.get_full_name() or self.user.username

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



class ClinicBusinessHoursRecord(models.Model):
    """診所營業時間記錄 - 優化版"""
    
    WEEKDAY_CHOICES = [
        (0, '週一'), (1, '週二'), (2, '週三'), (3, '週四'),
        (4, '週五'), (5, '週六'), (6, '週日')
    ]
    
    STATUS_CHOICES = [
        ('open', '營業'),
        ('closed', '休息'),
        ('holiday', '節假日'),
        ('emergency', '緊急時段'),
    ]
    
    clinic = models.ForeignKey(
        'VetClinic',
        on_delete=models.CASCADE,
        related_name="business_hours",
        verbose_name="所屬診所",
        db_index=True  # 加索引優化查詢
    )
    
    weekday = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        verbose_name="星期",
        validators=[MinValueValidator(0), MaxValueValidator(6)]
    )
    
    start_time = models.TimeField(verbose_name="開始時間")
    end_time = models.TimeField(verbose_name="結束時間")
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
        verbose_name="狀態"
    )
    
    # 新增：排序和優先級
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="排序",
        help_text="同一天多個時段的排序"
    )
    
    # 新增：有效期限（支援節假日等特殊安排）
    effective_date = models.DateField(
        null=True, blank=True,
        verbose_name="特定日期",
        help_text="如果設定，則僅在此日期有效"
    )
    
    # 新增：是否為預設時間表
    is_default = models.BooleanField(
        default=True,
        verbose_name="是否為預設時間表",
        help_text="非預設時間表可用於特殊安排"
    )
    
    # 新增：備註
    notes = models.TextField(
        blank=True,
        verbose_name="備註",
        help_text="額外說明，如：僅限急診等"
    )
    
    # 審計欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_business_hours',
        verbose_name="建立者"
    )

    class Meta:
        # 優化的唯一約束
        unique_together = [
            ('clinic', 'weekday', 'start_time', 'end_time', 'effective_date', 'is_default')
        ]
        
        # 複合索引優化查詢
        indexes = [
            models.Index(fields=['clinic', 'weekday', 'is_default']),
            models.Index(fields=['clinic', 'effective_date']),
            models.Index(fields=['weekday', 'start_time']),
        ]
        
        ordering = ['weekday', 'order', 'start_time']
        verbose_name = "診所營業時間"
        verbose_name_plural = "診所營業時間"

    def clean(self):
        """數據驗證"""
        super().clean()
        
        # 時間邏輯驗證
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError({
                    'end_time': '結束時間必須晚於開始時間'
                })
        
        # 檢查時段重疊
        if self.clinic_id:
            overlapping = ClinicBusinessHoursRecord.objects.filter(
                clinic=self.clinic,
                weekday=self.weekday,
                is_default=self.is_default,
                effective_date=self.effective_date,
                status='open'
            ).exclude(pk=self.pk)
            
            for record in overlapping:
                if (self.start_time < record.end_time and 
                    self.end_time > record.start_time):
                    raise ValidationError(
                        f'與現有時段 {record.start_time}-{record.end_time} 重疊'
                    )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        date_str = f" ({self.effective_date})" if self.effective_date else ""
        return f"{self.clinic.clinic_name} - {self.get_weekday_display()} {self.start_time}~{self.end_time}{date_str}"
    
    @property
    def duration_minutes(self):
        """計算時段長度（分鐘）"""
        if not (self.start_time and self.end_time):
            return 0
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return end_minutes - start_minutes
    
    @property
    def duration_hours(self):
        """計算時段長度（小時）"""
        return round(self.duration_minutes / 60, 2)


class ClinicBusinessHoursTemplate(models.Model):
    """營業時間模板 - 新增模型"""
    
    TEMPLATE_TYPES = [
        ('weekday_only', '平日營業'),
        ('weekend_half', '週末半天'),
        ('full_week', '全週營業'),
        ('custom', '自訂模板'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="模板名稱")
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPES,
        verbose_name="模板類型"
    )
    description = models.TextField(blank=True, verbose_name="描述")
    
    # JSON 儲存模板數據
    template_data = models.JSONField(
        default=dict,
        verbose_name="模板數據",
        help_text="營業時間的 JSON 格式數據"
    )
    
    # 是否為系統預設模板
    is_system_template = models.BooleanField(
        default=False,
        verbose_name="系統模板"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "營業時間模板"
        verbose_name_plural = "營業時間模板"
        ordering = ['template_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


# 管理器類別
class ClinicBusinessHoursManager(models.Manager):
    """營業時間查詢管理器"""
    
    def for_clinic(self, clinic):
        """獲取指定診所的營業時間"""
        return self.filter(clinic=clinic)
    
    def active_hours(self, clinic, date=None):
        """獲取有效的營業時間"""
        queryset = self.filter(
            clinic=clinic,
            status='open'
        )
        
        if date:
            # 優先查找特定日期的安排
            specific_date = queryset.filter(
                effective_date=date,
                is_default=False
            )
            if specific_date.exists():
                return specific_date
            
            # 否則返回該星期的預設安排
            weekday = date.weekday()
            return queryset.filter(
                weekday=weekday,
                is_default=True,
                effective_date__isnull=True
            )
        
        return queryset.filter(is_default=True)
    
    def is_open_now(self, clinic):
        """檢查診所當前是否營業"""
        now = datetime.datetime.now()
        current_time = now.time()
        today = now.date()
        weekday = today.weekday()
        
        # 先檢查今天是否有特殊安排
        special_hours = self.filter(
            clinic=clinic,
            effective_date=today,
            is_default=False,
            status='open'
        )
        
        if special_hours.exists():
            return special_hours.filter(
                start_time__lte=current_time,
                end_time__gte=current_time
            ).exists()
        
        # 檢查預設營業時間
        return self.filter(
            clinic=clinic,
            weekday=weekday,
            is_default=True,
            status='open',
            start_time__lte=current_time,
            end_time__gte=current_time
        ).exists()

# 將管理器添加到模型
ClinicBusinessHoursRecord.add_to_class('objects', ClinicBusinessHoursManager())
#===========📅 預約排程模組============#

class VetSchedule(models.Model):
    """獸醫師排班模型"""
    
    # ========= 現有欄位保留 =========
    doctor = models.ForeignKey(VetDoctor, on_delete=models.CASCADE, related_name='schedules')
    weekday = models.IntegerField(choices=WEEKDAYS, verbose_name='星期')
    start_time = models.TimeField(verbose_name='開始時間')
    end_time = models.TimeField(verbose_name='結束時間')
    appointment_duration = models.IntegerField(default=30, verbose_name='預約時長(分鐘)')
    max_appointments_per_slot = models.IntegerField(default=1, verbose_name='每時段最大預約數')
    notes = models.TextField(blank=True, verbose_name='備註')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ========= 新增欄位 =========
    schedule_type = models.CharField(
        max_length=20,
        choices=[
            ('weekly', '週排班'),
            ('monthly', '月排班'),
            ('custom', '自訂排班')
        ],
        default='weekly',
        verbose_name='排班類型'
    )

    # 排班優先級
    PRIORITY_CHOICES = [
        ('normal', '一般'),
        ('high', '高'),
        ('urgent', '緊急'),
    ]
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name='優先級'
    )
    
    # 排班狀態
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '啟用'),
        ('suspended', '暫停'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='狀態'
    )

    has_conflicts = models.BooleanField(default=False, verbose_name='有衝突')
    conflict_details = models.JSONField(blank=True, null=True, verbose_name='衝突詳情')
    
    valid_from = models.DateField(null=True, blank=True, verbose_name='生效開始日期')
    valid_until = models.DateField(null=True, blank=True, verbose_name='生效結束日期')
    
    copied_from = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        verbose_name='複製自'
    )
    
    batch_group = models.CharField(max_length=50, blank=True, verbose_name='批量群組')
    
    def check_conflicts(self):
        """檢查並更新衝突狀態"""
        conflicts = []
        
        # 檢查同醫師同天時間衝突
        overlapping = VetSchedule.objects.filter(
            doctor=self.doctor,
            weekday=self.weekday,
            is_active=True
        ).exclude(id=self.id)
        
        for schedule in overlapping:
            if time_overlap(self.start_time, self.end_time,
                          schedule.start_time, schedule.end_time):
                conflicts.append({
                    'type': 'time_overlap',
                    'schedule_id': schedule.id,
                    'message': f'與 {schedule.start_time}-{schedule.end_time} 重疊'
                })
        
        self.has_conflicts = len(conflicts) > 0
        self.conflict_details = conflicts if conflicts else None
        return conflicts
    # ========= 保留現有方法 =========
    def period_display(self):
        """保留這個方法（如果其他地方有用到）"""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    
    # ========= 新增方法 =========
    @property
    def is_expired(self):
        """檢查排班是否已過期"""
        if self.valid_until:
            return date.today() > self.valid_until
        return False
    
    @property
    def can_delete(self):
        """檢查是否可刪除（無未來預約）"""
        future_appointments = VetAppointment.objects.filter(
            slot__doctor=self.doctor,
            slot__date__gte=date.today(),
            status__in=['pending', 'confirmed']
        )
        return not future_appointments.exists()
    
    @property
    def duration_hours(self):
        """計算時段時數"""
        if self.start_time and self.end_time:
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            return (end_minutes - start_minutes) / 60
        return 0
    
    @property
    def total_slots(self):
        """計算總可預約數"""
        if self.appointment_duration > 0:
            hours = self.duration_hours
            slots_per_hour = 60 / self.appointment_duration
            return int(hours * slots_per_hour * self.max_appointments_per_slot)
        return 0
    
    class Meta:
        verbose_name = '排班設定'
        verbose_name_plural = '排班設定'
        ordering = ['doctor', 'weekday', 'start_time']
        
    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.get_weekday_display()} {self.period_display()}"


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
    
    @property
    def is_expired(self):
        """檢查預約是否已過期"""
        if self.status in ['cancelled', 'completed', 'no_show']:
            return False
        
        from django.utils import timezone
        now = timezone.now()
        appointment_datetime = datetime.combine(self.slot.date, self.slot.end_time)
        appointment_datetime = timezone.make_aware(appointment_datetime)
        
        return now > appointment_datetime
    
    @property
    def is_today(self):
        """檢查預約是否為今日"""
        from django.utils import timezone
        return self.slot.date == timezone.now().date()
    
    @property  
    def is_future(self):
        """檢查預約是否為未來"""
        from django.utils import timezone
        now = timezone.now()
        appointment_datetime = datetime.combine(self.slot.date, self.slot.start_time)
        appointment_datetime = timezone.make_aware(appointment_datetime)
        
        return appointment_datetime > now
    
    def mark_as_expired(self, mark_as='cancelled'):
        """標記預約為過期
        
        Args:
            mark_as: 標記為什麼狀態 ('cancelled' 或 'no_show')
                   - 'cancelled': 已取消（獸醫端自動取消）
                   - 'no_show': 未到診（病患未出現）
        """
        if self.is_expired and self.status in ['pending', 'confirmed']:
            self.status = mark_as
            self.updated_at = timezone.now()
            # 添加取消原因備註
            if mark_as == 'cancelled':
                if hasattr(self, 'cancel_reason'):
                    self.cancel_reason = '系統自動取消：預約已過期'
                if not self.notes:
                    self.notes = '系統自動取消：預約已過期'
                else:
                    self.notes += '\n[系統自動取消：預約已過期]'
            self.save()
            return True
        return False
    
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

寵物姓名：{self.pet.name}
飼主：{self.owner.get_full_name() or self.owner.username}
預約日期：{self.slot.date}
預約時間：{self.slot.start_time} - {self.slot.end_time}
聯絡電話：{getattr(self.owner.profile, 'phone_number', '未提供')}
預約原因：{self.reason or '未填寫'}

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

#===========🔐 用戶管理模組============#

class Profile(models.Model):
    """使用者檔案模型 - 調整為新架構"""
    
    ACCOUNT_TYPE_CHOICES = [
        ('owner', '飼主'),
        ('clinic_admin', '診所管理員'),# 可能是助手或獸醫師
        ('veterinarian', '獸醫師'),# 純粹看診獸醫師
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    account_type = models.CharField(max_length=15, choices=ACCOUNT_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True, verbose_name='手機號碼')
    
    # 為了向下兼容，添加獸醫相關屬性
    @property
    def is_clinic_admin(self):
        return self.account_type == 'clinic_admin'
    
    @property
    def is_veterinarian(self):
        return self.account_type == 'veterinarian'
    
    @property
    def is_active(self):
        return self.user.is_active
    
    @property
    def can_manage_doctors(self):
        return self.is_clinic_admin
    
    @property
    def is_active_veterinarian(self):
        return self.is_veterinarian and self.is_active
        
    @property
    def license_verified_with_moa(self):
        # 假設所有獸醫師都已驗證，實際應該檢查相關驗證資料
        return self.is_veterinarian
    
    @property
    def clinic(self):
        """獲取關聯的診所"""
        try:
            if self.is_clinic_admin:
                # 診所管理員：查找管理的診所
                return VetClinic.objects.filter(clinic_admin=self.user).first()
            else:
                # 獸醫師：透過 VetDoctor 查找診所
                doctor = VetDoctor.objects.filter(user=self.user).first()
                return doctor.clinic if doctor else None
        except:
            return None
    
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

#=============== 寵物管理模組 ================#
# 寵物基本資料
class PetTag(models.Model):
    """寵物標籤系統"""
    
    TAG_TYPES = [
        ('medical', '醫療狀況'),
        ('behavior', '行為特性'),
        ('diet', '飲食需求'),
        ('emergency', '緊急狀況'),
        ('other', '其他'),
    ]
    
    TAG_COLORS = [
        ('red', '紅色'),
        ('orange', '橘色'),
        ('yellow', '黃色'),
        ('green', '綠色'),
        ('blue', '藍色'),
        ('purple', '紫色'),
        ('gray', '灰色'),
    ]
    
    name = models.CharField(max_length=50, verbose_name='標籤名稱')
    tag_type = models.CharField(max_length=20, choices=TAG_TYPES, default='other', verbose_name='標籤類型')
    color = models.CharField(max_length=10, choices=TAG_COLORS, default='blue', verbose_name='標籤顏色')
    description = models.TextField(blank=True, verbose_name='標籤描述')
    is_system_tag = models.BooleanField(default=False, verbose_name='系統預設標籤')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = '寵物標籤'
        verbose_name_plural = '寵物標籤'
        unique_together = ['name', 'tag_type']
    
    def __str__(self):
        return f"{self.name} ({self.get_tag_type_display()})"


class Pet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pets', verbose_name='飼主')
    species = models.CharField(max_length=50, verbose_name='種類')
    breed = models.CharField(max_length=50, verbose_name='品種')
    name = models.CharField(max_length=100)
    sterilization_status = models.CharField(max_length=20, choices=SterilizationStatus.choices)
    chip = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name='晶片號碼')
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    weight = models.FloatField(null=True, blank=True)
    feature = models.TextField(blank=True)
    picture = models.ImageField(upload_to='pet_pictures/', blank=True, null=True)
    
    # 新增字段
    tags = models.ManyToManyField(PetTag, blank=True, verbose_name='標籤')
    last_visit_date = models.DateField(null=True, blank=True, verbose_name='最後就診日期')
    is_active = models.BooleanField(default=True, verbose_name='狀態啟用')
    emergency_contact = models.CharField(max_length=200, blank=True, verbose_name='緊急聯絡人')
    emergency_phone = models.CharField(max_length=20, blank=True, verbose_name='緊急聯絡電話')
    medical_notes = models.TextField(blank=True, verbose_name='重要醫療備註')
    
    # 領養相關字段
    is_adoption_only = models.BooleanField(default=False, verbose_name='是否正在送養中')
    is_adopted = models.BooleanField(default=False, verbose_name='是否已完成送養（被領養）')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '寵物'
        verbose_name_plural = '寵物'
        ordering = ['-updated_at', 'name']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['last_visit_date']),
            models.Index(fields=['species', 'breed']),
        ]

    def __str__(self):
        return self.name
    
    @property
    def age(self):
        """計算寵物年齡"""
        if self.birth_date:
            from datetime import date
            today = date.today()
            age = today.year - self.birth_date.year
            if today.month < self.birth_date.month or (today.month == self.birth_date.month and today.day < self.birth_date.day):
                age -= 1
            return age
        return None
    
    @property
    def age_display(self):
        """友好顯示年齡"""
        age = self.age
        if age is None:
            return "年齡未知"
        elif age < 1:
            from datetime import date
            months = (date.today().year - self.birth_date.year) * 12 + date.today().month - self.birth_date.month
            return f"{months}個月"
        else:
            return f"{age}歲"

    @property
    def detailed_age(self):
        """詳細年齡顯示：X年X個月X天"""
        if not self.birth_date:
            return "年齡未知"

        from datetime import date
        today = date.today()
        birth = self.birth_date

        # 計算年、月、日
        years = today.year - birth.year
        months = today.month - birth.month
        days = today.day - birth.day

        # 處理負數天數
        if days < 0:
            months -= 1
            # 獲取上個月的天數
            if today.month == 1:
                prev_month = 12
                prev_year = today.year - 1
            else:
                prev_month = today.month - 1
                prev_year = today.year

            import calendar
            days_in_prev_month = calendar.monthrange(prev_year, prev_month)[1]
            days += days_in_prev_month

        # 處理負數月份
        if months < 0:
            years -= 1
            months += 12

        # 格式化顯示
        result_parts = []
        if years > 0:
            result_parts.append(f"{years}年")
        if months > 0:
            result_parts.append(f"{months}個月")
        if days > 0:
            result_parts.append(f"{days}天")

        if not result_parts:
            return "今天出生"

        return "".join(result_parts)
    
    @property
    def has_recent_visit(self):
        """是否有近期就診記錄（30天內）"""
        if self.last_visit_date:
            from datetime import date, timedelta
            return (date.today() - self.last_visit_date) <= timedelta(days=30)
        return False
    
    def get_medical_tags(self):
        """獲取醫療相關標籤"""
        return self.tags.filter(tag_type='medical')
    
    def get_emergency_tags(self):
        """獲取緊急狀況標籤"""
        return self.tags.filter(tag_type='emergency')
    
    def update_last_visit_date(self):
        """更新最後就診日期"""
        from datetime import date
        self.last_visit_date = date.today()
        self.save(update_fields=['last_visit_date', 'updated_at'])

# 寵物的每日生活紀錄
class DailyRecord(models.Model):
    # 重新組織分類：數據類型在前，筆記類型在後
    CATEGORY_CHOICES = [
        # 健康數據類（需要趨勢分析）
        ('temperature', '體溫監測'),
        ('weight', '體重記錄'),
        ('exercise', '運動記錄'),
        # 生活筆記類（重內容記錄）
        ('diet', '飲食筆記'),
        ('medication', '用藥記錄'),
        ('allergen', '過敏記錄'),
        ('mood', '行為觀察'),
        ('other', '其他筆記'),
    ]
    
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    content = models.TextField(blank=True, verbose_name='記錄內容')
    
    # 數值字段
    temperature = models.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        null=True, 
        blank=True, 
        verbose_name='體溫(°C)',
        validators=[MinValueValidator(35.0), MaxValueValidator(45.0)]
    )
    weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='體重(kg)',
        validators=[MinValueValidator(0.1), MaxValueValidator(100.0)]
    )
    medication_dosage = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='藥物劑量'
    )
    exercise_duration = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name='運動時長(分鐘)',
        validators=[MinValueValidator(0), MaxValueValidator(720)]
    )
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = '生活記錄'
        verbose_name_plural = '生活記錄'

    def __str__(self):
        return f"{self.pet.name} 的生活記錄（{self.date}）"
    
    def is_data_type(self):
        """判斷是否為數據類型記錄（需要趨勢分析）"""
        return self.category in ['temperature', 'weight', 'exercise']
    
    def is_note_type(self):
        """判斷是否為筆記類型記錄（重內容記錄）"""
        return not self.is_data_type()
    
    def get_display_value(self):
        """根據分類返回適當的顯示值"""
        if self.category == 'temperature' and self.temperature:
            return f"{self.temperature}°C"
        elif self.category == 'weight' and self.weight:
            return f"{self.weight}kg"
        elif self.category == 'exercise' and self.exercise_duration:
            return f"{self.exercise_duration}分鐘"
        elif self.category == 'medication' and self.medication_dosage:
            return self.medication_dosage
        else:
            return self.content[:50] + "..." if len(self.content) > 50 else self.content


#=============📋 醫療記錄模組=============#

# 疫苗與驅蟲紀錄（含施打獸醫、地點）
class VaccineRecord(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='vaccine_records', verbose_name='寵物')
    name = models.CharField(max_length=100, verbose_name='疫苗品牌')
    date = models.DateField(verbose_name='施打日期')
    location = models.CharField(max_length=200, verbose_name='施打地點')
    vet = models.ForeignKey('VetDoctor', on_delete=models.SET_NULL, null=True, verbose_name='施打醫師') # SET_NULL：避免醫師帳號刪除時連同歷史疫苗紀錄也被刪除（資料應保留）。
    protection_period_months = models.IntegerField(null=True, blank=True, verbose_name='保護效期（月）', help_text='疫苗保護效期，以月為單位')
    next_due_date = models.DateField(null=True, blank=True, verbose_name='下次接種日期', help_text='根據保護效期自動計算或手動設定')

    def save(self, *args, **kwargs):
        # 如果有保護效期，自動計算下次接種日期
        if self.protection_period_months and self.date and not self.next_due_date:
            from dateutil.relativedelta import relativedelta
            self.next_due_date = self.date + relativedelta(months=self.protection_period_months)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pet.name} - {self.name}（{self.date}）"

class DewormRecord(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='deworm_records', verbose_name='寵物')
    name = models.CharField(max_length=100, verbose_name='驅蟲品牌')
    date = models.DateField(verbose_name='施打日期')
    location = models.CharField(max_length=200, verbose_name='施打地點')
    vet = models.ForeignKey('VetDoctor', on_delete=models.SET_NULL, null=True, verbose_name='施打醫師')
    protection_period_months = models.IntegerField(null=True, blank=True, verbose_name='保護效期（月）', help_text='驅蟲保護效期，以月為單位')
    next_due_date = models.DateField(null=True, blank=True, verbose_name='下次施打日期', help_text='根據保護效期自動計算或手動設定')

    def save(self, *args, **kwargs):
        # 如果有保護效期，自動計算下次施打日期
        if self.protection_period_months and self.date and not self.next_due_date:
            from dateutil.relativedelta import relativedelta
            self.next_due_date = self.date + relativedelta(months=self.protection_period_months)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pet.name} - {self.name}（{self.date}）"

# 健康報告（上傳 PDF 給寵物與飼主）
class Report(models.Model):
    pet = models.ForeignKey('Pet', on_delete=models.CASCADE, related_name='reports')
    vet = models.ForeignKey(Profile, on_delete=models.CASCADE, limit_choices_to={'account_type': 'vet'})
    clinic = models.ForeignKey('VetClinic', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='檢驗地點')  # 檢驗地點
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

    # 生理數據
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="體重(kg)")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name="體溫(°C)")
    heart_rate = models.IntegerField(null=True, blank=True, verbose_name="心率(bpm)")
    respiratory_rate = models.IntegerField(null=True, blank=True, verbose_name="呼吸頻率(per min)")

    # 主訴與症狀
    chief_complaint = models.TextField(blank=True, verbose_name="主訴")
    physical_examination = models.TextField(blank=True, verbose_name="理學檢查結果")

    # 診斷相關
    diagnosis = models.TextField(verbose_name="診斷結果")
    diagnosis_confidence = models.IntegerField(default=3, choices=[(1, '很低信心'), (2, '低信心'), (3, '中等信心'), (4, '高信心'), (5, '非常有信心')], verbose_name="診斷信心度")

    # 治療相關
    treatment = models.TextField(verbose_name="治療內容")
    treatment_plan = models.TextField(blank=True, verbose_name="治療計劃")

    # 追蹤與費用
    follow_up_required = models.BooleanField(default=False, verbose_name="需要追蹤")
    follow_up_date = models.DateField(null=True, blank=True, verbose_name="追蹤日期")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="總費用")

    # 其他備註
    notes = models.TextField(blank=True, verbose_name="備註與醫囑")
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

    @property
    def medical_details(self):
        """解析 notes 欄位中的結構化醫療資訊"""
        import re
        import json

        details = {
            'weight': None,
            'temperature': None,
            'heart_rate': None,
            'respiratory_rate': None,
            'symptoms': [],
            'prescriptions': []
        }

        if not self.notes:
            return details

        # 解析體重
        weight_match = re.search(r'體重:\s*(\d+(?:\.\d+)?)kg', self.notes)
        if weight_match:
            details['weight'] = float(weight_match.group(1))

        # 解析體溫
        temp_match = re.search(r'體溫:\s*(\d+(?:\.\d+)?)°C', self.notes)
        if temp_match:
            details['temperature'] = float(temp_match.group(1))

        # 解析心率
        hr_match = re.search(r'心率:\s*(\d+)次/分', self.notes)
        if hr_match:
            details['heart_rate'] = int(hr_match.group(1))

        # 解析呼吸頻率
        rr_match = re.search(r'呼吸:\s*(\d+)次/分', self.notes)
        if rr_match:
            details['respiratory_rate'] = int(rr_match.group(1))

        # 解析症狀
        symptom_pattern = r'•\s*([^(]+)\s*\(嚴重程度:\s*([^)]+)\)'
        symptoms = re.findall(symptom_pattern, self.notes)
        for name, severity in symptoms:
            details['symptoms'].append({
                'name': name.strip(),
                'severity': severity.strip()
            })

        # 解析處方藥品
        # 匹配處方區段，從 "💊 處方藥品:" 開始到下一個 emoji 區段或結尾
        prescription_section = re.search(r'💊 處方藥品:(.*?)(?=⚕️|📅|$)', self.notes, re.DOTALL)
        if prescription_section:
            prescription_text = prescription_section.group(1)

            # 分步解析處方信息
            # 首先找到所有藥品條目
            drug_entries = re.split(r'\n\s*•\s*', prescription_text.strip())

            for entry in drug_entries:
                if not entry.strip():
                    continue

                lines = entry.strip().split('\n')
                if not lines:
                    continue

                # 第一行包含藥品名稱
                first_line = lines[0].strip()
                name_match = re.match(r'•?\s*([^(]+)\s*\(([^)]+)\)', first_line)

                if name_match:
                    chinese_name = name_match.group(1).strip()
                    english_name = name_match.group(2).strip()
                else:
                    chinese_name = first_line.replace('•', '').strip()
                    english_name = ""

                # 解析其他屬性
                dosage = ""
                frequency = ""
                route = ""
                duration = ""
                instructions = ""

                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith('劑量:'):
                        dosage = line.replace('劑量:', '').strip()
                    elif line.startswith('頻率:'):
                        frequency = line.replace('頻率:', '').strip()
                    elif line.startswith('給藥方式:'):
                        route = line.replace('給藥方式:', '').strip()
                    elif line.startswith('療程:'):
                        duration = line.replace('療程:', '').strip()
                    elif line.startswith('用藥指示:'):
                        instructions = line.replace('用藥指示:', '').strip()

                # 組合藥品名稱
                medication = f"{chinese_name} ({english_name})" if english_name else chinese_name

                details['prescriptions'].append({
                    'medication': medication,
                    'dosage': dosage,
                    'frequency': frequency,
                    'route': route,
                    'duration': duration,
                    'instructions': instructions
                })

        return details

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


#=========== 領養專區模組 ==============#

REGION_CHOICES = [
    ('north', '北部地區'),
    ('central', '中部地區'),
    ('south', '南部地區'),
    ('east', '東部地區'),
    ('island', '離島地區'),
]

def validate_pdf(value):
    if not value.name.endswith('.pdf'):
        raise ValidationError("只允許上傳 PDF 檔案")

class AdoptionPet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='adoptions', verbose_name='飼主')
    species = models.CharField(max_length=50, verbose_name='種類')
    breed = models.CharField(max_length=50, verbose_name='品種')
    name = models.CharField(max_length=20)
    sterilization_status = models.CharField(max_length=20, choices=SterilizationStatus.choices)
    chip = models.CharField(max_length=15, blank=True, null=True, unique=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    weight = models.FloatField(null=True, blank=True)
    vaccine = models.TextField(max_length=20, blank=True)
    feature = models.TextField(max_length=100, blank=True)
    adopt_picture1 = models.ImageField(upload_to='pet_pictures/', blank=True, null=True)
    is_adopted = models.BooleanField(default=False)
    posted_date = models.DateTimeField(auto_now_add=True)
    physical_condition = models.TextField(max_length=100, blank=True)
    adoption_condition = models.TextField(max_length=100, blank=True)
    adopt_picture2 = models.ImageField(upload_to='pet_pictures/', blank=True, null=True)
    adopt_picture3 = models.ImageField(upload_to='pet_pictures/', blank=True, null=True)
    adopt_picture4 = models.ImageField(upload_to='pet_pictures/', blank=True, null=True)
    phone = models.CharField("手機號碼", max_length=20, blank=True)
    line_id = models.CharField("LINE ID", max_length=50, blank=True)
    adopt_place = models.CharField("領養地點", max_length=100, blank=True, choices=REGION_CHOICES)
    original_pet = models.ForeignKey(Pet, on_delete=models.SET_NULL, null=True, blank=True)
    is_publish = models.BooleanField(default=True)

    health_certificate = models.FileField(
        upload_to='pet_certificate/health_certificates/',
        validators=[validate_pdf],
        blank=True, null=True,
        verbose_name="健康證明 (PDF)"
    )
    vaccine_certificate = models.FileField(
        upload_to='pet_certificate/vaccine_certificates/',
        validators=[validate_pdf],
        blank=True, null=True,
        verbose_name="疫苗接種證明 (PDF)"
    )

    def __str__(self):
        return f"{self.name} 的送養紀錄（{self.posted_date.date()}）"

    @property
    def age(self):
        if not self.birth_date:
            return None

        today = date.today()
        years = today.year - self.birth_date.year
        months = today.month - self.birth_date.month
        days = today.day - self.birth_date.day

        if days < 0:
            months -= 1
        if months < 0:
            years -= 1
            months += 12

        total_months = years * 12 + months

        if total_months < 1:
            return "未滿 1 個月"
        elif total_months < 12:
            return f"{total_months} 個月"
        else:
            return f"{years} 歲"

    @property
    def detailed_age(self):
        """詳細年齡顯示：X年X個月X天"""
        if not self.birth_date:
            return "年齡未知"

        from datetime import date
        today = date.today()
        birth = self.birth_date

        # 計算年、月、日
        years = today.year - birth.year
        months = today.month - birth.month
        days = today.day - birth.day

        # 處理負數天數
        if days < 0:
            months -= 1
            # 獲取上個月的天數
            if today.month == 1:
                prev_month = 12
                prev_year = today.year - 1
            else:
                prev_month = today.month - 1
                prev_year = today.year

            import calendar
            days_in_prev_month = calendar.monthrange(prev_year, prev_month)[1]
            days += days_in_prev_month

        # 處理負數月份
        if months < 0:
            years -= 1
            months += 12

        # 格式化顯示
        result_parts = []
        if years > 0:
            result_parts.append(f"{years}年")
        if months > 0:
            result_parts.append(f"{months}個月")
        if days > 0:
            result_parts.append(f"{days}天")

        if not result_parts:
            return "今天出生"

        age_str = "".join(result_parts)

        # 計算總年齡（歲）
        total_years = years
        if months >= 6:  # 超過6個月算半歲
            total_years += 0.5

        if total_years > 0:
            if total_years == int(total_years):
                age_str += f"（{int(total_years)}歲）"
            else:
                age_str += f"（{total_years}歲）"

        return age_str

# 更改飼主
class TransferRequest(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE)
    from_owner = models.ForeignKey(User, related_name='sent_transfers', on_delete=models.CASCADE)
    to_email = models.EmailField()
    to_phone = models.CharField(max_length=20)
    to_user = models.ForeignKey(User, null=True, blank=True, related_name='received_transfers', on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=[
        ('pending', '待確認'),
        ('accepted', '已接受'),
        ('rejected', '已拒絕'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    from_owner_has_seen = models.BooleanField(default=False)
    to_user_has_seen = models.BooleanField(default=False)

# 為了向下兼容，為 User 模型添加 vet_profile 屬性
def get_vet_profile(self):
    """獲取用戶的獸醫檔案（向下兼容）"""
    try:
        # 修正：應該返回VetDoctor實例，不是Profile
        return VetDoctor.objects.get(user=self)
    except VetDoctor.DoesNotExist:
        return None

# 將 vet_profile 屬性添加到 User 模型
User.add_to_class('vet_profile', property(get_vet_profile))

#===========📅 進階排班管理模組============#

class ScheduleTemplate(models.Model):
    """排班模板 - 支援快速套用常用排班"""
    
    TEMPLATE_TYPE_CHOICES = [
        ('personal', '個人模板'),
        ('clinic', '診所模板'),
        ('system', '系統模板'),
    ]
    
    SCHEDULE_PATTERN_CHOICES = [
        ('weekly', '週循環'),
        ('monthly', '月循環'), 
        ('custom', '自訂模式'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='模板名稱')
    description = models.TextField(blank=True, verbose_name='模板描述')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, verbose_name='模板類型')
    schedule_pattern = models.CharField(max_length=20, choices=SCHEDULE_PATTERN_CHOICES, default='weekly', verbose_name='排班模式')
    
    # 模板所有者
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='建立者')
    clinic = models.ForeignKey(VetClinic, on_delete=models.CASCADE, null=True, blank=True, verbose_name='所屬診所')
    
    # 模板內容 (JSON格式儲存排班資料)
    template_data = models.JSONField(default=dict, verbose_name='模板資料')
    
    # 使用統計
    usage_count = models.IntegerField(default=0, verbose_name='使用次數')
    
    # 狀態
    is_active = models.BooleanField(default=True, verbose_name='啟用狀態')
    is_public = models.BooleanField(default=False, verbose_name='公開模板')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '排班模板'
        verbose_name_plural = '排班模板'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def increment_usage(self):
        """增加使用次數"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])

class EnhancedVetSchedule(models.Model):
    """增強版獸醫排班 - 支援更靈活的排班管理"""
    
    SCHEDULE_TYPE_CHOICES = [
        ('regular', '固定排班'),
        ('rotation', '輪班制'),
        ('on_call', '值班制'),
        ('temporary', '臨時排班'),
        ('substitute', '代班'),
    ]
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('pending', '待審核'),
        ('approved', '已核准'),
        ('active', '生效中'),
        ('expired', '已到期'),
        ('cancelled', '已取消'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '低優先級'),
        ('normal', '一般'),
        ('high', '高優先級'),
        ('urgent', '緊急'),
    ]
    
    # 基本資訊
    doctor = models.ForeignKey(VetDoctor, on_delete=models.CASCADE, related_name='enhanced_schedules')
    clinic = models.ForeignKey(VetClinic, on_delete=models.CASCADE, verbose_name='診所')
    
    # 排班基本設定
    title = models.CharField(max_length=200, verbose_name='排班標題')
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE_CHOICES, default='regular', verbose_name='排班類型')
    
    # 時間設定
    start_date = models.DateField(verbose_name='開始日期')
    end_date = models.DateField(null=True, blank=True, verbose_name='結束日期')
    
    # 週排班設定
    weekdays = models.JSONField(default=list, verbose_name='工作日設定')  # [0,1,2,3,4] 代表週一到週五
    daily_time_slots = models.JSONField(default=dict, verbose_name='每日時段設定')  # {"0": [{"start": "09:00", "end": "12:00"}, {...}]}
    
    # 預約相關
    appointment_duration = models.IntegerField(default=30, verbose_name='預約時長(分鐘)')
    max_appointments_per_slot = models.IntegerField(default=1, verbose_name='每時段最大預約數')
    buffer_time = models.IntegerField(default=0, verbose_name='緩衝時間(分鐘)')
    
    # 管理欄位
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='狀態')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal', verbose_name='優先級')
    
    # 審核相關
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='approved_schedules', verbose_name='核准者')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='核准時間')
    
    # 備註和設定
    notes = models.TextField(blank=True, verbose_name='備註')
    is_holiday_excluded = models.BooleanField(default=True, verbose_name='排除國定假日')
    
    # 排班來源
    created_from_template = models.ForeignKey(ScheduleTemplate, on_delete=models.SET_NULL, 
                                            null=True, blank=True, verbose_name='來源模板')
    parent_schedule = models.ForeignKey('self', on_delete=models.CASCADE, 
                                      null=True, blank=True, verbose_name='父排班')
    
    # 衝突檢測
    has_conflicts = models.BooleanField(default=False, verbose_name='有衝突')
    conflict_details = models.JSONField(default=dict, verbose_name='衝突詳情')
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='建立者')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '增強排班'
        verbose_name_plural = '增強排班'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['doctor', 'start_date', 'status']),
            models.Index(fields=['clinic', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.title} ({self.start_date})"
    
    def clean(self):
        """資料驗證"""
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError('結束日期不能早於開始日期')
    
    def check_conflicts(self, save=True):
        """檢查排班衝突"""
        conflicts = []
        
        # 檢查同醫師時間重疊
        overlapping = EnhancedVetSchedule.objects.filter(
            doctor=self.doctor,
            status__in=['approved', 'active'],
            start_date__lte=self.end_date or self.start_date,
            end_date__gte=self.start_date
        ).exclude(id=self.id)
        
        for schedule in overlapping:
            # 檢查週工作日重疊
            common_weekdays = set(self.weekdays) & set(schedule.weekdays)
            if common_weekdays:
                conflicts.append({
                    'type': 'doctor_time_overlap',
                    'schedule_id': schedule.id,
                    'schedule_title': schedule.title,
                    'message': f'與排班「{schedule.title}」時間重疊'
                })
        
        # 檢查診所容量限制
        if self.clinic.clinic_mode == 'single' and self.doctor.clinic != self.clinic:
            conflicts.append({
                'type': 'clinic_mode_violation',
                'message': '單一獸醫診所模式下不允許外部獸醫師排班'
            })
        
        self.has_conflicts = len(conflicts) > 0
        self.conflict_details = {'conflicts': conflicts, 'checked_at': timezone.now().isoformat()}
        
        if save:
            self.save(update_fields=['has_conflicts', 'conflict_details'])
        
        return conflicts
    
    def generate_daily_schedule(self, target_date):
        """生成指定日期的具體排班資料"""
        weekday = target_date.weekday()
        
        if weekday not in self.weekdays:
            return []
        
        daily_slots = self.daily_time_slots.get(str(weekday), [])
        schedule_items = []
        
        for slot in daily_slots:
            try:
                start_time = datetime.strptime(slot['start'], '%H:%M').time()
                end_time = datetime.strptime(slot['end'], '%H:%M').time()
                
                schedule_items.append({
                    'date': target_date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_minutes': self.appointment_duration,
                    'max_appointments': self.max_appointments_per_slot,
                    'buffer_time': self.buffer_time,
                })
            except (KeyError, ValueError):
                continue
        
        return schedule_items
    
    @property
    def total_work_hours_per_week(self):
        """計算每週總工作時數"""
        total_minutes = 0
        
        for weekday in self.weekdays:
            daily_slots = self.daily_time_slots.get(str(weekday), [])
            for slot in daily_slots:
                try:
                    start_time = datetime.strptime(slot['start'], '%H:%M').time()
                    end_time = datetime.strptime(slot['end'], '%H:%M').time()
                    
                    # 轉換為分鐘計算
                    start_minutes = start_time.hour * 60 + start_time.minute
                    end_minutes = end_time.hour * 60 + end_time.minute
                    
                    # 處理跨日情況
                    if end_minutes <= start_minutes:
                        end_minutes += 24 * 60
                    
                    slot_minutes = end_minutes - start_minutes
                    total_minutes += slot_minutes
                    
                except (KeyError, ValueError, AttributeError):
                    continue
        
        return round(total_minutes / 60.0, 1)
    
    @property
    def is_active(self):
        """檢查排班是否當前有效"""
        today = date.today()
        return (self.status == 'active' and 
                self.start_date <= today and 
                (not self.end_date or self.end_date >= today))

class ScheduleChangeRequest(models.Model):
    """排班異動申請 - 支援請假、調班等申請"""
    
    REQUEST_TYPE_CHOICES = [
        ('leave', '請假'),
        ('swap', '調班'),
        ('overtime', '加班'),
        ('substitute', '代班'),
        ('time_change', '時間調整'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待審核'),
        ('approved', '已核准'),
        ('rejected', '已拒絕'),
        ('cancelled', '已取消'),
    ]
    
    # 基本資訊
    requestor = models.ForeignKey(VetDoctor, on_delete=models.CASCADE, verbose_name='申請人')
    clinic = models.ForeignKey(VetClinic, on_delete=models.CASCADE, verbose_name='診所')
    
    # 異動類型和原因
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES, verbose_name='異動類型')
    reason = models.TextField(verbose_name='異動原因')
    
    # 原始排班
    original_schedule = models.ForeignKey(EnhancedVetSchedule, on_delete=models.CASCADE, 
                                        related_name='change_requests', verbose_name='原排班')
    
    # 異動時間範圍
    change_start_date = models.DateField(verbose_name='異動開始日期')
    change_end_date = models.DateField(verbose_name='異動結束日期')
    change_start_time = models.TimeField(null=True, blank=True, verbose_name='異動開始時間')
    change_end_time = models.TimeField(null=True, blank=True, verbose_name='異動結束時間')
    
    # 替代安排(調班、代班用)
    substitute_doctor = models.ForeignKey(VetDoctor, on_delete=models.SET_NULL, 
                                        null=True, blank=True, 
                                        related_name='substitute_requests', verbose_name='代班醫師')
    
    # 審核相關
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='狀態')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  verbose_name='審核者')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='審核時間')
    review_notes = models.TextField(blank=True, verbose_name='審核意見')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '排班異動申請'
        verbose_name_plural = '排班異動申請'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.requestor.user.get_full_name()} - {self.get_request_type_display()} ({self.change_start_date})"

class ClinicScheduleRule(models.Model):
    """診所排班規則 - 定義診所的排班約束條件"""
    
    clinic = models.OneToOneField(VetClinic, on_delete=models.CASCADE, 
                                related_name='schedule_rules', verbose_name='診所')
    
    # 時間限制
    min_shift_duration = models.IntegerField(default=240, verbose_name='最短班次時間(分鐘)')  # 4小時
    max_shift_duration = models.IntegerField(default=480, verbose_name='最長班次時間(分鐘)')  # 8小時
    min_break_between_shifts = models.IntegerField(default=720, verbose_name='班次間最短休息(分鐘)')  # 12小時
    
    # 週工作限制
    max_work_hours_per_week = models.IntegerField(default=40, verbose_name='每週最大工作時數')
    max_consecutive_work_days = models.IntegerField(default=6, verbose_name='最大連續工作天數')
    
    # 人力配置
    min_doctors_per_shift = models.IntegerField(default=1, verbose_name='每班最少獸醫數')
    max_doctors_per_shift = models.IntegerField(default=3, verbose_name='每班最多獸醫數')
    
    # 請假規則
    min_leave_notice_days = models.IntegerField(default=7, verbose_name='請假最少提前天數')
    max_consecutive_leave_days = models.IntegerField(default=14, verbose_name='最大連續請假天數')
    
    # 自動審核設定
    auto_approve_leave_hours = models.IntegerField(default=8, verbose_name='自動核准請假時數(小時)')
    require_substitute_for_leave = models.BooleanField(default=True, verbose_name='請假需要代班安排')
    
    # 通知設定
    notify_schedule_changes = models.BooleanField(default=True, verbose_name='排班異動通知')
    notify_conflict_detection = models.BooleanField(default=True, verbose_name='衝突檢測通知')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '診所排班規則'
        verbose_name_plural = '診所排班規則'
    
    def __str__(self):
        return f"{self.clinic.clinic_name} - 排班規則"

# 工具函數
def time_overlap(start1, end1, start2, end2):
    """檢查兩個時間範圍是否重疊"""
    return start1 < end2 and start2 < end1

def get_work_days_in_range(start_date, end_date, weekdays, exclude_holidays=True):
    """取得日期範圍內的工作日"""
    work_days = []
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() in weekdays:
            if not exclude_holidays or not is_holiday(current_date):
                work_days.append(current_date)
        current_date += timedelta(days=1)
    
    return work_days

def is_holiday(date_obj):
    """檢查是否為假日 - 可以擴展為查詢國定假日API"""
    # 簡單實作：只檢查週末
    return date_obj.weekday() >= 5  # 週六、週日


#===========💊 政府動物用藥資料庫模組===============#
class AnimalDrug(models.Model):
    """動物用藥資訊模型 - 整合農委會開放資料"""
    
    # 基本藥物資訊
    license_number = models.CharField(max_length=100, unique=True, verbose_name='許可證字號')
    chinese_name = models.CharField(max_length=255, blank=True, verbose_name='中文品名')
    english_name = models.CharField(max_length=255, blank=True, verbose_name='英文品名')
    
    # 製造商資訊
    manufacturer = models.CharField(max_length=200, blank=True, verbose_name='製造廠名稱')
    applicant = models.CharField(max_length=200, blank=True, verbose_name='申請商名稱')
    
    # 藥物特性
    dosage_form = models.CharField(max_length=100, blank=True, verbose_name='劑型')
    packaging = models.CharField(max_length=200, blank=True, verbose_name='包裝')
    indications = models.TextField(blank=True, verbose_name='適應症')
    active_ingredients = models.TextField(blank=True, verbose_name='有效成分')
    target_animals = models.CharField(max_length=200, blank=True, verbose_name='適用動物')
    
    # 狀態管理
    is_active = models.BooleanField(default=True, verbose_name='藥品是否有效')
    sync_date = models.DateTimeField(auto_now=True, verbose_name='最後同步時間')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '動物用藥'
        verbose_name_plural = '動物用藥'
        ordering = ['chinese_name']
    
    def __str__(self):
        return f"{self.chinese_name or self.english_name} ({self.license_number})"
    
    @classmethod
    def search_drugs(cls, query, limit=20):
        """智慧搜索動物用藥"""
        if not query or len(query.strip()) < 2:
            return cls.objects.none()
            
        from django.db.models import Q
        
        # 多維度搜索：中文名、英文名、成分、適應症
        search_conditions = Q()
        
        # 中文關鍵字搜索
        search_conditions |= Q(chinese_name__icontains=query)
        
        # 英文關鍵字搜索（不區分大小寫）
        search_conditions |= Q(english_name__icontains=query)
        
        # 有效成分搜索
        search_conditions |= Q(active_ingredients__icontains=query)
        
        # 適應症搜索
        search_conditions |= Q(indications__icontains=query)
        
        # 許可證字號搜索
        search_conditions |= Q(license_number__icontains=query)
        
        return cls.objects.filter(
            search_conditions,
            is_active=True
        ).distinct()[:limit]
