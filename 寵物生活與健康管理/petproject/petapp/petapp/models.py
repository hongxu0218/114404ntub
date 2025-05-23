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
