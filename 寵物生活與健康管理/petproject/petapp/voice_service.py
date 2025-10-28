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
                # 移除 language 參數，讓 Whisper 自動檢測語言（支援中英混合）
                beam_size=5,            # 提高準確度
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

        # 獲取今天的日期用於提示
        today = date.today().strftime('%Y-%m-%d')

        prompt = f"""你是一個專業的寵物管理系統語音助手。請仔細分析使用者的語音輸入，判斷意圖並抽取所有相關資訊。

今天的日期是：{today}

使用者說：「{text}」

請以 JSON 格式回應（只回傳 JSON，不要其他文字）：

{{
    "intent": "意圖類型",
    "confidence": 信心分數(0-1),
    "data": {{欄位資料}}
}}

【支援的意圖類型】：
1. add_pet - 新增寵物
2. add_daily_record - 新增生活記錄（體溫、體重、運動、飲食、用藥、行為觀察）
3. add_vaccine - 新增疫苗記錄
4. add_deworm - 新增驅蟲記錄
5. add_medical_record - 新增就診記錄
6. unknown - 無法判斷

【各意圖的欄位格式】：

1️⃣ add_pet:
{{
    "pet_name": "寵物名字",
    "species": "dog" 或 "cat",
    "breed": "品種",
    "gender": "M" 或 "F",
    "age": 年齡(整數),
    "weight": 體重(數字),
    "sterilization_status": "Y" 或 "N" 或 "U"(未知),
    "chip": "晶片號碼",
    "feature": "其他特徵描述"
}}

2️⃣ add_daily_record:
{{
    "pet_name": "寵物名字",
    "record_type": "temperature|weight|exercise|diet|medication|allergen|mood|other",
    "content": "記錄內容描述",
    "temperature": 體溫數值(如38.5),
    "weight": 體重數值(如5.2),
    "exercise_duration": 運動時長(分鐘)
}}

3️⃣ add_vaccine:
{{
    "pet_name": "寵物名字",
    "vaccine_name": "疫苗品牌/名稱",
    "date": "施打日期(YYYY-MM-DD)",
    "location": "施打地點",
    "protection_period_months": 保護效期(月)
}}

4️⃣ add_deworm:
{{
    "pet_name": "寵物名字",
    "deworm_name": "驅蟲品牌/名稱",
    "date": "施打日期(YYYY-MM-DD)",
    "location": "施打地點",
    "protection_period_months": 保護效期(月)
}}

5️⃣ add_medical_record:
{{
    "pet_name": "寵物名字",
    "visit_date": "就診日期(YYYY-MM-DD)",
    "clinic_location": "診所名稱（例如：愛心動物醫院、台北動物醫院，如果使用者說「XX醫院」「XX診所」必須填入此欄位）",
    "weight": 體重(kg),
    "temperature": 體溫(°C),
    "heart_rate": 心率(bpm),
    "respiratory_rate": 呼吸頻率,
    "chief_complaint": "主訴（主要症狀或就診原因）",
    "diagnosis": "診斷結果（例如：腸胃炎、感冒、皮膚病）",
    "treatment": "治療內容（例如：打針、開藥、點滴）",
    "total_cost": 費用(數字，例如1500代表1500元),
    "follow_up_required": true/false,
    "follow_up_date": "追蹤日期(YYYY-MM-DD)",
    "notes": "備註"
}}

重要提示：
- 如果使用者說「今天去XX醫院」「在XX診所」，clinic_location 必須填「XX醫院」或「XX診所」
- 如果使用者說「診斷是XX」「診斷為XX」「醫生說是XX」，diagnosis 應填「XX」
- 如果使用者說「開了XX藥」「打了針」「吃藥」，treatment 應包含這些內容
- 如果使用者說「花了一千五」「費用1500」「1500元」，total_cost 應填數字1500

【重要規則】：
- 如果欄位未提到，設為 null
- clinic_location 非常重要，請務必從使用者語音中提取醫院或診所名稱
- gender: M=公/男, F=母/女
- species: dog=狗, cat=貓
- sterilization_status: Y=已結紮, N=未結紮, U=未知
- date 格式必須是 YYYY-MM-DD，如果只說"今天"，請用 {today}
- 只回傳 JSON，不要任何其他解釋文字
- confidence 應該根據你對使用者意圖的確定程度來評分（0-1之間）
"""

        try:
            print(f"[Ollama] 開始分析文字: {text[:100]}...")
            response = ollama.chat(
                model='qwen2.5:1.5b-instruct',  # 統一使用 1.5b 模型（輕量快速）
                messages=[{'role': 'user', 'content': prompt}],
                format='json'  # 要求回傳 JSON 格式
            )

            # 解析 JSON
            content = response['message']['content']
            print(f"[Ollama] AI 回應: {content[:200]}...")

            result = json.loads(content)
            print(f"[Ollama] 解析成功 - 意圖: {result.get('intent')}, 信心度: {result.get('confidence')}")

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
