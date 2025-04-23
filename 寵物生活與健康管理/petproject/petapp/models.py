# petapp/models.py
from django.db import models

from django.contrib.auth.models import User

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

    def __str__(self):
        return f"{self.user.username} ({self.get_account_type_display()})"