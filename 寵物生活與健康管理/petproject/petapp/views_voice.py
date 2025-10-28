from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Pet, DailyRecord, VaccineRecord, DewormRecord, MedicalRecord
from .voice_service import VoiceToDataService
import os
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal

# 初始化語音服務
voice_service = VoiceToDataService()

@login_required
def voice_input_page(request):
    """語音輸入頁面"""
    return render(request, 'voice/voice_input.html')

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def voice_create_handler(request):
    """處理語音建立請求的核心 API"""

    audio_file = request.FILES.get('audio')

    if not audio_file:
        return JsonResponse({'error': '未收到音訊檔案'}, status=400)

    try:
        # 1. 儲存暫存音訊檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            for chunk in audio_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name

        # 2. 語音轉文字
        transcribed_text = voice_service.transcribe_audio(temp_path)

        # 刪除暫存檔案
        os.unlink(temp_path)

        if not transcribed_text:
            return JsonResponse({
                'success': False,
                'error': '語音轉文字失敗，請重新錄音'
            }, status=400)

        # 3. AI 意圖識別與欄位抽取
        result = voice_service.extract_intent_and_fields(transcribed_text)

        intent = result.get('intent')
        confidence = result.get('confidence', 0)
        data = result.get('data', {})

        # 4. 信心度檢查
        if confidence < 0.7:
            return JsonResponse({
                'success': False,
                'need_confirmation': True,
                'transcribed_text': transcribed_text,
                'intent': intent,
                'parsed_data': data,
                'confidence': confidence,
                'message': f'系統理解信心度較低 ({confidence:.0%})，請確認是否正確'
            })

        # 5. 根據意圖建立資料
        if intent == 'add_pet':
            created_object = create_pet_from_voice(request.user, data)
            return JsonResponse({
                'success': True,
                'transcribed_text': transcribed_text,
                'intent': 'add_pet',
                'created_id': created_object.id,
                'message': f'✅ 成功新增寵物：{created_object.name}',
                'redirect_url': '/pets/'  # 修正：寵物列表頁面
            })

        elif intent == 'add_daily_record':
            created_object = create_daily_record_from_voice(request.user, data)
            return JsonResponse({
                'success': True,
                'transcribed_text': transcribed_text,
                'intent': 'add_daily_record',
                'created_id': created_object.id,
                'message': f'✅ 成功新增生活紀錄：{created_object.get_category_display()}',
                'redirect_url': '/pets/health/'  # 修正：健康記錄頁面
            })

        elif intent == 'add_vaccine':
            created_object = create_vaccine_from_voice(request.user, data)
            return JsonResponse({
                'success': True,
                'transcribed_text': transcribed_text,
                'intent': 'add_vaccine',
                'created_id': created_object.id,
                'message': f'✅ 成功新增疫苗記錄：{created_object.name}',
                'redirect_url': '/pets/health/'  # 修正：健康記錄頁面（疫苗記錄會顯示在這裡）
            })

        elif intent == 'add_deworm':
            created_object = create_deworm_from_voice(request.user, data)
            return JsonResponse({
                'success': True,
                'transcribed_text': transcribed_text,
                'intent': 'add_deworm',
                'created_id': created_object.id,
                'message': f'✅ 成功新增驅蟲記錄：{created_object.name}',
                'redirect_url': '/pets/health/'  # 修正：健康記錄頁面（驅蟲記錄會顯示在這裡）
            })

        elif intent == 'add_medical_record':
            created_object = create_medical_record_from_voice(request.user, data)
            return JsonResponse({
                'success': True,
                'transcribed_text': transcribed_text,
                'intent': 'add_medical_record',
                'created_id': created_object.id,
                'message': f'✅ 成功新增就診記錄',
                'redirect_url': '/pets/health/'  # 修正：健康記錄頁面（就診記錄會顯示在這裡）
            })

        else:
            return JsonResponse({
                'success': False,
                'transcribed_text': transcribed_text,
                'message': '❓ 無法識別您的意圖，請重新描述'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f'❌ 處理失敗：{str(e)}'
        }, status=500)


# ========== 各功能的建立函數 ==========

def get_or_create_pet(user, pet_name):
    """根據寵物名字查找或提示使用者"""
    if not pet_name:
        # 如果沒提供寵物名字，使用使用者的第一隻寵物
        pet = Pet.objects.filter(owner=user).first()
        if not pet:
            raise ValueError('找不到寵物，請先新增寵物')
        return pet

    # 嘗試找到同名寵物
    pet = Pet.objects.filter(owner=user, name=pet_name).first()
    if not pet:
        raise ValueError(f'找不到名為「{pet_name}」的寵物，請確認名字是否正確')

    return pet


def create_pet_from_voice(user, data):
    """從語音資料建立寵物"""
    pet = Pet.objects.create(
        owner=user,
        name=data.get('pet_name') or '未命名',
        species=data.get('species') or 'dog',
        breed=data.get('breed') or '未知品種',
        gender=data.get('gender') or 'M',
        weight=data.get('weight'),
        sterilization_status=data.get('sterilization_status') or 'U',
        chip=data.get('chip') or '',
        feature=data.get('feature') or '語音建立',
    )

    # 如果有年齡，計算出生日期
    if data.get('age'):
        age_years = int(data['age'])
        pet.birth_date = date.today() - timedelta(days=age_years * 365)
        pet.save()

    return pet


def create_daily_record_from_voice(user, data):
    """從語音資料建立生活記錄"""
    pet = get_or_create_pet(user, data.get('pet_name'))

    # 判斷記錄類型（如果沒指定，根據內容智慧判斷）
    record_type = data.get('record_type', 'other')

    # 智慧判斷：如果有體溫就是體溫監測
    if data.get('temperature') and record_type == 'other':
        record_type = 'temperature'
    elif data.get('weight') and record_type == 'other':
        record_type = 'weight'
    elif data.get('exercise_duration') and record_type == 'other':
        record_type = 'exercise'

    record = DailyRecord.objects.create(
        pet=pet,
        date=date.today(),
        category=record_type,
        content=data.get('content') or '語音建立的紀錄',
        temperature=Decimal(str(data['temperature'])) if data.get('temperature') else None,
        weight=Decimal(str(data['weight'])) if data.get('weight') else None,
        exercise_duration=data.get('exercise_duration')
    )

    return record


def create_vaccine_from_voice(user, data):
    """從語音資料建立疫苗記錄"""
    pet = get_or_create_pet(user, data.get('pet_name'))

    # 處理日期
    vaccine_date = data.get('date')
    if isinstance(vaccine_date, str):
        vaccine_date = datetime.strptime(vaccine_date, '%Y-%m-%d').date()
    elif not vaccine_date:
        vaccine_date = date.today()

    vaccine = VaccineRecord.objects.create(
        pet=pet,
        name=data.get('vaccine_name') or '語音記錄疫苗',
        date=vaccine_date,
        location=data.get('location') or '語音記錄',
        protection_period_months=data.get('protection_period_months')
    )

    return vaccine


def create_deworm_from_voice(user, data):
    """從語音資料建立驅蟲記錄"""
    pet = get_or_create_pet(user, data.get('pet_name'))

    # 處理日期
    deworm_date = data.get('date')
    if isinstance(deworm_date, str):
        deworm_date = datetime.strptime(deworm_date, '%Y-%m-%d').date()
    elif not deworm_date:
        deworm_date = date.today()

    deworm = DewormRecord.objects.create(
        pet=pet,
        name=data.get('deworm_name') or '語音記錄驅蟲',
        date=deworm_date,
        location=data.get('location') or '語音記錄',
        protection_period_months=data.get('protection_period_months')
    )

    return deworm


def create_medical_record_from_voice(user, data):
    """從語音資料建立就診記錄"""
    pet = get_or_create_pet(user, data.get('pet_name'))

    # 處理日期
    visit_date = data.get('visit_date')
    if isinstance(visit_date, str):
        visit_date = datetime.strptime(visit_date, '%Y-%m-%d').date()
    elif not visit_date:
        visit_date = date.today()

    # 處理追蹤日期
    follow_up_date = data.get('follow_up_date')
    if isinstance(follow_up_date, str):
        follow_up_date = datetime.strptime(follow_up_date, '%Y-%m-%d').date()

    # 處理必填欄位
    clinic_location = data.get('clinic_location')
    if not clinic_location:
        clinic_location = '語音記錄（未指定診所）'

    diagnosis = data.get('diagnosis')
    if not diagnosis:
        diagnosis = '語音記錄（待補充診斷）'

    treatment = data.get('treatment')
    if not treatment:
        treatment = '語音記錄（待補充治療內容）'

    medical_record = MedicalRecord.objects.create(
        pet=pet,
        recorded_by=user,
        visit_date=visit_date,
        clinic_location=clinic_location,
        weight=Decimal(str(data['weight'])) if data.get('weight') else None,
        temperature=Decimal(str(data['temperature'])) if data.get('temperature') else None,
        heart_rate=data.get('heart_rate'),
        respiratory_rate=data.get('respiratory_rate'),
        chief_complaint=data.get('chief_complaint') or '',
        diagnosis=diagnosis,
        treatment=treatment,
        total_cost=Decimal(str(data['total_cost'])) if data.get('total_cost') else None,
        follow_up_required=data.get('follow_up_required') or False,
        follow_up_date=follow_up_date,
        notes=data.get('notes') or ''
    )

    return medical_record
