from faster_whisper import WhisperModel
import ollama
import json
from datetime import datetime, date

class VoiceToDataService:
    """語音轉資料自動化服務"""

    def __init__(self):
        # 初始化 Whisper 模型（medium 模型提供更好的中文識別準確度）
        # 第一次使用會自動下載模型（約 1.5GB）
        self.whisper_model = WhisperModel("medium", device="cpu", compute_type="int8")

    def transcribe_audio(self, audio_file_path):
        """步驟1: 將語音轉為文字"""
        try:
            print(f"[Whisper] 開始轉錄音檔: {audio_file_path}")
            segments, info = self.whisper_model.transcribe(
                audio_file_path,
                language='zh',          # 明確指定中文，提高準確度
                beam_size=5,            # 提高準確度
                best_of=5,              # 從5個候選中選最佳結果
                vad_filter=True,        # 開啟語音活動檢測（過濾靜音）
                vad_parameters=dict(    # VAD 參數
                    min_silence_duration_ms=500  # 最小靜音持續時間
                )
            )

            # 顯示檢測到的語言
            detected_language = info.language
            language_probability = info.language_probability
            print(f"[Whisper] 檢測語言: {detected_language} (信心度: {language_probability:.2%})")

            text = " ".join([segment.text for segment in segments])
            print(f"[Whisper] 轉錄成功: {text}")
            return text.strip()
        except Exception as e:
            print(f"[Whisper ERROR] 語音轉文字錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
            return ""

    def extract_intent_and_fields(self, text):
        """步驟2: 使用 Ollama 分析意圖並抽取欄位"""

        # 檢查輸入文字是否為空
        if not text or text.strip() == "":
            print("[Ollama ERROR] 輸入文字為空")
            return {
                "intent": "unknown",
                "confidence": 0,
                "data": {},
                "error": "語音轉文字失敗，未收到有效文字"
            }

        print(f"[Ollama] 收到文字輸入（長度: {len(text)}）: {text}")

        # 獲取今天的日期用於提示
        today = date.today().strftime('%Y-%m-%d')

        prompt = f"""分析：「{text}」(今天:{today})

⚠️只能返回以下意圖之一（不能自創意圖）：
add_pet, edit_pet, delete_pet, query_pet,
add_daily_record, edit_daily_record, delete_daily_record,
add_vaccine, edit_vaccine, delete_vaccine,
add_deworm, edit_deworm, delete_deworm,
add_medical_record, edit_medical_record, delete_medical_record

意圖判斷規則（優先順序）：
1.提到「疫苗/打針/預防針」→add_vaccine/edit_vaccine
2.提到「驅蟲/驅蟲藥/點藥/除蟲」→add_deworm/edit_deworm
3.提到「看診/就診/看醫生/去醫院」→add_medical_record/edit_medical_record
4.提到完整寵物資料（名字+品種+出生日期等）→add_pet
5.有「編輯/修改/改名/更名」+「寵物/檔案/資料」→edit_pet
6.有「今天/昨天」+狀況描述→add_daily_record

⚠️重要：
- 即使用過去式「我建立了」，只要包含完整寵物資料→仍是add_pet！
- 用戶說「檔案」通常指「寵物檔案」或「寵物資料」，不是電腦文件
- 「改名字/更名/修改名字」→edit_pet（修改寵物名稱）

寵物名稱提取規則：
⚠️優先檢查：「幫/為/給+名字」格式
  "幫哈奇寫"→pet_name:"哈奇" ✅
  "為Coco記錄"→pet_name:"Coco" ✅
⚠️次要檢查：「名字+的」格式
  "哈奇點的驅蟲藥"→pet_name:"哈奇" ✅
  "Mickey吃的藥"→pet_name:"Mickey" ✅
⚠️第三檢查：名字+動詞
  "哈奇點了驅蟲藥"→pet_name:"哈奇" ✅
⚠️名字特徵：2-4個字的詞，可以是中文、英文或混合
⚠️找不到名字→pet_name:null（系統用最新建立的寵物）

藥名/疫苗名提取規則：
⚠️優先提取「牌子叫/品牌是/叫做/名字是+XXX」中的XXX
  "牌子叫益百分"→deworm_name/vaccine_name:"益百分" ✅
  "品牌是蟲愛滴劑"→deworm_name:"蟲愛滴劑" ✅
⚠️如果沒有明確品牌，提取第一個相關詞作為名稱

數值提取規則（⚠️極其重要：必須提取所有數值！）：
temperature:只要提到「體溫/發燒/溫度+數字」→必須創建temperature記錄（如"體溫38度"→{{"record_type":"temperature","temperature":38}}）
weight:只要提到「體重/重量/公斤+數字」→必須創建weight記錄（如"體重4.3公斤"→{{"record_type":"weight","weight":4.3}}）
exercise:只要提到「運動/散步/走路+數字分鐘」→必須創建exercise記錄（如"散步15分鐘"→{{"record_type":"exercise","exercise_duration":15}}）

⚠️即使同時有很多行為觀察，也要記得提取數值到獨立記錄中！
例如：提到6種行為+體重+體溫+運動 → 必須返回9條記錄，不能只返回6條！

⚠️關鍵規則：提取所有提到的資料！
如果用戶同時說了多種資料，必須全部提取，一個都不能漏！

⚠️如果同時提到多種行為/症狀（如"很躁動而且過敏了"）：
使用records陣列格式，每種行為/症狀一條記錄：
{{"records":[
  {{"record_type":"mood","content":"很躁動"}},
  {{"record_type":"allergen","content":"過敏了"}}
]}}

⚠️如果同時提到多種數值（如"35公斤並且38度"）：
同樣使用records陣列，每種數值一條記錄：
{{"records":[
  {{"record_type":"weight","content":"體重35公斤","weight":35}},
  {{"record_type":"temperature","content":"體溫38度","temperature":38}}
]}}

⚠️如果同時有行為+數值（如"很躁動、過敏、體重4.5公斤、體溫39度"）：
必須提取所有4種資料到records陣列中！不能只提取其中2種！

⚠️records陣列沒有數量限制：
- 用戶提到2種→返回2條記錄
- 用戶提到4種→返回4條記錄
- 用戶提到8種（全部類型）→返回8條記錄
最多可以包含所有8種記錄類型：mood, diet, allergen, medication, other, temperature, weight, exercise

⚠️如果只有一種記錄，直接返回單個data物件（不用records陣列）

品種提取規則：
⚠️關鍵：如果用戶說「新增+品種」或「品種+寵物」，品種就是那個詞
  "新增貴賓犬"→breed:"貴賓犬" ✅
  "他是柴犬"→breed:"柴犬" ✅
  "品種是英國短毛貓"→breed:"英國短毛貓" ✅
⚠️品種必須用中文（如"英國短毛貓"不是"British Shorthair"）

性別/絕育/特徵規則：
gender:M=公/male, F=母/female
sterilization_status:Y=已結紮, N=未結紮, U=未知
feature:提取外觀特徵（如"肚子上有胎記"→feature:"肚子上有胎記"）

add_pet必須返回的欄位：
{{"pet_name":"名字","breed":"品種","gender":"M/F","age":年齡數字,"weight":體重數字,"feature":"外觀特徵","sterilization_status":"Y/N/U"}}

add_medical_record必須返回的欄位：
{{"pet_name":"名字","visit_date":"就診日期","clinic_location":"診所/醫院名稱","diagnosis":"診斷/症狀","treatment":"治療/藥物","total_cost":費用數字}}

就診記錄提取規則：
clinic_location:提取「去XX醫院/XX診所/在XX看病」中的醫院/診所名稱
diagnosis:提取「症狀是XX/診斷為XX/得了XX」中的疾病/症狀
treatment:提取「開了XX藥/治療XX/吃XX」中的藥物/治療內容
total_cost:提取「費用XX元/花了XX塊/XX元」中的數字

record_type(優先順序)：
mood:過動/躁動/心情/焦慮/興奮/沒精神
diet:食慾/挑食/不吃飯
allergen:過敏
medication:吃藥/維他命
other:拉肚子/亂大便
temperature:體溫/發燒（⚠️必須提取數值到temperature欄位）
weight:體重（⚠️必須提取數值到weight欄位）
exercise:散步/運動（⚠️必須提取分鐘數到exercise_duration欄位）

⚠️檢查清單：分析完輸入後，檢查是否遺漏任何資料
- 提到體溫/溫度+數字？ → 必須有temperature記錄
- 提到體重/公斤+數字？ → 必須有weight記錄
- 提到散步/運動+分鐘？ → 必須有exercise記錄

範例格式（⚠️必須根據實際輸入提取資料，不要複製範例內容！）：
"新增貴賓犬叫檸檬他是公的兩歲體重3公斤已結紮肚子有胎記"→{{"intent":"add_pet","confidence":0.95,"data":{{"pet_name":"檸檬","breed":"貴賓犬","gender":"M","age":2,"weight":3,"feature":"肚子有胎記","sterilization_status":"Y"}}}}
"把未知的名字改成檸檬"→{{"intent":"edit_pet","confidence":0.95,"data":{{"pet_name":"未知","field_to_update":{{"name":"檸檬"}}}}}}
"檸檬今天去愛生醫院看病症狀是腸胃炎開了消炎藥費用900塊"→{{"intent":"add_medical_record","confidence":0.95,"data":{{"pet_name":"檸檬","visit_date":"{today}","clinic_location":"愛生醫院","diagnosis":"腸胃炎","treatment":"消炎藥","total_cost":900,"follow_up_date":null,"weight":null,"temperature":null}}}}
"檸檬很焦慮挑食對魚過敏吃維他命B拉肚子體重4.3公斤體溫38度散步15分鐘"→{{"intent":"add_daily_record","confidence":0.95,"data":{{"pet_name":"檸檬","target_date":"{today}","records":[{{"record_type":"mood","content":"很焦慮"}},{{"record_type":"diet","content":"挑食"}},{{"record_type":"allergen","content":"對魚過敏"}},{{"record_type":"medication","content":"吃維他命B"}},{{"record_type":"other","content":"拉肚子"}},{{"record_type":"weight","content":"體重4.3公斤","weight":4.3}},{{"record_type":"temperature","content":"體溫38度","temperature":38}},{{"record_type":"exercise","content":"散步15分鐘","exercise_duration":15}}]}}}}
"今天哈奇點的驅蟲藥牌子叫藝百分"→{{"intent":"add_deworm","confidence":0.95,"data":{{"pet_name":"哈奇","deworm_name":"藝百分","date":"{today}","location":null,"protection_period_months":null}}}}
"毛毛今天很躁動"→{{"intent":"add_daily_record","confidence":0.95,"data":{{"pet_name":"毛毛","target_date":"{today}","record_type":"mood","content":"毛毛今天很躁動","temperature":null,"weight":null,"exercise_duration":null}}}}

⚠️關鍵：必須分析「{text}」的實際內容！不要返回範例中的資料！
回傳JSON（必須包含intent,confidence,data）："""

        try:
            print(f"[Ollama] 開始分析文字: {text[:100]}...")
            response = ollama.chat(
                model='qwen2.5:3b-instruct',  # 使用 3b 模型（更好的理解能力）
                messages=[{'role': 'user', 'content': prompt}],
                format='json'  # 要求回傳 JSON 格式
            )

            # 解析 JSON
            content = response['message']['content']
            print(f"[Ollama] AI 回應: {content[:200]}...")

            result = json.loads(content)
            print(f"[Ollama] 解析成功 - 意圖: {result.get('intent')}, 信心度: {result.get('confidence')}")

            # 🔧 後處理：自動糾正錯誤的意圖判斷
            result = self._post_process_intent(text, result)

            # 🛡️ 安全網：補充 AI 遺漏的數值記錄
            if result.get('intent') == 'add_daily_record' and 'records' in result.get('data', {}):
                result = self._fill_missing_numeric_records(text, result)

            return result

        except json.JSONDecodeError as e:
            print(f"[Ollama ERROR] JSON 解析失敗: {str(e)}")
            print(f"[Ollama ERROR] 原始內容: {content}")

            # 如果直接解析失敗，嘗試提取 JSON
            try:
                start = content.find('{')
                end = content.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = content[start:end]
                    result = json.loads(json_str)
                    print(f"[Ollama] 成功從文字中提取 JSON")
                    return result
            except Exception as e2:
                print(f"[Ollama ERROR] 提取 JSON 也失敗: {str(e2)}")

            return {
                "intent": "unknown",
                "confidence": 0,
                "data": {},
                "error": f"AI 回應格式錯誤: {str(e)}"
            }

        except Exception as e:
            print(f"[Ollama ERROR] Ollama 處理錯誤: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "intent": "unknown",
                "confidence": 0,
                "data": {},
                "error": str(e)
            }

    def _post_process_intent(self, text, result):
        """
        後處理：自動糾正 AI 的錯誤判斷

        規則1：如果輸入文字中沒有編輯關鍵詞，但 AI 判斷為 edit 系列，則自動修正為 add 系列
        規則2：如果輸入包含生活記錄關鍵詞，但 AI 判斷為 add_pet/edit_pet，則修正為 add_daily_record
        規則3：如果沒有「新增」「建立」等關鍵詞，但 AI 判斷為 add_pet，則檢查是否為生活記錄
        """
        intent = result.get('intent')

        # 定義編輯關鍵詞
        edit_keywords = ['編輯', '修改', '更新', '更改', '改成', '變更', '調整']

        # 定義新增寵物關鍵詞
        add_pet_keywords = ['新增', '建立', '創建', '增加', '登記', '註冊', '幫我加', '幫我新增']

        # 定義生活記錄關鍵詞（按分類）
        # ⚠️ 重要：順序很重要！mood 必須優先檢查，避免被誤判為 other
        daily_record_keywords = {
            # 優先級1：行為觀察（必須優先檢查）
            'mood': ['過動', '过动', '好動', '好动', '活潑', '活泼', '躁動', '躁动', '興奮', '兴奋', '暴躁',
                     '心情', '情緒', '情绪', '開心', '开心', '難過', '难过', '焦慮', '焦虑', '緊張', '紧张', '黏人', '沮喪', '沮丧',
                     '不理人', '躲起來', '躲起来', '安靜', '安静', '懶洋洋', '懒洋洋',
                     '沒精神', '没精神', '有精神', '嗜睡', '精神很好', '精神不好',
                     '一直叫', '亂叫', '亂咬', '咬東西', '破壞', '破坏'],
            # 優先級2：飲食相關
            'diet': ['食慾', '食欲', '胃口', '食量', '不吃飯', '不吃饭', '挑食', '拒食', '吃很多', '吃得少'],
            # 優先級3：過敏相關
            'allergen': ['過敏', '过敏', '起疹子', '搔癢', '搔痒', '紅腫', '红肿', '過敏原', '过敏原'],
            # 優先級4：用藥相關
            'medication': ['吃藥', '吃药', '服藥', '服药', '維他命', '维他命', '保健品'],
            # 優先級5：數據監測
            'temperature': ['體溫', '体温', '發燒', '发烧', '燒到', '烧到'],
            'weight': ['體重', '体重', '變重', '变重', '變輕', '变轻', '胖了', '瘦了'],
            'exercise': ['散步', '運動', '运动', '跑步', '走路', '玩耍'],
            # 優先級6：其他（最後兜底）
            'other': ['拉肚子', '亂大便', '乱大便', '便便', '尿尿', '便秘', '軟便', '软便', '血便']
        }

        # 定義時間關鍵詞（強制判斷為生活記錄）
        time_keywords = ['今天', '昨天', '前天', '最近', '這幾天', '這陣子', '今日', '昨日', '上週', '這週']

        # 檢查文字中是否包含編輯關鍵詞
        has_edit_keyword = any(keyword in text for keyword in edit_keywords)

        # 檢查是否包含時間關鍵詞
        has_time_keyword = any(keyword in text for keyword in time_keywords)

        # 檢查是否包含生活記錄關鍵詞（按優先級順序檢查）
        detected_record_type = None
        for record_type, keywords in daily_record_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected_record_type = record_type
                break  # 找到第一個匹配就停止（優先級高的會先被檢查到）

        # 規則2：如果包含生活記錄關鍵詞，但判斷為 add_pet 或 edit_pet
        if detected_record_type and intent in ['add_pet', 'edit_pet']:
            # ⚠️ 智能判斷：檢查是否真的是「新增寵物」
            has_add_pet_keyword = any(keyword in text for keyword in add_pet_keywords)

            # 檢查是否有完整的寵物資料（名字、品種、性別、年齡等，至少2項）
            pet_data = result.get('data', {})
            complete_pet_fields = sum([
                bool(pet_data.get('pet_name')),           # 有名字
                bool(pet_data.get('breed')),              # 有品種
                bool(pet_data.get('species')),            # 有物種
                bool(pet_data.get('gender')),             # 有性別
                bool(pet_data.get('birth_date')) or bool(pet_data.get('age_years')) or bool(pet_data.get('age_months')),  # 有年齡
                bool(pet_data.get('sterilization_status'))  # 有絕育狀態
            ])
            has_complete_pet_info = complete_pet_fields >= 2

            # 🔧 關鍵邏輯：如果有「新增寵物」關鍵詞 + 完整寵物資料 → 保持 add_pet
            if has_add_pet_keyword and has_complete_pet_info:
                print(f"[後處理] ✅ 保持 {intent}：檢測到「新增寵物」關鍵詞 + 完整寵物資料（{complete_pet_fields} 項）")
                print(f"[後處理] 提示：體重將存入寵物檔案，體溫等數據建議稍後單獨記錄")
                print(f"[後處理] 原始文字: {text}")
                # 不修改，保持 add_pet

            else:
                # 🔧 否則：改為生活記錄
                old_intent = intent
                result['intent'] = 'add_daily_record'

                # 修正 data 結構
                if 'field_to_update' in result.get('data', {}):
                    field_to_update = result['data'].pop('field_to_update')
                    # 將 field_to_update 中的內容提取為 content
                    if 'feature' in field_to_update:
                        result['data']['content'] = field_to_update['feature']
                    else:
                        result['data']['content'] = text
                elif 'content' not in result.get('data', {}):
                    result['data']['content'] = text

                # 設定正確的 record_type
                result['data']['record_type'] = detected_record_type

                # 確保數值欄位為 null
                result['data']['temperature'] = None
                result['data']['weight'] = None
                result['data']['exercise_duration'] = None

                print(f"[後處理] 🔧 自動修正意圖: {old_intent} → {result['intent']}")
                print(f"[後處理] 原因: 檢測到生活記錄關鍵詞（{detected_record_type}），但沒有完整寵物資料")
                print(f"[後處理] 原始文字: {text}")

        # 規則1：如果判斷為 edit 系列，但沒有編輯關鍵詞
        elif intent in ['edit_pet', 'edit_daily_record', 'edit_medical_record'] and not has_edit_keyword:
            old_intent = intent

            # 自動修正為 add 系列
            if intent == 'edit_daily_record':
                result['intent'] = 'add_daily_record'

                # 修正 data 結構：從 field_to_update 轉為直接欄位
                if 'field_to_update' in result.get('data', {}):
                    field_to_update = result['data'].pop('field_to_update')
                    # 將 field_to_update 中的內容移到 data 的頂層
                    for key, value in field_to_update.items():
                        if key not in result['data']:
                            result['data'][key] = value
                    print(f"[後處理] 已將 field_to_update 內容提升到 data 頂層")

                # 確保有 content 欄位
                if 'content' not in result['data'] or not result['data']['content']:
                    result['data']['content'] = text
                    print(f"[後處理] 自動填入 content: {text}")

                # 如果能檢測到 record_type，設定它
                if detected_record_type:
                    result['data']['record_type'] = detected_record_type
                    print(f"[後處理] 設定 record_type: {detected_record_type}")

            elif intent == 'edit_pet':
                result['intent'] = 'add_pet'
                # edit_pet 轉 add_pet 可能需要更多欄位，暫時不處理

            elif intent == 'edit_medical_record':
                result['intent'] = 'add_medical_record'
                # 同上

            print(f"[後處理] 🔧 自動修正意圖: {old_intent} → {result['intent']}")
            print(f"[後處理] 原因: 文字中沒有編輯關鍵詞（{edit_keywords}）")
            print(f"[後處理] 原始文字: {text}")

        # 規則3：如果判斷為 add_pet，但沒有「新增」「建立」等關鍵詞
        elif intent == 'add_pet':
            has_add_pet_keyword = any(keyword in text for keyword in add_pet_keywords)

            # 如果沒有新增關鍵詞，檢查是否應該是生活記錄
            if not has_add_pet_keyword:
                # 優先判斷：如果有時間關鍵詞（如「今天」「昨天」），很可能是生活記錄
                if has_time_keyword:
                    old_intent = intent
                    result['intent'] = 'add_daily_record'

                    # 修正 data 結構
                    pet_name = result.get('data', {}).get('pet_name', '')

                    # 如果有 feature 欄位（AI 誤判行為/狀況為外觀特徵）
                    content = text
                    if 'feature' in result.get('data', {}):
                        content = result['data']['feature']

                    # 推斷 record_type
                    final_record_type = detected_record_type if detected_record_type else 'other'

                    # 重建 data 結構
                    result['data'] = {
                        'pet_name': pet_name,
                        'record_type': final_record_type,
                        'content': content,
                        'temperature': None,
                        'weight': None,
                        'exercise_duration': None
                    }

                    print(f"[後處理] 🔧 自動修正意圖: {old_intent} → {result['intent']}")
                    print(f"[後處理] 原因: 檢測到時間關鍵詞「{[kw for kw in time_keywords if kw in text]}」，判斷為生活記錄")
                    print(f"[後處理] record_type: {final_record_type}")
                    print(f"[後處理] 原始文字: {text}")

                # 其次判斷：如果有檢測到生活記錄關鍵詞
                elif detected_record_type:
                    old_intent = intent
                    result['intent'] = 'add_daily_record'

                    # 修正 data 結構
                    pet_name = result.get('data', {}).get('pet_name', '')

                    # 如果有 feature 欄位（AI 可能誤判健康狀況為外觀特徵）
                    content = text
                    if 'feature' in result.get('data', {}):
                        # 使用原始 feature 內容作為記錄內容
                        content = result['data']['feature']

                    # 重建 data 結構
                    result['data'] = {
                        'pet_name': pet_name,
                        'record_type': detected_record_type,
                        'content': content,
                        'temperature': None,
                        'weight': None,
                        'exercise_duration': None
                    }

                    print(f"[後處理] 🔧 自動修正意圖: {old_intent} → {result['intent']}")
                    print(f"[後處理] 原因: 沒有「新增」「建立」關鍵詞，但檢測到 {detected_record_type} 關鍵詞")
                    print(f"[後處理] 原始文字: {text}")
                else:
                    # 沒有生活記錄關鍵詞，但也沒有新增關鍵詞 → 可能是錯誤判斷
                    print(f"[後處理] ⚠️ 警告: AI 判斷為 add_pet，但文字中沒有「新增」「建立」等關鍵詞")
                    print(f"[後處理] 原始文字: {text}")
                    print(f"[後處理] 建議: 這可能是陳述一個事實，而非建立新檔案")

        # 規則4：修正錯誤的 record_type
        # 如果是 add_daily_record，但 record_type 不正確，且我們檢測到了更精確的類型
        if intent == 'add_daily_record' and detected_record_type:
            current_record_type = result.get('data', {}).get('record_type')

            # 如果 AI 返回的是 'other'，但我們檢測到了更精確的類型（mood, diet, allergen 等）
            if current_record_type == 'other' and detected_record_type != 'other':
                old_record_type = current_record_type
                result['data']['record_type'] = detected_record_type

                print(f"[後處理] 🔧 自動修正 record_type: {old_record_type} → {detected_record_type}")
                print(f"[後處理] 原因: 檢測到更精確的分類關鍵詞")
                print(f"[後處理] 原始文字: {text}")

        return result

    def _fill_missing_numeric_records(self, text, result):
        """
        安全網：用正則表達式從原始文本提取數值，補充 AI 遺漏的記錄
        """
        import re

        data = result.get('data', {})
        records = data.get('records', [])

        # 檢查已有的記錄類型
        existing_types = {record.get('record_type') for record in records}

        added_count = 0

        # 🔍 檢測體溫
        if 'temperature' not in existing_types:
            # 匹配：體溫XX度、溫度XX度、XX度
            temp_patterns = [
                r'體溫[是]?(\d+(?:\.\d+)?)\s*度',
                r'溫度[是]?(\d+(?:\.\d+)?)\s*度',
                r'發燒[到]?(\d+(?:\.\d+)?)\s*度',
            ]
            for pattern in temp_patterns:
                match = re.search(pattern, text)
                if match:
                    temp_value = float(match.group(1))
                    records.append({
                        'record_type': 'temperature',
                        'content': f'體溫{temp_value}度',
                        'temperature': temp_value,
                        'weight': None,
                        'exercise_duration': None
                    })
                    print(f"[🛡️ 安全網] 自動補充體溫記錄: {temp_value}度")
                    added_count += 1
                    break

        # 🔍 檢測體重
        if 'weight' not in existing_types:
            # 匹配：體重XX公斤、XX公斤、重量XX
            weight_patterns = [
                r'體重[是]?(\d+(?:\.\d+)?)\s*公斤',
                r'體重[是]?(\d+(?:\.\d+)?)\s*kg',
                r'重量[是]?(\d+(?:\.\d+)?)\s*公斤',
                r'現在[是]?(\d+(?:\.\d+)?)\s*公斤',
            ]
            for pattern in weight_patterns:
                match = re.search(pattern, text)
                if match:
                    weight_value = float(match.group(1))
                    records.append({
                        'record_type': 'weight',
                        'content': f'體重{weight_value}公斤',
                        'temperature': None,
                        'weight': weight_value,
                        'exercise_duration': None
                    })
                    print(f"[🛡️ 安全網] 自動補充體重記錄: {weight_value}公斤")
                    added_count += 1
                    break

        # 🔍 檢測運動
        if 'exercise' not in existing_types:
            # 匹配：散步XX分鐘、運動XX分鐘、走了XX分鐘
            exercise_patterns = [
                r'散步[是]?(\d+)\s*分鐘',
                r'運動[是]?(\d+)\s*分鐘',
                r'走[了]?(\d+)\s*分鐘',
                r'跑[了]?(\d+)\s*分鐘',
            ]
            for pattern in exercise_patterns:
                match = re.search(pattern, text)
                if match:
                    exercise_value = int(match.group(1))
                    records.append({
                        'record_type': 'exercise',
                        'content': f'運動{exercise_value}分鐘',
                        'temperature': None,
                        'weight': None,
                        'exercise_duration': exercise_value
                    })
                    print(f"[🛡️ 安全網] 自動補充運動記錄: {exercise_value}分鐘")
                    added_count += 1
                    break

        if added_count > 0:
            print(f"[🛡️ 安全網] 共補充了 {added_count} 條AI遺漏的數值記錄")
            data['records'] = records
            result['data'] = data

        return result
