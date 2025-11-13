from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Pet, DailyRecord, VaccineRecord, DewormRecord, MedicalRecord
from .voice_service import VoiceToDataService
import os
import tempfile
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

# 初始化語音服務
voice_service = VoiceToDataService()


def clean_number(value):
    """清洗數字：去除單位，提取純數字"""
    if value is None:
        return None

    # 如果已經是數字類型，直接返回
    if isinstance(value, (int, float)):
        return value

    # 轉換為字串處理
    value_str = str(value).strip()

    # 移除常見的單位
    units = ['公斤', 'kg', 'KG', '斤', '度', '°C', '℃', 'C', '元', '塊', '分鐘', '分', 'bpm', 'BPM']
    for unit in units:
        value_str = value_str.replace(unit, '')

    # 提取數字（支援小數點）
    match = re.search(r'(\d+\.?\d*)', value_str)
    if match:
        return float(match.group(1))

    return None


def parse_relative_date(date_string):
    """解析相對日期：今天、昨天、前天、X天前、上週X等"""
    if not date_string:
        return date.today()

    date_str = str(date_string).strip()
    today = date.today()

    # 如果已經是 YYYY-MM-DD 格式
    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return today

    # 今天
    if '今天' in date_str or '今日' in date_str:
        return today

    # 昨天
    if '昨天' in date_str or '昨日' in date_str:
        return today - timedelta(days=1)

    # 前天
    if '前天' in date_str:
        return today - timedelta(days=2)

    # X天前
    days_ago_match = re.search(r'(\d+)天前', date_str)
    if days_ago_match:
        days = int(days_ago_match.group(1))
        return today - timedelta(days=days)

    # 上週X（上週一到上週日）
    weekday_map = {
        '一': 0, '二': 1, '三': 2, '四': 3,
        '五': 4, '六': 5, '日': 6, '天': 6
    }
    last_week_match = re.search(r'上週([一二三四五六日天])', date_str)
    if last_week_match:
        target_weekday = weekday_map[last_week_match.group(1)]
        current_weekday = today.weekday()
        # 計算到上週目標星期幾的天數
        days_back = current_weekday + 7 - target_weekday
        if days_back == 7:
            days_back = 7
        return today - timedelta(days=days_back)

    # 預設返回今天
    print(f"[日期解析] 無法解析 '{date_str}'，使用今天")
    return today

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

    temp_path = None  # 初始化暫存檔案路徑

    try:
        # 1. 儲存暫存音訊檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            for chunk in audio_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name

        # 2. 語音轉文字
        transcribed_text = voice_service.transcribe_audio(temp_path)

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

            # 處理並行創建多條記錄的情況
            if isinstance(created_object, list):
                # 返回多條記錄
                categories = [obj.get_category_display() for obj in created_object]
                message = f'✅ 成功新增 {len(created_object)} 筆生活紀錄：' + '、'.join(categories)
                created_ids = [obj.id for obj in created_object]

                return JsonResponse({
                    'success': True,
                    'transcribed_text': transcribed_text,
                    'intent': 'add_daily_record',
                    'created_ids': created_ids,  # 多個 ID
                    'count': len(created_object),
                    'message': message,
                    'redirect_url': '/pets/health/'
                })
            else:
                # 返回單條記錄
                return JsonResponse({
                    'success': True,
                    'transcribed_text': transcribed_text,
                    'intent': 'add_daily_record',
                    'created_id': created_object.id,
                    'message': f'✅ 成功新增生活紀錄：{created_object.get_category_display()}',
                    'redirect_url': '/pets/health/'
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

            # 🔍 檢測就診過程中是否同時進行了驅蟲或疫苗
            additional_records = []
            original_text = transcribed_text.lower()

            # 檢測驅蟲關鍵詞
            deworm_keywords = ['驅蟲', '驱虫', '除蟲', '除虫', '點藥', '点药', '蟲愛', '虫爱']
            if any(keyword in original_text for keyword in deworm_keywords):
                # 嘗試創建驅蟲記錄
                try:
                    # 從原始文本中提取驅蟲藥品牌
                    import re
                    deworm_name = '就診時驅蟲'

                    # 嘗試匹配品牌名稱（優先順序從高到低）
                    brand_patterns = [
                        # Pattern 1: 匹配「驅蟲是XX驅蟲藥」
                        r'(?:驅蟲|驱虫)[是]\s*(.+?)(?:驅蟲藥|驱虫药)',
                        # Pattern 2: 匹配「驅蟲是XX」
                        r'(?:驅蟲|驱虫)[是]\s*(.+?)(?:[，。、\s]|費用|费用|然後|疫苗|$)',
                        # Pattern 3: 匹配「驅蟲品牌是XX」
                        r'(?:驅蟲|驱虫)[的]?品牌[是]?\s*(.+?)(?:[，。、\s]|總共|费用|$)',
                        # Pattern 4: 匹配「驅蟲牌子叫XX」
                        r'(?:驅蟲|驱虫)[的]?牌子[是叫]?\s*(.+?)(?:[，。、\s]|總共|费用|$)',
                        # Pattern 5: 匹配「點了XX」「打了XX驅蟲」
                        r'(?:點|打)[了]?\s*(.+?)(?:驅蟲|驱虫)',
                    ]
                    for pattern in brand_patterns:
                        match = re.search(pattern, transcribed_text)
                        if match:
                            extracted = match.group(1).strip()
                            # 清理噪音詞（按順序清理）
                            extracted = (extracted
                                .replace('藥', '')
                                .replace('药', '')
                                .replace('驅蟲', '')
                                .replace('驱虫', '')
                                .replace('的品牌', '')
                                .replace('品牌', '')
                                .replace('的牌子', '')
                                .replace('牌子', '')
                                .rstrip('的')  # 移除尾部的「的」
                                .strip())
                            # 驗證提取的名稱是否有效
                            if extracted and len(extracted) >= 2 and extracted not in ['順便', '然後', '疫苗跟', '跟']:
                                deworm_name = extracted
                                print(f"[驅蟲提取] Pattern 匹配成功: '{pattern}' → '{deworm_name}'")
                                break

                    deworm_record = create_deworm_from_voice(request.user, {
                        'pet_name': data.get('pet_name'),
                        'deworm_name': deworm_name,
                        'date': data.get('visit_date'),
                        'location': data.get('clinic_location'),
                        'protection_period_months': None
                    })
                    additional_records.append(('驅蟲記錄', deworm_record.name))
                    print(f"[就診附加] 自動創建驅蟲記錄: {deworm_record.name}")
                except Exception as e:
                    print(f"[就診附加] 創建驅蟲記錄失敗: {e}")

            # 檢測疫苗關鍵詞
            vaccine_keywords = ['疫苗', '打針', '預防針', '预防针', '接種', '接种']
            if any(keyword in original_text for keyword in vaccine_keywords):
                # 嘗試創建疫苗記錄
                try:
                    import re
                    vaccine_name = '就診時疫苗'

                    # 嘗試匹配疫苗名稱（優先順序從高到低）
                    vaccine_patterns = [
                        # Pattern 1: 匹配「疫苗是/叫XX疫苗」（最具體）
                        r'疫苗[是叫]\s*(.+?)疫苗',
                        # Pattern 2: 匹配「疫苗是/叫XX」
                        r'疫苗[是叫]\s*(.+?)(?:，|。|\s|費用|然後|$)',
                        # Pattern 3: 匹配「打XX病」（如「打狂犬病」）
                        r'打\s*([^\s，。]+?病)',
                        # Pattern 4: 匹配「打XX疫苗」（但XX不能是空）
                        r'打\s*([^\s，。疫苗]+?)疫苗',
                        # Pattern 5: 匹配「打了XX針」
                        r'打了\s*(.+?)針',
                        # Pattern 6: 匹配「接種XX疫苗」
                        r'接種\s*(.+?)疫苗',
                        # Pattern 7: 匹配「接種XX」
                        r'接種\s*(.+?)(?:，|。|$|\s)',
                    ]
                    for pattern in vaccine_patterns:
                        match = re.search(pattern, transcribed_text)
                        if match:
                            extracted = match.group(1).strip()
                            # 清理噪音詞
                            extracted = (extracted
                                .replace('了', '')
                                .replace('預防針', '')
                                .replace('打針', '')
                                .replace('疫苗', '')
                                .replace('的是', '')
                                .replace('是', '', 1)  # 只移除第一個「是」
                                .strip())
                            # 驗證提取的名稱是否有效
                            if extracted and len(extracted) >= 2 and extracted not in ['預防', '防疫', '打', '順便', '然後', '跟']:
                                vaccine_name = extracted
                                print(f"[疫苗提取] Pattern 匹配成功: '{pattern}' → '{vaccine_name}'")
                                break

                    vaccine_record = create_vaccine_from_voice(request.user, {
                        'pet_name': data.get('pet_name'),
                        'vaccine_name': vaccine_name,
                        'date': data.get('visit_date'),
                        'location': data.get('clinic_location'),
                        'protection_period_months': None
                    })
                    additional_records.append(('疫苗記錄', vaccine_record.name))
                    print(f"[就診附加] 自動創建疫苗記錄: {vaccine_record.name}")
                except Exception as e:
                    print(f"[就診附加] 創建疫苗記錄失敗: {e}")

            # 準備回應訊息
            message = f'✅ 成功新增就診記錄'
            if additional_records:
                additional_msg = '、'.join([f'{name}({record})' for name, record in additional_records])
                message += f' + {additional_msg}'

            return JsonResponse({
                'success': True,
                'transcribed_text': transcribed_text,
                'intent': 'add_medical_record',
                'created_id': created_object.id,
                'additional_records': len(additional_records),
                'message': message,
                'redirect_url': '/pets/health/'
            })

        elif intent == 'edit_pet':
            updated_object = edit_pet_from_voice(request.user, data)
            return JsonResponse({
                'success': True,
                'transcribed_text': transcribed_text,
                'intent': 'edit_pet',
                'updated_id': updated_object.id,
                'message': f'✅ 成功更新寵物資料：{updated_object.name}',
                'redirect_url': '/pets/'
            })

        elif intent == 'edit_daily_record':
            updated_object = edit_daily_record_from_voice(request.user, data)
            return JsonResponse({
                'success': True,
                'transcribed_text': transcribed_text,
                'intent': 'edit_daily_record',
                'updated_id': updated_object.id,
                'message': f'✅ 成功更新生活紀錄',
                'redirect_url': '/pets/health/'
            })

        elif intent == 'edit_medical_record':
            updated_object = edit_medical_record_from_voice(request.user, data)
            return JsonResponse({
                'success': True,
                'transcribed_text': transcribed_text,
                'intent': 'edit_medical_record',
                'updated_id': updated_object.id,
                'message': f'✅ 成功更新就診記錄',
                'redirect_url': '/pets/health/'
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

    finally:
        # 無論成功或失敗，都刪除暫存檔案
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                print(f"[清理] 已刪除暫存檔案: {temp_path}")
            except Exception as cleanup_error:
                print(f"[警告] 無法刪除暫存檔案 {temp_path}: {cleanup_error}")


# ========== 各功能的建立函數 ==========

def get_or_create_pet(user, pet_name):
    """根據寵物名字查找或提示使用者"""
    if not pet_name:
        # 如果沒提供寵物名字，使用使用者最新建立的寵物（更符合直覺）
        pet = Pet.objects.filter(owner=user).order_by('-created_at').first()
        if not pet:
            raise ValueError('找不到寵物，請先新增寵物')
        print(f"[自動選擇] 未指定寵物名稱，使用最新建立的寵物: {pet.name}")
        return pet

    # 嘗試找到同名寵物
    pet = Pet.objects.filter(owner=user, name=pet_name).first()
    if not pet:
        raise ValueError(f'找不到名為「{pet_name}」的寵物，請確認名字是否正確')

    return pet


def create_pet_from_voice(user, data):
    """從語音資料建立寵物"""

    # 除錯：顯示 AI 回傳的原始資料
    print(f"[AI 回傳資料] {data}")

    # 容錯處理：AI 可能返回多種不同的欄位名稱，統一轉換為標準欄位

    # Feature 欄位的多種變體
    feature_variants = ['notes', 'special_feature', 'body_markings', 'markings', 'characteristics']
    for variant in feature_variants:
        if variant in data and 'feature' not in data:
            data['feature'] = data.pop(variant)
            print(f"[自動修正] 將 '{variant}' 欄位轉換為 'feature': {data['feature']}")
            break

    # Birth date 欄位的多種變體
    birth_date_variants = ['date_of_birth', 'birthday', 'born_date']
    for variant in birth_date_variants:
        if variant in data and 'birth_date' not in data:
            data['birth_date'] = data.pop(variant)
            print(f"[自動修正] 將 '{variant}' 欄位轉換為 'birth_date': {data['birth_date']}")
            break

    # Weight 欄位的多種變體
    weight_variants = ['weight_kg', 'weight_in_kg', 'body_weight']
    for variant in weight_variants:
        if variant in data and 'weight' not in data:
            data['weight'] = data.pop(variant)
            print(f"[自動修正] 將 '{variant}' 欄位轉換為 'weight': {data['weight']}")
            break

    # Age 欄位的多種變體（優先處理年份，再處理月份）
    if 'age_years' in data and 'age' not in data:
        data['age'] = data.pop('age_years')
        print(f"[自動修正] 將 'age_years' 欄位轉換為 'age': {data['age']}")
    elif 'age_months' in data and 'age' not in data:
        age_months = data.pop('age_months')
        data['age'] = age_months / 12.0
        print(f"[自動修正] 將 'age_months' ({age_months}月) 轉換為 'age': {data['age']:.1f}年")
    elif 'age_in_months' in data and 'age' not in data:
        age_in_months = data.pop('age_in_months')
        data['age'] = age_in_months / 12.0
        print(f"[自動修正] 將 'age_in_months' ({age_in_months}月) 轉換為 'age': {data['age']:.1f}年")

    # 清理資料：只保留預期的欄位，移除 AI 可能添加的額外欄位
    expected_fields = ['pet_name', 'species', 'breed', 'gender', 'age', 'birth_date', 'weight',
                       'sterilization_status', 'chip', 'feature']
    clean_data = {k: v for k, v in data.items() if k in expected_fields}

    if len(clean_data) < len(data):
        removed_fields = set(data.keys()) - set(clean_data.keys())
        print(f"[警告] 移除了額外欄位: {removed_fields}")

    data = clean_data

    # 智能判斷：如果品種是兔子/天竺鼠/倉鼠等，自動將 species 設為 "other"
    breed = data.get('breed') or '未知品種'
    species = data.get('species') or 'dog'

    # 如果 AI 返回中文的 "其他"，轉換為英文 "other"
    if species in ['其他', '其它']:
        print(f"[智能判斷] 轉換中文 species '其他' → 'other'")
        species = 'other'

    # 其他動物清單
    other_animals = ['兔子', '天竺鼠', '倉鼠', '鳥類', '鳥', '爬蟲類', '爬蟲', '魚類', '魚']

    # 如果品種中包含其他動物關鍵字，強制設為 "other"
    if breed:
        for animal in other_animals:
            if animal in breed:
                species = 'other'
                print(f"[智能判斷] 偵測到 '{breed}' 為非貓狗動物，已自動設定 species='other'")
                break

    # 處理性別：只有在沒有提供時才用預設值
    gender_raw = data.get('gender')

    # 映射性別代碼：AI 返回 M/F，但資料庫需要 male/female/unknown
    gender_map = {
        'M': 'male',
        'F': 'female',
        'male': 'male',
        'female': 'female',
        'unknown': 'unknown'
    }

    if not gender_raw:
        gender = 'male'  # 預設為公
        print(f"[預設值] 性別未提供，使用預設值: male")
    else:
        gender = gender_map.get(gender_raw, 'male')
        print(f"[AI 識別] 性別: {gender_raw} → {gender}")

    # 處理特徵：只有在沒有提供時才用預設值
    feature = data.get('feature')
    if not feature:
        feature = '語音建立'
        print(f"[預設值] 特徵未提供，使用預設值: 語音建立")
    else:
        print(f"[AI 識別] 特徵: {feature}")

    # 轉換絕育狀態：AI 可能返回多種格式，統一轉換
    sterilization_map = {
        'Y': 'sterilized',
        'T': 'sterilized',  # True 的縮寫
        'True': 'sterilized',
        'true': 'sterilized',
        '已結紮': 'sterilized',
        '已绝育': 'sterilized',
        'sterilized': 'sterilized',
        'N': 'not_sterilized',
        'F': 'not_sterilized',  # False 的縮寫
        'False': 'not_sterilized',
        'false': 'not_sterilized',
        '未結紮': 'not_sterilized',
        '未绝育': 'not_sterilized',
        'not_sterilized': 'not_sterilized',
        'U': 'unknown',
        '未知': 'unknown',
        'unknown': 'unknown'
    }
    sterilization_status = data.get('sterilization_status') or 'U'
    sterilization_db_value = sterilization_map.get(sterilization_status, 'unknown')
    print(f"[AI 識別] 絕育狀態: {sterilization_status} → {sterilization_db_value}")

    # 處理出生日期
    birth_date_value = None
    if data.get('birth_date'):
        # 優先使用 AI 直接提供的出生日期
        try:
            from datetime import datetime
            birth_date_str = str(data['birth_date']).strip()
            birth_date_value = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            print(f"[AI 識別] 出生日期: {birth_date_value}")
        except Exception as e:
            print(f"[警告] 出生日期格式錯誤: {data['birth_date']}, 錯誤: {e}")
    elif data.get('age') is not None:
        # 如果沒有提供出生日期但有年齡，從年齡推算出生日期
        try:
            age_years = int(data['age'])
            birth_date_value = date.today() - timedelta(days=age_years * 365)
            print(f"[計算] 從年齡 {age_years} 歲推算出生日期: {birth_date_value}")
        except Exception as e:
            print(f"[警告] 無法從年齡計算出生日期: {e}")

    pet = Pet.objects.create(
        owner=user,
        name=data.get('pet_name') or '未命名',
        species=species,
        breed=breed,
        gender=gender,
        birth_date=birth_date_value,
        weight=clean_number(data.get('weight')),
        sterilization_status=sterilization_db_value,
        chip=data.get('chip') or None,  # 晶片號碼預設 None（語音不適合輸入長串數字）
        feature=feature,
    )

    return pet


def create_daily_record_from_voice(user, data):
    """從語音資料建立生活記錄（支援 AI 返回的 records 陣列格式和自動拆分數值類型）"""
    pet = get_or_create_pet(user, data.get('pet_name'))

    # 容錯處理：AI 有時會錯誤地使用 field_to_update（這是 edit 才用的）
    if 'field_to_update' in data and 'content' not in data:
        print(f"[警告] AI 錯誤地在 add_daily_record 中使用了 field_to_update，正在自動修正...")
        field_to_update = data.get('field_to_update', {})
        if 'content' in field_to_update:
            data['content'] = field_to_update['content']
            print(f"[自動修正] 從 field_to_update 中提取 content: {data['content']}")

    # 🔧 方案1：AI 返回 records 陣列（優先處理）
    if 'records' in data and isinstance(data['records'], list):
        print(f"[AI 拆分] AI 返回了 {len(data['records'])} 條記錄，開始創建...")
        created_records = []

        for idx, record_data in enumerate(data['records'], 1):
            # 清洗數字資料
            temp = clean_number(record_data.get('temperature'))
            weight = clean_number(record_data.get('weight'))
            exercise = clean_number(record_data.get('exercise_duration'))

            record_type = record_data.get('record_type', 'other')
            content = record_data.get('content') or '語音建立的紀錄'

            record = DailyRecord.objects.create(
                pet=pet,
                date=date.today(),
                category=record_type,
                content=content,
                temperature=Decimal(str(temp)) if temp else None,
                weight=Decimal(str(weight)) if weight else None,
                exercise_duration=int(exercise) if exercise else None
            )

            print(f"[✓] 第{idx}條: {record.get_category_display()} - {content}")
            created_records.append(record)

        return created_records  # 返回記錄列表

    # 🔧 方案2：自動檢測並拆分數值類型（向後兼容）
    else:
        # 清洗數字資料
        temp = clean_number(data.get('temperature'))
        weight = clean_number(data.get('weight'))
        exercise = clean_number(data.get('exercise_duration'))

        # 智能拆分：如果同時有多個數據類型，創建多條獨立記錄
        data_types = []
        if temp is not None:
            data_types.append(('temperature', temp))
        if weight is not None:
            data_types.append(('weight', weight))
        if exercise is not None:
            data_types.append(('exercise', exercise))

        created_records = []
        original_content = data.get('content') or '語音建立的紀錄'

        # 如果有多個數據類型，創建多條記錄
        if len(data_types) > 1:
            print(f"[自動拆分] 檢測到 {len(data_types)} 種數據類型，將創建 {len(data_types)} 條獨立記錄")

            for record_type, value in data_types:
                if record_type == 'temperature':
                    record = DailyRecord.objects.create(
                        pet=pet,
                        date=date.today(),
                        category='temperature',
                        content=f"{pet.name}體溫{value}度",
                        temperature=Decimal(str(value)),
                        weight=None,
                        exercise_duration=None
                    )
                    print(f"[✓] 創建體溫記錄: {value}度")
                    created_records.append(record)

                elif record_type == 'weight':
                    record = DailyRecord.objects.create(
                        pet=pet,
                        date=date.today(),
                        category='weight',
                        content=f"{pet.name}體重{value}公斤",
                        temperature=None,
                        weight=Decimal(str(value)),
                        exercise_duration=None
                    )
                    print(f"[✓] 創建體重記錄: {value}公斤")
                    created_records.append(record)

                elif record_type == 'exercise':
                    record = DailyRecord.objects.create(
                        pet=pet,
                        date=date.today(),
                        category='exercise',
                        content=f"{pet.name}運動{value}分鐘",
                        temperature=None,
                        weight=None,
                        exercise_duration=int(value)
                    )
                    print(f"[✓] 創建運動記錄: {value}分鐘")
                    created_records.append(record)

            return created_records  # 返回記錄列表

        # 如果只有一個數據類型或沒有數據類型，創建單條記錄
        else:
            record_type = data.get('record_type', 'other')

            # 智慧判斷：如果有數據但 record_type 是 other，自動修正
            if len(data_types) == 1:
                record_type = data_types[0][0]

            record = DailyRecord.objects.create(
                pet=pet,
                date=date.today(),
                category=record_type,
                content=original_content,
                temperature=Decimal(str(temp)) if temp else None,
                weight=Decimal(str(weight)) if weight else None,
                exercise_duration=int(exercise) if exercise else None
            )

            return record  # 返回單條記錄


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
        location=data.get('location') or '家裡',  # 驅蟲通常在家自己點，預設家裡
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

    # 清洗數字資料
    weight = clean_number(data.get('weight'))
    temperature = clean_number(data.get('temperature'))
    heart_rate = clean_number(data.get('heart_rate'))
    respiratory_rate = clean_number(data.get('respiratory_rate'))
    total_cost = clean_number(data.get('total_cost'))

    medical_record = MedicalRecord.objects.create(
        pet=pet,
        recorded_by=user,
        visit_date=visit_date,
        clinic_location=clinic_location,
        weight=Decimal(str(weight)) if weight else None,
        temperature=Decimal(str(temperature)) if temperature else None,
        heart_rate=int(heart_rate) if heart_rate else None,
        respiratory_rate=int(respiratory_rate) if respiratory_rate else None,
        chief_complaint=data.get('chief_complaint') or '',
        diagnosis=diagnosis,
        treatment=treatment,
        total_cost=Decimal(str(total_cost)) if total_cost else None,
        follow_up_required=data.get('follow_up_required') or False,
        follow_up_date=follow_up_date,
        notes=data.get('notes') or ''
    )

    return medical_record


# ==================== 編輯功能 ====================

def edit_pet_from_voice(user, data):
    """從語音資料編輯寵物"""
    pet_name = data.get('pet_name')

    if not pet_name:
        raise ValueError('缺少寵物名稱')

    # 找到用戶的寵物
    try:
        pet = Pet.objects.get(owner=user, name=pet_name)
    except Pet.DoesNotExist:
        raise ValueError(f'找不到名為 {pet_name} 的寵物')
    except Pet.MultipleObjectsReturned:
        # 如果有多隻同名寵物，使用最新的
        pet = Pet.objects.filter(owner=user, name=pet_name).order_by('-id').first()
        print(f"[警告] 發現多隻同名寵物 '{pet_name}'，已選擇最新的")

    # 更新欄位
    field_to_update = data.get('field_to_update', {})

    # 容錯處理：AI 有時會在 field_to_update 中返回 'notes' 而不是 'feature'
    if 'notes' in field_to_update and 'feature' not in field_to_update:
        field_to_update['feature'] = field_to_update.pop('notes')
        print(f"[自動修正] 將 'notes' 欄位轉換為 'feature': {field_to_update['feature']}")

    if 'weight' in field_to_update:
        pet.weight = clean_number(field_to_update['weight'])
        print(f"[更新] {pet_name} 體重 → {pet.weight}")

    if 'breed' in field_to_update:
        pet.breed = field_to_update['breed']
        print(f"[更新] {pet_name} 品種 → {pet.breed}")

    if 'sterilization_status' in field_to_update:
        # 轉換絕育狀態：AI 可能返回多種格式，統一轉換
        sterilization_map = {
            'Y': 'sterilized',
            'T': 'sterilized',  # True 的縮寫
            'True': 'sterilized',
            'true': 'sterilized',
            '已結紮': 'sterilized',
            '已绝育': 'sterilized',
            'sterilized': 'sterilized',
            'N': 'not_sterilized',
            'F': 'not_sterilized',  # False 的縮寫
            'False': 'not_sterilized',
            'false': 'not_sterilized',
            '未結紮': 'not_sterilized',
            '未绝育': 'not_sterilized',
            'not_sterilized': 'not_sterilized',
            'U': 'unknown',
            '未知': 'unknown',
            'unknown': 'unknown'
        }
        status = field_to_update['sterilization_status']
        pet.sterilization_status = sterilization_map.get(status, 'unknown')
        print(f"[更新] {pet_name} 絕育狀態 → {pet.sterilization_status}")

    if 'gender' in field_to_update:
        # 映射性別代碼：AI 返回 M/F，但資料庫需要 male/female/unknown
        gender_map = {
            'M': 'male',
            'F': 'female',
            'male': 'male',
            'female': 'female',
            'unknown': 'unknown'
        }
        gender_raw = field_to_update['gender']
        pet.gender = gender_map.get(gender_raw, 'male')
        print(f"[更新] {pet_name} 性別: {gender_raw} → {pet.gender}")

    if 'feature' in field_to_update:
        pet.feature = field_to_update['feature']
        print(f"[更新] {pet_name} 特徵 → {pet.feature}")

    if 'name' in field_to_update:
        old_name = pet.name
        new_name = field_to_update['name']
        pet.name = new_name
        print(f"[更新] 寵物改名: {old_name} → {new_name}")

    pet.save()
    return pet


def edit_daily_record_from_voice(user, data):
    """從語音資料編輯生活記錄"""
    pet_name = data.get('pet_name')
    target_date_str = data.get('target_date', '今天')
    record_type = data.get('record_type', None)

    if not pet_name:
        raise ValueError('缺少寵物名稱')

    # 找到寵物
    try:
        pet = Pet.objects.get(owner=user, name=pet_name)
    except Pet.DoesNotExist:
        raise ValueError(f'找不到名為 {pet_name} 的寵物')
    except Pet.MultipleObjectsReturned:
        pet = Pet.objects.filter(owner=user, name=pet_name).order_by('-id').first()

    # 解析日期
    target_date = parse_relative_date(target_date_str)
    print(f"[查詢] {pet_name} 在 {target_date} 的記錄")

    # 查詢記錄
    query = DailyRecord.objects.filter(pet=pet, date=target_date)

    if record_type:
        query = query.filter(category=record_type)

    records = list(query.order_by('-id'))

    if not records:
        raise ValueError(f'找不到 {pet_name} 在 {target_date_str} ({target_date}) 的記錄')

    if len(records) > 1:
        print(f"[警告] 發現 {len(records)} 筆記錄，選擇最新的")

    record = records[0]

    # 更新欄位
    field_to_update = data.get('field_to_update', {})

    if 'temperature' in field_to_update:
        temp = clean_number(field_to_update['temperature'])
        record.temperature = Decimal(str(temp)) if temp else None
        print(f"[更新] 體溫 → {record.temperature}")

    if 'weight' in field_to_update:
        weight = clean_number(field_to_update['weight'])
        record.weight = Decimal(str(weight)) if weight else None
        print(f"[更新] 體重 → {record.weight}")

    if 'content' in field_to_update:
        record.content = field_to_update['content']
        print(f"[更新] 內容 → {record.content}")

    if 'exercise_duration' in field_to_update:
        exercise = clean_number(field_to_update['exercise_duration'])
        record.exercise_duration = int(exercise) if exercise else None
        print(f"[更新] 運動時長 → {record.exercise_duration}")

    record.save()
    return record


def edit_medical_record_from_voice(user, data):
    """從語音資料編輯就診記錄"""
    pet_name = data.get('pet_name')
    target_date_str = data.get('target_date', '今天')

    if not pet_name:
        raise ValueError('缺少寵物名稱')

    # 找到寵物
    try:
        pet = Pet.objects.get(owner=user, name=pet_name)
    except Pet.DoesNotExist:
        raise ValueError(f'找不到名為 {pet_name} 的寵物')
    except Pet.MultipleObjectsReturned:
        pet = Pet.objects.filter(owner=user, name=pet_name).order_by('-id').first()

    # 解析日期
    target_date = parse_relative_date(target_date_str)
    print(f"[查詢] {pet_name} 在 {target_date} 的就診記錄")

    # 查詢記錄
    records = list(MedicalRecord.objects.filter(
        pet=pet,
        visit_date=target_date
    ).order_by('-id'))

    if not records:
        raise ValueError(f'找不到 {pet_name} 在 {target_date_str} ({target_date}) 的就診記錄')

    if len(records) > 1:
        print(f"[警告] 發現 {len(records)} 筆記錄，選擇最新的")

    record = records[0]

    # 更新欄位
    field_to_update = data.get('field_to_update', {})

    if 'diagnosis' in field_to_update:
        record.diagnosis = field_to_update['diagnosis']
        print(f"[更新] 診斷 → {record.diagnosis}")

    if 'treatment' in field_to_update:
        record.treatment = field_to_update['treatment']
        print(f"[更新] 治療 → {record.treatment}")

    if 'total_cost' in field_to_update:
        cost = clean_number(field_to_update['total_cost'])
        record.total_cost = Decimal(str(cost)) if cost else None
        print(f"[更新] 費用 → {record.total_cost}")

    if 'weight' in field_to_update:
        weight = clean_number(field_to_update['weight'])
        record.weight = Decimal(str(weight)) if weight else None
        print(f"[更新] 體重 → {record.weight}")

    if 'temperature' in field_to_update:
        temp = clean_number(field_to_update['temperature'])
        record.temperature = Decimal(str(temp)) if temp else None
        print(f"[更新] 體溫 → {record.temperature}")

    record.save()
    return record
