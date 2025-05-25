# petapp/models.py
# 匯入 Django 所需模組
from django.db import models
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

# 使用者資料擴充：Profile 模型，用於區分飼主與獸醫，並儲存聯絡與診所資訊
class Profile(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('owner', '飼主'),
        ('vet', '獸醫'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name='手機號碼')
    vet_license = models.FileField(upload_to='vet_licenses/', blank=True, null=True, verbose_name='獸醫證照')
    vet_license_city = models.CharField(max_length=20, blank=True, null=True, verbose_name='執業執照縣市')
    is_verified_vet = models.BooleanField(default=False, verbose_name='獸醫身分已驗證')
    clinic_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='醫院／診所名稱')
    clinic_address = models.CharField(max_length=255, blank=True, null=True, verbose_name='醫院／診所地址')

    def __str__(self):
        return f"{self.user.username} ({self.get_account_type_display()})"

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

# 飼主幫寵物預約看診
class VetAppointment(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, verbose_name="預約寵物")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="飼主")
    vet = models.ForeignKey(Profile, on_delete=models.CASCADE, limit_choices_to={'account_type': 'vet'}, verbose_name="預約獸醫")
    date = models.DateField(verbose_name="預約日期")
    time = models.TimeField(verbose_name="預約時間")
    reason = models.TextField(verbose_name="預約原因", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pet.name} 預約 {self.vet.clinic_name or self.vet.user.username} 於 {self.date} {self.time}"

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
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, verbose_name="寵物")
    vet = models.ForeignKey(Profile, limit_choices_to={'account_type': 'vet'}, on_delete=models.SET_NULL, null=True, verbose_name="看診獸醫")
    visit_date = models.DateField(auto_now_add=True, verbose_name="看診日期")
    clinic_location = models.CharField(max_length=100, verbose_name="看診地點")
    diagnosis = models.TextField(verbose_name="診斷結果")
    treatment = models.TextField(verbose_name="治療內容")
    notes = models.TextField(blank=True, verbose_name="備註")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return f"{self.pet.name} - {self.visit_date}"

# 星期與時段常數對應（用於排班與顯示）
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
    
# ============= 動物認領養功能模型 =============

class AdoptionShelter(models.Model):
    """收容所資料表"""
    shelter_code = models.IntegerField(unique=True, verbose_name="收容所代碼")
    shelter_name = models.CharField(max_length=100, verbose_name="收容所名稱")
    address = models.CharField(max_length=200, blank=True, verbose_name="地址")
    phone = models.CharField(max_length=50, blank=True, verbose_name="電話")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "收容所"
        verbose_name_plural = "收容所"
        db_table = 'adoption_shelters'
        
    def __str__(self):
        return self.shelter_name

class AdoptionAnimal(models.Model):
    """認領養動物資料表"""
    
    # 基本資料
    animal_id = models.CharField(max_length=50, unique=True, verbose_name="動物編號")
    shelter_pkid = models.CharField(max_length=50, blank=True, verbose_name="收容編號")
    animal_area_pkid = models.IntegerField(null=True, blank=True, verbose_name="縣市代碼")
    animal_shelter_pkid = models.IntegerField(null=True, blank=True, verbose_name="收容所代碼")
    
    # 動物資訊
    animal_place = models.CharField(max_length=100, blank=True, verbose_name="實際所在地")
    animal_kind = models.CharField(max_length=50, blank=True, verbose_name="動物類型")
    animal_variety = models.CharField(max_length=100, blank=True, verbose_name="動物品種")
    animal_sex = models.CharField(max_length=20, blank=True, verbose_name="性別")
    animal_bodytype = models.CharField(max_length=20, blank=True, verbose_name="體型")
    animal_colour = models.CharField(max_length=50, blank=True, verbose_name="毛色")
    animal_age = models.CharField(max_length=20, blank=True, verbose_name="年齡")
    animal_sterilization = models.CharField(max_length=20, blank=True, verbose_name="絕育狀況")
    animal_bacterin = models.CharField(max_length=20, blank=True, verbose_name="疫苗接種")
    animal_foundplace = models.CharField(max_length=200, blank=True, verbose_name="尋獲地")
    animal_title = models.CharField(max_length=200, blank=True, verbose_name="標題")
    animal_status = models.CharField(max_length=50, blank=True, verbose_name="認養狀態")
    animal_remark = models.TextField(blank=True, verbose_name="備註")
    animal_caption = models.TextField(blank=True, verbose_name="說明")
    
    # 時間資訊
    animal_opendate = models.DateTimeField(null=True, blank=True, verbose_name="開放認養時間(起)")
    animal_closeddate = models.DateTimeField(null=True, blank=True, verbose_name="開放認養時間(迄)")
    animal_update = models.DateTimeField(null=True, blank=True, verbose_name="資料異動時間")
    animal_createtime = models.DateTimeField(null=True, blank=True, verbose_name="資料建立時間")
    
    # 收容所資訊
    shelter_name = models.CharField(max_length=100, blank=True, verbose_name="收容所名稱")
    shelter_address = models.CharField(max_length=200, blank=True, verbose_name="收容所地址")
    shelter_tel = models.CharField(max_length=50, blank=True, verbose_name="收容所電話")
    
    # 圖片資訊
    album_file = models.URLField(blank=True, verbose_name="圖片網址")
    album_update = models.DateTimeField(null=True, blank=True, verbose_name="圖片更新時間")
    
    # 品種與其他
    animal_subid = models.CharField(max_length=50, blank=True, verbose_name="動物品種")
    cdate = models.DateTimeField(null=True, blank=True, verbose_name="資料更新時間")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    is_active = models.BooleanField(default=True, verbose_name="是否啟用")
    
    # 外鍵關聯
    shelter = models.ForeignKey(AdoptionShelter, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="收容所")
    
    class Meta:
        verbose_name = "認領養動物"
        verbose_name_plural = "認領養動物"
        ordering = ['-animal_update', '-created_at']
        db_table = 'adoption_animals'
        indexes = [
            models.Index(fields=['animal_kind']),
            models.Index(fields=['animal_status']),
            models.Index(fields=['animal_area_pkid']),
            models.Index(fields=['animal_shelter_pkid']),
        ]
    
    def __str__(self):
        return f"{self.animal_title or self.animal_id} - {self.animal_kind}"
    
    @property
    def status_display(self):
        """取得狀態顯示名稱"""
        status_map = {
            'OPEN': 'open',
            'CLOSED': 'closed', 
            'ADOPTED': 'adopted'
        }
        return status_map.get(self.animal_status, 'other')
    
    @property
    def is_available(self):
        """是否可認養"""
        return self.animal_status == 'OPEN' and self.is_active
    
    @property
    def status_chinese(self):
        """中文狀態顯示"""
        status_map = {
            'OPEN': '開放認養',
            'CLOSED': '不開放認養',
            'ADOPTED': '已認養'
        }
        return status_map.get(self.animal_status, '其他')
    @property
    def animal_sex_display(self):
        """性別中文顯示"""
        sex_map = {
            'M': '公',
            'F': '母',
        }
        return sex_map.get(self.animal_sex, self.animal_sex or '未知')
    
    @property
    def animal_age_display(self):
        """年齡中文顯示"""
        age_map = {
            'ADULT': '成年',
            'CHILD': '幼年',
        }
        return age_map.get(self.animal_age, self.animal_age or '未知')
    
    @property
    def animal_bodytype_display(self):
        """體型中文顯示"""
        bodytype_map = {
            'SMALL': '小型',
            'MEDIUM': '中型',
            'LARGE': '大型',
        }
        return bodytype_map.get(self.animal_bodytype, self.animal_bodytype or '未知')
    
    @property
    def animal_sterilization_display(self):
        """絕育狀況中文顯示"""
        sterilization_map = {
            'T': '已絕育',
            'F': '未絕育',
        }
        return sterilization_map.get(self.animal_sterilization, self.animal_sterilization or '未知')
    
    @property
    def animal_bacterin_display(self):
        """疫苗接種中文顯示"""
        bacterin_map = {
            'T': '已接種',
            'F': '未接種',
        }
        return bacterin_map.get(self.animal_bacterin, self.animal_bacterin or '未知')
    
    

class AdoptionFavorite(models.Model):
    """使用者收藏動物"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    animal = models.ForeignKey(AdoptionAnimal, on_delete=models.CASCADE, verbose_name="動物")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏時間")
    
    class Meta:
        unique_together = ('user', 'animal')
        verbose_name = "收藏動物"
        verbose_name_plural = "收藏動物"
        db_table = 'adoption_favorites'
    
    def __str__(self):
        return f"{self.user.username} 收藏 {self.animal.animal_title}"

class AdoptionApplication(models.Model):
    """認養申請"""
    APPLICATION_STATUS_CHOICES = [
        ('PENDING', '待審核'),
        ('APPROVED', '已通過'),
        ('REJECTED', '已拒絕'),
        ('COMPLETED', '已完成'),
    ]
    
    animal = models.ForeignKey(AdoptionAnimal, on_delete=models.CASCADE, verbose_name="認養動物")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="申請人")
    
    # 申請人資訊
    applicant_name = models.CharField(max_length=50, verbose_name="申請人姓名")
    applicant_phone = models.CharField(max_length=20, verbose_name="聯絡電話")
    applicant_email = models.EmailField(verbose_name="電子信箱")
    applicant_address = models.TextField(verbose_name="居住地址")
    
    # 認養相關資訊
    experience = models.TextField(verbose_name="飼養經驗")
    housing_type = models.CharField(max_length=50, verbose_name="居住環境")
    family_consent = models.BooleanField(verbose_name="家人同意")
    
    # 申請狀態
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS_CHOICES, default='PENDING', verbose_name="申請狀態")
    admin_notes = models.TextField(blank=True, verbose_name="管理員備註")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="申請時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "認養申請"
        verbose_name_plural = "認養申請"
        ordering = ['-created_at']
        db_table = 'adoption_applications'
    
    def __str__(self):
        return f"{self.applicant_name} 申請認養 {self.animal.animal_title}"