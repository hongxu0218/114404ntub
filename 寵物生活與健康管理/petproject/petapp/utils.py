
from datetime import date
from calendar import monthrange
from django.utils.timezone import localtime
from .models import DailyRecord
from .choices import DOG_CHOICES, CAT_CHOICES, DOGVACCINE_CHOICES, CATVACCINE_CHOICES
import json

# （體溫）共用程式
def get_temperature_data(pet, year, month):
    """
    根據寵物與月份，取得該月所有有效體溫紀錄，並整理成趨勢圖可用格式。
    """
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='temperature',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

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
    return records

# （體重）共用程式
def get_weight_data(pet, year, month):
    """
    根據寵物與月份，取得該月所有有效體溫紀錄，並整理成趨勢圖可用格式。
    """
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='weight',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    records = []
    for rec in raw_records:
        try:
            weight_value = float(rec.content)
        except ValueError:
            continue
        records.append({
            'id': rec.id,
            'date': rec.date.strftime('%Y-%m-%d'),
            'datetime': rec.date.strftime('%Y-%m-%d'),
            'recorded_date': rec.date.strftime('%Y-%m-%d'),
            'submitted_at': localtime(rec.created_at).strftime('%H:%M'),
            'weight': weight_value,
            'raw_content': rec.content,
        })
    return records

# （品種/疫苗）切換表單的共用程式
def get_species_choices(species_json):
    try:
        species_data = json.loads(species_json)
        species_choice = species_data.get('species_choice', '')
    except Exception:
        species_choice = ''

    if species_choice == '狗':
        return DOG_CHOICES, DOGVACCINE_CHOICES
    elif species_choice == '貓':
        return CAT_CHOICES, CATVACCINE_CHOICES
    elif species_choice == '其他':
        breed_other = species_data.get('breed_other', '其他')
        vaccine_other = species_data.get('vaccine_other', '其他')
        return [(breed_other, breed_other)], [(vaccine_other, vaccine_other)]
    return [('', '請先選擇'), ('其他', '其他')], [('', '請先選擇'), ('其他', '其他')]
