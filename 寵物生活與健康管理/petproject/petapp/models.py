# petapp/models.py
from django.db import models

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

import json

# Create your models here.
# 未來可在此定義寵物相關模型，例如 Pet、VaccineRecord 等
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

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class Species(models.TextChoices):  #種類
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

class Pet(models.Model):
    species = models.CharField(max_length=10, choices=Species.choices)
    breed = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    sterilization_status = models.CharField(max_length=20, choices=SterilizationStatus.choices)
    chip = models.CharField(max_length=100, blank=True, null=True)
    year_of_birth = models.IntegerField(null=True, blank=True)
    month_of_birth = models.IntegerField(null=True, blank=True)
    day_of_birth = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    weight = models.FloatField(null=True, blank=True)
    feature = models.TextField(blank=True)
    picture = models.ImageField(upload_to='pet_pictures/', blank=True, null=True)

    def __str__(self):
        return self.name
    
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
    created_at = models.DateTimeField(auto_now_add=True)  # 實際填寫的時間戳
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    content = models.TextField(blank=True)

    def __str__(self):
        return f"{self.pet.name} 的生活記錄（{self.date}）"

# 新增寵物地點模型
class PetLocation(models.Model):
    """寵物相關地點模型"""

    LOCATION_TYPES = [
    ('hospital', '醫院'),
    ('cosmetic', '美容'),
    ('park', '公園'),
    ('product', '用品'),
    ('shelter', '收容所'),
    ('funeral', '殯葬'),
    ('live', '住宿'),
    ('boarding', '寄宿')

    ]

    # 基本資訊
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name='名稱')
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name='地址')
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name='電話')
    website = models.TextField(blank=True, null=True, verbose_name='網站')
    
    # 服務類型標籤 - 使用布林欄位標記各種服務
    is_cosmetic = models.BooleanField(default=False, verbose_name='提供美容')
    is_funeral = models.BooleanField(default=False, verbose_name='提供殯葬')
    is_hospital = models.BooleanField(default=False, verbose_name='提供醫療')
    is_live = models.BooleanField(default=False, verbose_name='提供住宿')
    is_boarding =models.BooleanField(default=False, verbose_name='寄宿')
    is_park = models.BooleanField(default=False, verbose_name='公園')
    is_product = models.BooleanField(default=False, verbose_name='銷售用品')
    is_shelter = models.BooleanField(default=False, verbose_name='收容所')
    
    # 地理資訊
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='城市')
    district = models.CharField(max_length=100, blank=True, null=True, verbose_name='地區')
    lat = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True, verbose_name='緯度')
    lon = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True, verbose_name='經度')
    
    # 評分資訊
    rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, verbose_name='評分')
    rating_count = models.IntegerField(blank=True, null=True, verbose_name='評分數量')
    
    # 營業資訊
    business_hours = models.JSONField(blank=True, null=True, verbose_name='營業時間')
    
    # 醫院特有屬性
    has_emergency = models.BooleanField(default=False, verbose_name='提供24小時急診')
    
    # 寵物支援
    support_small_dog = models.BooleanField(default=False, verbose_name='小型犬')
    support_medium_dog = models.BooleanField(default=False, verbose_name='中型犬')
    support_large_dog = models.BooleanField(default=False, verbose_name='大型犬')
    support_cat = models.BooleanField(default=False, verbose_name='貓')
    support_bird = models.BooleanField(default=False, verbose_name='鳥類')
    support_rodent = models.BooleanField(default=False, verbose_name='嚙齒類/小動物')
    support_reptile = models.BooleanField(default=False, verbose_name='爬蟲類')
    support_other = models.BooleanField(default=False, verbose_name='其他寵物')
    
    # 保留原始的支援寵物類型字串，用於顯示和相容性
    supported_pet_types = models.TextField(blank=True, null=True, verbose_name='寵物類型(原始)')
    
    # 是否為自動推斷的寵物類型
    is_pet_type_inferred = models.BooleanField(default=False, verbose_name='自動推斷的類型')
    
    # 其他資訊
    additional_info = models.JSONField(blank=True, null=True, verbose_name='額外資訊')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        db_table = 'pet_locations'  # 指定資料表名稱
        verbose_name = '寵物地點'
        verbose_name_plural = '寵物地點'
        indexes = [
            models.Index(fields=['city', 'district'], name='city_district_idx'),
            models.Index(fields=['is_hospital'], name='hospital_idx'),
            models.Index(fields=['is_live'], name='live_idx'),
            models.Index(fields=['is_cosmetic'], name='cosmetic_idx'),
            models.Index(fields=['has_emergency'], name='emergency_idx'),
            models.Index(fields=['support_small_dog'], name='small_dog_idx'),
            models.Index(fields=['support_medium_dog'], name='medium_dog_idx'),
            models.Index(fields=['support_large_dog'], name='large_dog_idx'),
            models.Index(fields=['support_cat'], name='cat_idx'),
        ]

    def __str__(self):
        services = self.get_services_list()
        service_text = f" ({', '.join(services)})" if services else ""
        return f"{self.name or '未命名'}{service_text}"
    
    def get_services_list(self):
        """取得提供的服務列表"""
        services = []
        if self.is_cosmetic:
            services.append('美容')
        if self.is_funeral:
            services.append('殯葬')
        if self.is_hospital:
            services.append('醫療')
        if self.is_live:
            services.append('住宿')
        if self.is_park:
            services.append('公園')
        if self.is_product:
            services.append('用品')
        if self.is_shelter:
            services.append('收容')
        return services
    
    def get_full_address(self):
        """取得完整地址 - 修正版本：只返回address欄位，避免重複"""
        # 只返回address欄位，不包含city和district
        return self.address if self.address else None
            
    
    def get_business_hours_formatted(self):
        """格式化營業時間"""
        if not self.business_hours:
            return None
        
        days_map = {
            'monday': '週一',
            'tuesday': '週二',
            'wednesday': '週三',
            'thursday': '週四',
            'friday': '週五',
            'saturday': '週六',
            'sunday': '週日'
        }
        
        formatted = {}
        for eng_day, chinese_day in days_map.items():
            if eng_day in self.business_hours:
                formatted[chinese_day] = self.business_hours[eng_day]
        
        return formatted
    
    def is_of_type(self, type_code):
        """檢查地點是否提供特定服務"""
        attr_name = f'is_{type_code}'
        return getattr(self, attr_name, False) if hasattr(self, attr_name) else False
    
    def get_supported_pet_types_list(self):
        """返回支援的寵物類型列表"""
        if self.supported_pet_types == '未明確說明':
            return ['未明確說明']
            
        pet_types = []
        if self.support_small_dog:
            pet_types.append('小型犬')
        if self.support_medium_dog:
            pet_types.append('中型犬')
        if self.support_large_dog:
            pet_types.append('大型犬')
        if self.support_cat:
            pet_types.append('貓')
        if self.support_bird:
            pet_types.append('鳥類')
        if self.support_rodent:
            pet_types.append('嚙齒類/小動物')
        if self.support_reptile:
            pet_types.append('爬蟲類')
        if self.support_other:
            pet_types.append('其他寵物')
        return pet_types
    
    def is_open_24_hours(self):
        """判斷是否全天營業"""
        if not self.business_hours:
            return False
            
        for day, hours in self.business_hours.items():
            if isinstance(hours, str) and ('24' in hours or '24小時' in hours):
                return True
        return False
    
    def save(self, *args, **kwargs):
        """儲存前的邏輯檢查"""
        # 如果不是醫院類型，確保急診欄位為 False
        if not self.is_hospital:
            self.has_emergency = False
            
        # 如果是「未明確說明」或空白，設置為自動推斷
        if self.supported_pet_types == '未明確說明' or not self.supported_pet_types:
            self.is_pet_type_inferred = True
            
        super().save(*args, **kwargs)