# petapp/chat_service.py
# -*- coding: utf-8 -*-
import os, re, json, requests, traceback
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# ====== 配置參數 ======
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "120"))  # 預設2分鐘，虛擬機環境建議更長

# ====== 專案路徑 ======
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(PROJECT_ROOT, "rag", "chroma_db")
COLLECTION_NAME = "faq_with_training"

# ====== 初始化向量檢索 ======
_client = None
_collection = None
_embedder = None

def init_vector_search():
    """初始化向量檢索系統"""
    global _client, _collection, _embedder

    if _client is not None:
        return True

    try:
        # 初始化向量資料庫
        import chromadb
        from chromadb.config import Settings
        _client = chromadb.PersistentClient(
            path=DB_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        _collection = _client.get_collection(COLLECTION_NAME)

        # 初始化嵌入模型
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")  # 自動配置  # 自動配置  # 自動配置  # 自動配置  # 自動配置

        print(f"[AI客服] 初始化成功，資料庫共有 {_collection.count()} 筆資料")
        return True

    except Exception as e:
        print(f"[AI客服] 初始化失敗: {e}")
        return False

def simple_search(query, top_k=3):
    """簡化版向量檢索"""
    if not init_vector_search():
        return []

    try:
        # 生成查詢向量
        query_embedding = _embedder.encode([query], normalize_embeddings=True).tolist()

        # 執行檢索
        results = _collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # 處理結果 - 使用更寬容的相似度計算
        matched_docs = []
        for doc, meta, dist in zip(docs, metas, distances):
            # 更寬容的相似度計算
            distance = abs(float(dist))

            # 對於距離值做更寬容的轉換
            if distance <= 0.5:
                similarity = 1.0  # 非常相似
            elif distance <= 1.0:
                similarity = 0.8  # 很相似
            elif distance <= 1.5:
                similarity = 0.5  # 中等相似
            else:
                similarity = max(0.0, 2.0 - distance) / 2.0  # 原始計算

            # 暫時降低門檻進行測試
            if similarity > 0.1:
                matched_docs.append({
                    'content': doc,
                    'title': meta.get('title', '寵物知識'),
                    'similarity': similarity
                })

        # 按相似度排序
        matched_docs.sort(key=lambda x: x['similarity'], reverse=True)

        print(f"[AI客服] 檢索到 {len(matched_docs)} 筆相關資料")
        return matched_docs[:2]  # 返回前2筆最相關的

    except Exception as e:
        print(f"[AI客服] 檢索錯誤: {e}")
        return []

def create_ai_prompt(user_question, search_results):
    """生成AI提示詞"""

    if not search_results:
        return f"""你是寵物照護專家，用戶問：{user_question}

由於暫時沒有找到直接相關的資料，請基於你的專業知識提供實用建議。
回答要求：
1. 直接回答問題，提供具體可行的建議
2. 用繁體中文回答
3. 內容要專業但易懂
4. 長度控制在150-300字
5. 如果是複雜醫療問題，建議諮詢獸醫"""

    # 整理檢索到的內容
    context = "\n".join([f"參考資料{i+1}：{doc['content']}" for i, doc in enumerate(search_results)])

    return f"""基於以下資料回答問題，用繁體中文，150字以內：

問題：{user_question}
資料：{context}

要求：實用、準確、簡潔。"""

def call_ai_model(prompt):
    """調用AI模型生成回答"""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,  # 可改為 True 啟用串流回應
            "options": {
                "temperature": 0.3,
                "num_ctx": 512,       # 進一步減少上下文長度
                "num_predict": 200,   # 減少預測長度到200字
                "num_thread": 2,      # 減少執行緒避免資源競爭
                "top_p": 0.9,         # 加入top_p提升效率
                "repeat_penalty": 1.1 # 避免重複內容
            }
        }

        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=OLLAMA_TIMEOUT_SEC)
        response.raise_for_status()

        data = response.json()
        if isinstance(data, dict) and "message" in data:
            return data["message"].get("content", "")

        return "AI回應格式錯誤"

    except requests.exceptions.ConnectionError:
        return "AI模型未啟動，請先執行：ollama serve"
    except Exception as e:
        print(f"[AI客服] 模型調用錯誤: {e}")
        return "AI服務暫時不可用，請稍後再試"

def fallback_response(question):
    """回退回答方案"""

    # 擴展關鍵字匹配，涵蓋更多常見問題
    keywords_responses = {
        "餵食|食物|飼料|營養|吃|餵|喂": "寵物餵食建議：\n1. 定時定量餵食\n2. 選擇適齡飼料\n3. 確保充足飲水\n4. 避免人類食物\n如需詳細飲食計劃，建議諮詢獸醫。",

        "健康|生病|疾病|症狀|不舒服|檢查": "寵物健康注意事項：\n1. 定期健康檢查\n2. 按時接種疫苗\n3. 觀察異常行為\n4. 維持清潔環境\n如有健康疑慮，請立即就醫。",

        "訓練|行為|吠叫|叫|教|學": "寵物行為訓練要點：\n1. 正向鼓勵為主\n2. 一致性指令\n3. 耐心重複練習\n4. 適當獎勵\n嚴重行為問題建議諮詢專業訓練師。",

        "洗澡|清潔|衛生|洗|乾淨|梳毛|護理|毛髮|美容": "寵物清潔護理：\n1. 定期洗澡（不宜過頻）\n2. 每日梳毛\n3. 清潔牙齒和耳朵\n4. 修剪指甲\n具體頻率依寵物種類而異。",

        "體重|紀錄|記錄|重量": "寵物體重管理：\n1. 定期測量並記錄體重\n2. 使用寵物專用秤或至獸醫院\n3. 建立體重變化表格\n4. 依體重調整飲食份量\n體重異常變化請諮詢獸醫。",

        "作息|生活|日常|時間": "寵物日常作息建議：\n1. 規律的餵食時間\n2. 固定的運動時段\n3. 充足的休息睡眠\n4. 定時的如廁訓練\n良好作息有助寵物健康成長。",

        "忘記密碼|忘記帳號|重設密碼|找回密碼|密碼重置": "密碼重設步驟：\n1. 點擊登入頁面的「忘記密碼？」連結\n2. 輸入您註冊時使用的Email地址\n3. 檢查信箱收取重設密碼郵件\n4. 點擊郵件中的重設連結\n5. 設定新密碼並確認\n\n如果沒有收到郵件，請檢查垃圾郵件匣或使用Google帳號登入。"
    }

    for pattern, response in keywords_responses.items():
        if re.search(pattern, question):
            return response

    return "目前知識庫沒有找到相關資訊，建議您：\n1. 諮詢專業獸醫\n2. 聯繫寵物店專家\n3. 查閱專業寵物照護書籍\n\n點選【轉人工客服】獲得進一步協助。"

@csrf_exempt
@require_POST
def api_chat(request):
    """AI客服主要API"""
    try:
        # 解析請求 - 處理編碼問題
        try:
            body = request.body.decode('utf-8')
        except UnicodeDecodeError:
            body = request.body.decode('utf-8', errors='ignore')

        data = json.loads(body)
        user_question = data.get("message", "").strip()

        if not user_question:
            return JsonResponse({"response": "請輸入您的問題"})

        try:
            print(f"[AI客服] 收到問題: {user_question}")
        except UnicodeEncodeError:
            print("[AI客服] 收到問題 (編碼問題，無法顯示)")

        # 優先檢查簡單的打招呼
        greeting_patterns = [
            r"^(hi|hello|嗨|哈囉|你好|您好)[\!！\?？]*$",
            r"^(早|午安|晚安|安|在嗎|在不在)[\!！\?？]*$"
        ]

        for pattern in greeting_patterns:
            if re.search(pattern, user_question, re.IGNORECASE):
                return JsonResponse({
                    "response": "您好！歡迎使用毛日好寵物生活管理平台！\n\n我是您的AI寵物照護助手，可以協助您：\n• 寵物餵食與營養指導\n• 健康照護建議\n• 行為訓練指導\n• 日常護理方法\n\n請告訴我您想了解什麼寵物相關問題？"
                })

        # 優先檢查常見系統操作問題（高優先級關鍵字匹配）
        priority_keywords = {
            "忘記密碼|忘記帳號|重設密碼|找回密碼|密碼重置": "密碼重設步驟：\n1. 點擊登入頁面的「忘記密碼？」連結\n2. 輸入您註冊時使用的Email地址\n3. 檢查信箱收取重設密碼郵件\n4. 點擊郵件中的重設連結\n5. 設定新密碼並確認\n\n如果沒有收到郵件，請檢查垃圾郵件匣或使用Google帳號登入。",

            "註冊|如何註冊|註冊帳號|建立帳號": "毛日好註冊步驟：\n1. 點擊右上角「註冊」按鈕\n2. 填寫姓名、Email、用戶名和密碼\n3. 點擊「註冊」按鈕\n4. 檢查信箱點擊確認連結\n5. 完成註冊即可登入使用\n\n也可以使用Google帳號快速註冊登入。",

            "登入|如何登入|無法登入": "登入方式：\n1. 使用註冊時的Email和密碼登入\n2. 或點擊「使用Google帳號登入」\n3. 如果忘記密碼，點擊「忘記密碼？」\n\n登入問題請確認：\n• Email拼寫正確\n• 密碼大小寫是否正確\n• 是否已完成Email驗證",

            "上傳.*照片|照片.*上傳|寵物.*照片|照片.*限制": "寵物照片上傳規格：\n1. 支援格式：JPG、PNG\n2. 檔案大小：不超過5MB\n3. 建議尺寸：800x800像素以上\n4. 系統會自動壓縮過大圖片\n5. 每隻寵物可上傳多張照片\n6. 照片用於寵物檔案和領養展示",

            "預約.*獸醫|獸醫.*預約|預約.*門診|門診.*預約": "毛日好預約獸醫門診：\n1. 點擊「預約門診」功能\n2. 選擇獸醫院和醫師\n3. 挑選可預約時段\n4. 填寫就診資訊和聯絡方式\n5. 確認預約資訊並送出\n6. 獸醫院會確認預約時間"
        }

        for pattern, response in priority_keywords.items():
            if re.search(pattern, user_question, re.IGNORECASE):
                return JsonResponse({"response": response})

        # 向量檢索 (優先使用詳細的Excel資料)
        search_results = simple_search(user_question)
        print(f"[AI客服] 向量檢索結果數量: {len(search_results)}")
        for i, result in enumerate(search_results):
            print(f"[AI客服] 結果{i+1}: 相似度={result['similarity']:.3f}, 內容前50字: {result['content'][:50]}...")

        if search_results:
            # 有檢索結果，使用AI生成回答
            prompt = create_ai_prompt(user_question, search_results)
            ai_response = call_ai_model(prompt)

            if ai_response and "AI模型未啟動" not in ai_response and "AI服務暫時不可用" not in ai_response:
                print(f"[AI客服] AI回答成功，長度: {len(ai_response)}")
                return JsonResponse({"response": ai_response})

        # 如果向量檢索失效，才使用關鍵字匹配
        system_patterns = [
            r"毛日好|註冊|登入|登錄|帳號|密碼|會員",
            r"這個系統|平台|網站|如何使用",
            r"功能|操作|怎麼用"
        ]

        for pattern in system_patterns:
            if re.search(pattern, user_question, re.IGNORECASE):
                return JsonResponse({
                    "response": "歡迎使用毛日好寵物生活管理平台！\n\n關於系統使用：\n• 註冊：點選右上角「註冊」按鈕建立帳號\n• 登入：使用您的帳號密碼或Google帳號登入\n• 功能：管理寵物資料、健康紀錄、領養資訊等\n\n如需詳細操作說明，請參考使用手冊或聯繫客服人員協助。"
                })

        # 沒有檢索結果或AI調用失敗，使用回退方案
        fallback = fallback_response(user_question)
        print(f"[AI客服] 使用回退回答，長度: {len(fallback)}")
        return JsonResponse({"response": fallback})

    except Exception as e:
        print(f"[AI客服] 處理錯誤: {e}")
        traceback.print_exc()
        return JsonResponse({"response": "服務暫時不可用，請稍後再試"})

@csrf_exempt
def api_chat_stream(request):
    """串流版本（暫時返回普通版本）"""
    return api_chat(request)

def clear_cache(request):
    """清除快取"""
    global _client, _collection, _embedder
    _client = None
    _collection = None
    _embedder = None
    return JsonResponse({"status": "cache cleared"})

def kb_status(request):
    """知識庫狀態檢查"""
    try:
        if init_vector_search():
            count = _collection.count() if _collection else 0
            return JsonResponse({
                "status": "ok",
                "vector_db": "connected",
                "documents": count,
                "embedder": "loaded"
            })
        else:
            return JsonResponse({
                "status": "error",
                "vector_db": "disconnected",
                "documents": 0,
                "embedder": "failed"
            })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        })