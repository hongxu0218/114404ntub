# petapp/chat_service.py
# -*- coding: utf-8 -*-
import os, re, json, requests, traceback, time
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# ====== 可選：環境變數覆蓋 ======
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "qwen2.5:3b-instruct")  # 建議先 3B 穩定
TOP_K           = int(os.getenv("RAG_TOP_K", "4"))
SNIPPET_CHARS   = int(os.getenv("RAG_SNIPPET_CHARS", "800"))  # >0 時截斷每段脈絡長度

# 模型與網路參數（優化性能）
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "30"))  # 減少超時時間
OLLAMA_NUM_CTX     = int(os.getenv("OLLAMA_NUM_CTX", "2048"))    # 增加上下文長度以支持更完整對話
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "800")) # 增加預測token數以支持完整回答
OLLAMA_TEMP        = float(os.getenv("OLLAMA_TEMP", "0.2"))      # 降低溫度提高一致性

# 是否把 sources 顯示給使用者（預設關閉）
_SHOW_SOURCES_ENV = os.getenv("SHOW_SOURCES_TO_USER", "0").lower()
SHOW_SOURCES_TO_USER = _SHOW_SOURCES_ENV in ("1", "true", "yes", "y")

# ====== 專案路徑 / 向量庫路徑 ======
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(PROJECT_ROOT, "rag", "chroma_db")   # ← 指向你的向量庫資料夾
COLLECTION_NAME = os.getenv("RAG_COLLECTION", "faq_with_training")      # ← 和你匯入的 collection 一致

# ====== 防 500：條件性載入 ======
try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb, Settings = None, None

# 匹配向量庫的嵌入模型維度
try:
    from sentence_transformers import SentenceTransformer
    # 使用512維的模型以匹配向量庫
    _embedder = SentenceTransformer("BAAI/bge-base-zh-v1.5")  # 512維，與ChromaDB一致
except Exception:
    try:
        # 備用選項：384維模型
        _embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5")  # 384維
    except Exception:
        _embedder = None

# ====== 回覆風格與格式 ======
FORMAT_INSTRUCTIONS = (
    "【輸出格式要求】\n"
    "若有命中知識片段：第一句以「根據提供的知識片段，」起頭；"
    "若無命中：第一句以「（一般建議）」起頭。\n"
    "接著輸出：\n"
    "1) 以條列步驟（1., 2., 3.）提供可執行指引；\n"
    "2) 接一個『注意事項：』小節，至少 2 點；\n"
    "請勿在最終輸出中主動加入「來源／參考來源」等字樣或清單。\n"
)
SYSTEM_PROMPT = (
    "你是『毛日好 Paw&Day』網站 AI 客服，請一律使用『繁體中文』回覆，"
    "先釐清使用者需求，再以條列步驟給出精簡可執行的回答。"
    "若屬於網站功能（註冊/登入/預約/健康紀錄/通知等），請指出頁面與按鈕路徑。"
    "若用戶問 FAQs，優先引用下方檢索的知識內容；若找不到就基於一般常識回覆，並標示『（一般建議）』。"
    "無論知識片段或產出中出現簡體或錯字，輸出給使用者前一律轉為正確的繁體中文（台灣用語），"
    "並自動校正常見錯字（如：'按鈍'→'按鈕'，'寻找/尋找'→'尋找'，'注册/注冊'→'註冊'，'登录/登錄'→'登入'）。"
    "\n\n" + FORMAT_INSTRUCTIONS
)

def _truncate(text: str, n: int) -> str:
    if not n or n <= 0 or len(text) <= n:
        return text
    return text[:n] + "…"

# ====== 繁體（台灣用語）＋常見錯字校正 ======
try:
    from opencc import OpenCC
    _cc_s2twp = OpenCC('s2twp')  # 簡 → 台灣繁體
    _cc_t2twp = OpenCC('t2twp')  # 繁 → 台灣用語
except Exception:
    _cc_s2twp = _cc_t2twp = None  # 沒裝 opencc 也不會當

_CUSTOM_REPLACE = {
    "按鈍": "按鈕",
    "寻找": "尋找",
    "注册": "註冊",
    "注冊": "註冊",
    "会员": "會員",
    "登录": "登入",
    "登錄": "登入",
    "菜單": "選單",
}

def normalize_zh_tw(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    t = text
    if _cc_s2twp and _cc_t2twp:
        t = _cc_s2twp.convert(t)
        t = _cc_t2twp.convert(t)
    for bad, good in _CUSTOM_REPLACE.items():
        t = t.replace(bad, good)
    return t

# ====== 後處理：條列與注意事項換行（更嚴謹）＋來源段落移除 ======
_LINE_ITEM_RE = re.compile(r'(?<!\S)(\d{1,2}\.)')  # 行首或空白邊界的「1.」「2.」
_SOURCE_LINE_PAT = re.compile(r"^\s*(參考來源|來源|資料來源)\s*[:：]?\s*$")

def _force_linebreaks(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return text
    t = text
    # 處理注意事項前的換行
    t = t.replace("注意事項：", "\n注意事項：")
    # 處理數字項目換行，但只在需要時添加
    t = re.sub(r'([^\n])(\d{1,2}\.)', r'\1\n\2', t)
    # 清理多餘的空白和換行
    t = re.sub(r'[ \t]+', ' ', t)  # 合併多餘空格
    t = re.sub(r'\n{3,}', '\n\n', t)  # 最多保留一個空行
    t = re.sub(r'^\s*\n+', '', t)  # 移除開頭的空行
    return t.strip()

def _strip_source_section(text: str) -> str:
    """
    移除模型正文裡以「來源：」「參考來源：」等開頭的段落與條列。
    也移除結尾殘留的「參考來源：無」。
    """
    if not isinstance(text, str) or not text.strip():
        return text
    t = text.replace("參考來源：無", "").rstrip()

    lines = t.splitlines()
    new_lines, skip = [], False
    for ln in lines:
        if _SOURCE_LINE_PAT.match(ln):
            skip = True
            continue
        if skip:
            if not ln.strip():  # 空行當作段落結束
                skip = False
            continue
        if ln.strip() in ("來源", "參考來源", "資料來源"):
            continue
        new_lines.append(ln)
    t = "\n".join(new_lines).rstrip()
    return t

# ====== 串流安全包裝：偵測用戶端中斷，安靜收尾 ======
def _guard_stream(generator):
    """
    將任一字串產生器包起來；若用戶端關閉連線（BrokenPipe / Reset / GeneratorExit），
    立即停止迴圈，避免 console 汙染與上游資源浪費。
    """
    try:
        for chunk in generator:
            yield chunk
    except (BrokenPipeError, ConnectionResetError, GeneratorExit):
        return
    except Exception as e:
        try:
            yield json.dumps({"type":"error","message":f"（一般建議）串流發生錯誤：{e}"}) + "\n"
        finally:
            return

# ====== 轉人工客服：連續失敗判斷 ======
HANDOFF_THRESHOLD = int(os.getenv("HANDOFF_THRESHOLD", "3"))
HANDOFF_COOLDOWN_SEC = int(os.getenv("HANDOFF_COOLDOWN_SEC", "900"))
HANDOFF_SESSION_KEY = "handoff_fail_count"
HANDOFF_LAST_TS_KEY = "handoff_last_ts"

_HANDOFF_FAIL_HINTS = [
    "（一般建議）", "我不太清楚", "我不確定", "無法判斷",
    "找不到相關資訊", "建議您聯絡客服"
]

def _is_ai_failure(reply_text: str, context_hit: bool, smalltalk: bool) -> bool:
    if smalltalk:
        return False
    if context_hit:
        return False
    t = (reply_text or "").strip()
    return any(h in t for h in _HANDOFF_FAIL_HINTS)

def _update_handoff_state(request, failed: bool):
    sess = request.session
    cnt = int(sess.get(HANDOFF_SESSION_KEY, 0))
    last = int(sess.get(HANDOFF_LAST_TS_KEY, 0))
    now  = int(time.time())

    if failed:
        cnt += 1
        sess[HANDOFF_SESSION_KEY] = cnt
    else:
        cnt = 0
        sess[HANDOFF_SESSION_KEY] = 0

    suggest = False
    if cnt >= HANDOFF_THRESHOLD and (now - last >= HANDOFF_COOLDOWN_SEC):
        suggest = True
        sess[HANDOFF_LAST_TS_KEY] = now

    meta = {
        "count": cnt,
        "threshold": HANDOFF_THRESHOLD,
        "cooldown_sec": HANDOFF_COOLDOWN_SEC,
        "suggest": suggest
    }
    return suggest, meta

# ====== 小聊/寒暄偵測 ======
_GREETING_PAT = re.compile(
    r"^(你好|您好|哈囉|嗨|hi|hello|hey|早安|午安|晚安|在嗎|有人在嗎|測試|test)$",
    re.IGNORECASE
)
_SMALLTALK_HINTS = [
    "無聊", "難過", "好累", "壓力", "焦慮", "生氣", "好開心",
    "不想上班", "不想工作", "想請假", "好懶"
]

def is_low_intent_smalltalk(text: str) -> bool:
    if not text:
        return True
    t = (text or "").strip()
    if _GREETING_PAT.match(t):
        return True
    if any(k in t for k in _SMALLTALK_HINTS):
        return True
    return False

def smalltalk_reply(user_text: str = "") -> str:
    t = (user_text or "").strip()

    if "無聊" in t:
        return normalize_zh_tw(
            "有點無聊嗎？來幾個和毛孩的輕鬆小任務：\n"
            "1. 零食嗅聞遊戲：把小零食藏在紙杯或毛巾底下，讓牠用鼻子找。\n"
            "2. 腦力玩具：用益智玩具（或寶特瓶戳洞自製）讓飼料慢慢掉出來。\n"
            "3. 快速放電：室內 5 分鐘逗貓棒／拋接玩具。\n"
            "4. 新把戲：練「坐下/碰拳/旋轉」，每次 1–2 分鐘。\n"
            "5. 嗅聞散步：散步時允許慢慢聞（聞=工作）。\n\n"
            "需要我把這些加入『每日任務』清單嗎？🙂"
        )

    if any(k in t for k in ["壓力", "焦慮", "難過", "心情不好"]):
        return normalize_zh_tw(
            "先深呼吸一下～也許和毛孩做點安定的小事會有幫助：\n"
            "1. 規律撫摸胸前/肩頸 3–5 分鐘。\n"
            "2. 低刺激散步，讓牠多嗅聞。\n"
            "3. 穩定儀式：固定點心/喝水/回籠順序。\n"
        )

    if any(k in t for k in ["不想上班", "不想工作", "想請假", "好懶"]):
        return normalize_zh_tw(
            "看起來你現在真的不太想上班～先讓自己深呼吸一下吧。\n"
            "1. 想像下班後的小確幸。\n"
            "2. 走動與喝水 3–5 分鐘。\n"
            "3. 和毛孩互動一下減壓。"
        )

    if _GREETING_PAT.match(t):
        return normalize_zh_tw(
            "哈囉～我在這！🙂\n"
            "想查詢預約、健康紀錄或常見問題嗎？你可以試試：\n"
            "1. 如何新增寵物？\n"
            "2. 預約洗澡的流程？\n"
            "3. 狗狗疫苗時程怎麼看？"
        )

    return normalize_zh_tw(
        "嗨～我在這。如果你願意，我可以：\n"
        "• 依毛孩年齡/體力安排每日互動清單\n"
        "• 幫你查常見問題或預約流程\n"
        "• 紀錄今天的散步/飲水/便便狀況"
    )

# ====== 「不要/不用了」快捷出口 ======
NEGATIVE_EXIT_WORDS = {"不要", "不用了", "算了", "先這樣", "不需要", "no", "No", "NO"}
def is_negative_exit(text: str) -> bool:
    return (text or "").strip() in NEGATIVE_EXIT_WORDS

# ====== 基本回應生成（當檢索失敗時） ======
def generate_fallback_response(user_msg: str) -> str:
    """當知識庫檢索失敗時，生成基本的寵物護理回應"""
    msg = (user_msg or "").lower()

    # 洗澡相關
    if any(word in msg for word in ["洗澡", "清潔", "沐浴"]):
        return normalize_zh_tw(
            "（一般建議）關於寵物洗澡的基本建議：\n\n"
            "1. 狗狗一般每1-2個月洗澡一次，貓咪通常不需要經常洗澡。\n"
            "2. 使用寵物專用洗毛精，水溫保持溫暖（約38-40°C）。\n"
            "3. 洗澡前先梳理毛髮，洗後徹底吹乾避免感冒。\n"
            "4. 耳朵進水可能引發感染，建議使用棉球保護。\n\n"
            "注意事項：\n"
            "• 幼齡或生病的寵物應避免洗澡。\n"
            "• 如有皮膚問題，請先諮詢獸醫師。"
        )

    # 疫苗相關
    if any(word in msg for word in ["疫苗", "預防針", "接種"]):
        return normalize_zh_tw(
            "（一般建議）關於寵物疫苗接種：\n\n"
            "1. 幼犬：8-10週齡開始首次疫苗，之後每3-4週補強。\n"
            "2. 幼貓：9-12週齡開始首次疫苗，之後每3-4週補強。\n"
            "3. 成年寵物每年需要補強疫苗。\n"
            "4. 狂犬病疫苗為法定必須接種項目。\n\n"
            "注意事項：\n"
            "• 疫苗前確保寵物身體健康。\n"
            "• 建議諮詢當地獸醫師制定個人化疫苗計畫。"
        )

    # 飲食相關
    if any(word in msg for word in ["飼料", "食物", "飲食", "餵食", "營養"]):
        return normalize_zh_tw(
            "（一般建議）關於寵物飲食：\n\n"
            "1. 選擇符合年齡段的高品質寵物飼料。\n"
            "2. 定時定量餵食，避免暴飲暴食。\n"
            "3. 確保充足的乾淨飲水。\n"
            "4. 避免餵食人類食物，特別是巧克力、洋蔥等有毒食物。\n\n"
            "注意事項：\n"
            "• 幼齡寵物需要較高頻率的餵食。\n"
            "• 如有特殊健康狀況，請諮詢獸醫師。"
        )

    # 訓練相關
    if any(word in msg for word in ["訓練", "教育", "行為", "服從"]):
        return normalize_zh_tw(
            "（一般建議）關於寵物訓練：\n\n"
            "1. 使用正向強化方式，獎勵良好行為。\n"
            "2. 保持訓練的一致性和耐心。\n"
            "3. 從基本指令開始：坐下、等待、過來。\n"
            "4. 社會化訓練同樣重要，讓寵物適應不同環境。\n\n"
            "注意事項：\n"
            "• 避免體罰，可能造成心理創傷。\n"
            "• 每次訓練時間不宜過長（10-15分鐘）。"
        )

    return ""  # 如果都不匹配，返回空字串

# ====== 意圖分流：每日互動清單 ======
_INTENT_PATTERNS = {
    "activity_plan": [
        "依毛孩年齡/體力安排每日互動清單",
        "每日互動清單", "互動清單", "活動清單", "每日任務",
    ]
}

def detect_intent(text: str) -> str:
    t = (text or "").strip()
    for intent, phrases in _INTENT_PATTERNS.items():
        if any(p in t for p in phrases):
            return intent
    return ""

def generate_activity_plan(
    species: str = "", age_years: float = None, weight_kg: float = None,
    energy: str = "", notes: str = ""
) -> str:
    sp = species or ""
    eg = (energy or "中").strip()
    try:
        age = float(age_years) if age_years is not None else None
    except Exception:
        age = None

    stage = "成齡"
    if age is not None:
        if age < 1:
            stage = "幼齡"
        elif age >= 7 and sp == "狗":
            stage = "熟齡"
        elif age >= 10 and sp == "貓":
            stage = "熟齡"

    mult = {"低": 0.7, "中": 1.0, "高": 1.3}.get(eg, 1.0)

    def mins(base):
        import math
        return int(5 * round((base * mult) / 5.0))

    if sp == "狗":
        walk_main = 25 if stage == "幼齡" else (35 if stage == "成齡" else 20)
        brain = 8 if stage == "幼齡" else (10 if stage == "成齡" else 8)
        play = 10 if stage == "幼齡" else (12 if stage == "成齡" else 8)
        plan = [
            f"1) 早晨：嗅聞散步＋如廁（{mins(walk_main)} 分）。",
            f"2) 上午：益智找食／嗅聞盒（{mins(brain)} 分）。",
            f"3) 下午：基礎訓練（{mins(brain)} 分）。",
            f"4) 傍晚：互動遊戲（{mins(play)} 分）。",
            f"5) 晚間：短程舒緩散步（{mins(15)} 分）。",
            f"6) 安定儀式（{mins(8)} 分）。",
        ]
        guard = [
            "注意事項：",
            "• 炎熱/雨天改室內嗅聞與找食。",
            "• 若有喘氣過快、跛行，立即降強度並評估就醫。",
            "• 零食總量 ≤ 每日熱量 10%。"
        ]
    elif sp == "貓":
        hunt = 8 if stage == "幼齡" else (10 if stage == "成齡" else 6)
        plan = [
            f"1) 早晨：逗貓棒狩獵循環（{mins(hunt)} 分）。",
            f"2) 上午：嗅聞找食（{mins(8)} 分）。",
            "3) 下午：環境探索（即時）。",
            f"4) 傍晚：逗貓棒第二回合（{mins(hunt)} 分）。",
            f"5) 晚間：梳理＋安定撫摸（{mins(6)} 分）。",
            "6) 貓砂巡檢（即時）。",
        ]
        guard = [
            "注意事項：",
            "• 若持續張口呼吸/躲藏不出，立即停止並評估壓力源。",
            "• 玩具收納避免誤食；避免高處危險跳躍。",
            "• 濕食可增攝水；器具每日清洗。"
        ]
    else:
        plan = [
            "1) 早晨：簡短互動（10–15 分）。",
            "2) 上午：腦力小任務（5–10 分）。",
            "3) 傍晚：主要活動（15–25 分）。",
            "4) 晚間：安定儀式（5–10 分）。"
        ]
        guard = [
            "注意事項：",
            "• 若喘氣、跛行、拒食、嘔吐等異常，降量並視情況就醫。",
            "• 每日至少一次腦力任務以降低破壞行為。"
        ]

    header = f"（一般建議）已為你生成**每日互動清單**（{sp or '通用'}｜能量：{eg}）"
    if age is not None:
        header += f"｜年齡：約 {age} 歲"
    extra = []
    if weight_kg:
        extra.append(f"體重：約 {weight_kg} kg")
    if notes:
        extra.append(f"備註：{notes}")
    if extra:
        header += "（" + "；".join(extra) + "）"

    return normalize_zh_tw(
        header + "\n" + "\n".join(plan) + "\n\n" + "\n".join(guard) +
        "\n\n需要我把這份清單存到你的『健康紀錄／每日任務』嗎？"
    )

# ====== 向量檢索（回 context_text 與 sources） ======
# 快取客戶端和嵌入模型來避免重複初始化
_client_cache = None
_collection_cache = None

def clear_cache():
    """清除快取的客戶端和集合"""
    global _client_cache, _collection_cache
    _client_cache = None
    _collection_cache = None
    print("[api_chat] 已清除快取")

def _get_cached_client():
    """獲取快取的客戶端和集合"""
    global _client_cache, _collection_cache

    if _client_cache is None or _collection_cache is None:
        if not chromadb or not Settings:
            return None, None
        try:
            _client_cache = chromadb.PersistentClient(
                path=DB_DIR,
                settings=Settings(anonymized_telemetry=False)
            )
            _collection_cache = _client_cache.get_or_create_collection(COLLECTION_NAME)
        except Exception as e:
            print(f"[api_chat] 初始化客戶端失敗: {e}")
            return None, None

    return _client_cache, _collection_cache

def safe_retrieve(query: str, top_k: int = TOP_K):
    """
    回傳：(context_text, sources: List[Dict])。
    優化版本：使用快取和降低的相似度門檻。
    """
    if _embedder is None:
        print("[api_chat] _embedder 缺失，無法檢索")
        return "", []

    client, col = _get_cached_client()
    if not client or not col:
        print("[api_chat] 無法獲取檢索客戶端")
        return "", []

    try:
        # 快速嵌入
        q_emb = _embedder.encode([query], normalize_embeddings=True).tolist()

        # 減少檢索數量以提高速度
        search_k = min(top_k, 3)  # 最多檢索3個結果

        res = col.query(
            query_embeddings=q_emb,
            n_results=search_k,
            include=["documents", "metadatas", "distances"]
        )

        docs = (res or {}).get("documents", [[]])[0] or []
        metas = (res or {}).get("metadatas", [[]])[0] or []
        dists = (res or {}).get("distances", [[]])[0] or []

        if not docs:
            return "", []

        # 使用更寬鬆的門檻以更快找到結果
        threshold = 0.4  # 固定使用較低門檻
        pairs = []

        for d, m, dist in zip(docs, metas, dists):
            try:
                sim = 1.0 - float(dist)
                if sim >= threshold:
                    pairs.append((d, m or {}, sim))
            except Exception:
                continue

        if not pairs:
            return "", []

        pairs.sort(key=lambda x: x[2], reverse=True)

        blocks, sources = [], []
        for i, (d, m, sim) in enumerate(pairs[:2], start=1):  # 最多使用2個片段
            # 縮短片段長度以減少處理時間
            snippet_len = min(SNIPPET_CHARS, 400) if SNIPPET_CHARS > 0 else 400
            snippet = _truncate(d, snippet_len)
            blocks.append(snippet.strip())
            sources.append({
                "id": (m.get("id") or f"rank-{i}"),
                "title": (m.get("title") or m.get("source") or "片段"),
                "score": round(sim, 4),
            })

        print(f"[api_chat] 快速檢索命中 {len(pairs)} 筆")
        return "\n\n---\n\n".join(blocks), sources

    except Exception as e:
        print(f"[api_chat] 檢索錯誤：{e}")
        return "", []

# ====== 與 Ollama 對話（一次回傳版） ======
def chat_with_ollama(messages):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": OLLAMA_TEMP,
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_NUM_PREDICT,
            "keep_alive": "10m",  # 增加模型快取時間
        }
    }
    try:
        r = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=OLLAMA_TIMEOUT_SEC)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            if isinstance(data.get("message"), dict) and "content" in data["message"]:
                return data["message"]["content"]
            if "response" in data:
                return data["response"]
        return "（一般建議）收到非預期格式回應，請稍後再試。"
    except requests.exceptions.ConnectionError:
        return "（一般建議）本機模型尚未啟動，請先執行：`ollama serve`，並確認已 `ollama pull qwen2.5:3b-instruct`。"
    except Exception as e:
        print("[api_chat] 與 Ollama 溝通錯誤：", e)
        traceback.print_exc()
        return f"（一般建議）AI 回覆發生錯誤：{e}"

# ====== 與 Ollama 串流對話（NDJSON）—強化版 ======
def chat_with_ollama_stream(messages):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": OLLAMA_TEMP,
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_NUM_PREDICT,
            "keep_alive": "10m",  # 增加模型快取時間
        }
    }
    r = None
    try:
        r = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=OLLAMA_TIMEOUT_SEC, stream=True)
        r.raise_for_status()

        # 逐行讀取 NDJSON；若下游（瀏覽器）已關閉，外層 _guard_stream 會終止並走到 finally 關 connection
        for line in r.iter_lines(chunk_size=8192, decode_unicode=True):
            if not line:
                continue
            try:
                piece = json.loads(line)
            except Exception:
                raw = normalize_zh_tw(line)
                yield json.dumps({"type": "delta", "text": raw}) + "\n"
                continue

            delta = ""
            if isinstance(piece.get("message"), dict):
                delta = piece["message"].get("content", "") or ""
            if not delta and "response" in piece:
                delta = piece.get("response") or ""

            if delta:
                delta = normalize_zh_tw(delta)
                yield json.dumps({"type": "delta", "text": delta}) + "\n"

        yield json.dumps({"type": "done"}) + "\n"

    except requests.exceptions.ConnectionError:
        yield json.dumps({"type":"error","message":"（一般建議）本機模型尚未啟動，請先執行：ollama serve，並確認已 pull 模型。"}) + "\n"
        yield json.dumps({"type":"done"}) + "\n"
    except (BrokenPipeError, ConnectionResetError, GeneratorExit):
        return
    except Exception as e:
        yield json.dumps({"type":"error","message":f"（一般建議）AI 回覆發生錯誤：{e}"}) + "\n"
        yield json.dumps({"type":"done"}) + "\n"
    finally:
        try:
            if r is not None:
                r.close()
        except Exception:
            pass

# ====== 非串流端點：/api/chat/ ======
@csrf_exempt
@require_POST
def api_chat(request):
    try:
        body = request.body
        if isinstance(body, bytes):
            body = body.decode('utf-8', errors='ignore')
        data = json.loads(body)
    except Exception:
        return JsonResponse({"reply": "（一般建議）請檢查JSON格式是否正確"})

    user_msg = (data.get("message") or "").strip()
    history = data.get("history") or []
    if not user_msg:
        return JsonResponse({"reply": "（一般建議）請輸入想詢問的內容，例如：如何新增寵物？"})

    # ✅ 使用者明確說「不要/不用了…」→ 立刻收尾並建議轉人工
    if is_negative_exit(user_msg):
        return JsonResponse({
            "reply": "了解～那我就不再建議囉。如需協助可以隨時點選【轉人工客服】🙂",
            "sources": [],
            "handoff": {
                "count": 0,
                "threshold": HANDOFF_THRESHOLD,
                "cooldown_sec": HANDOFF_COOLDOWN_SEC,
                "suggest": True
            }
        })

    # 小聊
    if is_low_intent_smalltalk(user_msg):
        return JsonResponse({"reply": smalltalk_reply(user_msg), "sources": [], "handoff": {
            "count": 0, "threshold": HANDOFF_THRESHOLD, "cooldown_sec": HANDOFF_COOLDOWN_SEC, "suggest": False
        }})

    # 意圖攔截
    intent = detect_intent(user_msg)
    if intent == "activity_plan":
        reply = generate_activity_plan()
        reply = _force_linebreaks(reply)
        reply = _strip_source_section(reply)
        return JsonResponse({"reply": reply, "sources": [], "handoff": {
            "count": 0, "threshold": HANDOFF_THRESHOLD, "cooldown_sec": HANDOFF_COOLDOWN_SEC, "suggest": False
        }})

    # RAG 檢索 - 添加快速失敗機制
    try:
        context, sources = safe_retrieve(user_msg)
    except Exception as e:
        print(f"[api_chat] 檢索系統錯誤，使用預設回應: {e}")
        context, sources = "", []

    if not context:
        # 提供基本的寵物護理回應
        fallback_response = generate_fallback_response(user_msg)
        if fallback_response:
            return JsonResponse({
                "reply": fallback_response,
                "sources": [],
                "handoff": _update_handoff_state(request, failed=False)[1],
            })
        else:
            return JsonResponse({
                "reply": "目前知識庫沒有找到相關資訊，建議您點選【轉人工客服】進一步協助。",
                "sources": [],
                "handoff": _update_handoff_state(request, failed=True)[1],  # 記一次失敗
            })

    opening = "根據提供的知識片段，"
    user_block = (
        f"{opening}請回答下列問題。\n\n"
        f"【站內知識】\n{context}\n\n"
        f"【使用者問題】{user_msg}"
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_block}]
    for h in history[-6:]:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.insert(1, h)

    reply = chat_with_ollama(messages)
    reply = normalize_zh_tw(reply)
    reply = _force_linebreaks(reply)
    reply = _strip_source_section(reply)

    if isinstance(reply, str) and reply.strip().endswith("參考來源：無"):
        reply = reply.rsplit("參考來源：無", 1)[0].rstrip()

    # 既然有命中 context，就不視為失敗
    _, handoff_meta = _update_handoff_state(request, failed=False)

    debug = bool(data.get("debug"))
    return JsonResponse({
        "reply": reply,
        "sources": (sources if (SHOW_SOURCES_TO_USER or debug) else []),
        "handoff": handoff_meta,
    })

# ====== 串流端點：/api/chat/stream/（NDJSON） ======
@csrf_exempt
@require_POST
def api_chat_stream(request):
    try:
        body = request.body
        if isinstance(body, bytes):
            body = body.decode('utf-8', errors='ignore')
        data = json.loads(body)
    except Exception:
        return StreamingHttpResponse(
            _guard_stream(iter([json.dumps({"type":"error","message":"（一般建議）請檢查JSON格式是否正確"})+"\n",
                                json.dumps({"type":"done"})+"\n"])),
            content_type="application/x-ndjson; charset=utf-8"
        )

    user_msg = (data.get("message") or "").strip()
    history  = (data.get("history") or [])
    if not user_msg:
        return StreamingHttpResponse(
            _guard_stream(iter([json.dumps({"type":"error","message":"（一般建議）請輸入想詢問的內容，例如：如何新增寵物？"})+"\n",
                                json.dumps({"type":"done"})+"\n"])),
            content_type="application/x-ndjson; charset=utf-8"
        )

    # ✅ 使用者明確說「不要/不用了…」→ 立刻收尾並建議轉人工
    if is_negative_exit(user_msg):
        def _bye_gen():
            yield json.dumps({"type":"meta","sources": []}) + "\n"
            yield json.dumps({"type":"delta","text":"了解～那我就不再建議囉。如需協助可以隨時點選【轉人工客服】🙂"}) + "\n"
            yield json.dumps({"type":"handoff","payload":{
                "count": 0, "threshold": HANDOFF_THRESHOLD, "cooldown_sec": HANDOFF_COOLDOWN_SEC, "suggest": True
            }}) + "\n"
            yield json.dumps({"type":"done"}) + "\n"
        resp = StreamingHttpResponse(_guard_stream(_bye_gen()), content_type="application/x-ndjson; charset=utf-8")
        resp["Cache-Control"] = "no-cache, no-transform"
        resp["X-Accel-Buffering"] = "no"
        return resp

    # 小聊
    if is_low_intent_smalltalk(user_msg):
        def _greet_gen():
            yield json.dumps({"type":"meta","sources": []}) + "\n"
            yield json.dumps({"type":"delta","text": smalltalk_reply(user_msg)}) + "\n"
            payload = {"count": 0, "threshold": HANDOFF_THRESHOLD, "cooldown_sec": HANDOFF_COOLDOWN_SEC, "suggest": False}
            yield json.dumps({"type":"handoff","payload": payload}) + "\n"
            yield json.dumps({"type":"done"}) + "\n"
        resp = StreamingHttpResponse(_guard_stream(_greet_gen()), content_type="application/x-ndjson; charset=utf-8")
        resp["Cache-Control"] = "no-cache, no-transform"
        resp["X-Accel-Buffering"] = "no"
        return resp

    # 意圖攔截
    intent = detect_intent(user_msg)
    if intent == "activity_plan":
        def _plan_gen():
            yield json.dumps({"type":"meta","sources": []}) + "\n"
            text = generate_activity_plan()
            text = _force_linebreaks(text)
            text = _strip_source_section(text)
            yield json.dumps({"type":"delta","text": text}) + "\n"
            payload = {"count": 0, "threshold": HANDOFF_THRESHOLD, "cooldown_sec": HANDOFF_COOLDOWN_SEC, "suggest": False}
            yield json.dumps({"type":"handoff","payload": payload}) + "\n"
            yield json.dumps({"type":"done"}) + "\n"
        resp = StreamingHttpResponse(_guard_stream(_plan_gen()), content_type="application/x-ndjson; charset=utf-8")
        resp["Cache-Control"] = "no-cache, no-transform"
        resp["X-Accel-Buffering"] = "no"
        return resp

    # RAG 檢索 - 添加快速失敗機制
    try:
        context, sources = safe_retrieve(user_msg)
    except Exception as e:
        print(f"[api_chat_stream] 檢索系統錯誤，使用預設回應: {e}")
        context, sources = "", []

    if not context:
        # 嘗試使用fallback回應
        fallback_response = generate_fallback_response(user_msg)

        def _nohit_gen():
            yield json.dumps({"type":"meta","sources": []}) + "\n"
            if fallback_response:
                yield json.dumps({"type":"delta","text": fallback_response}) + "\n"
                # 不記失敗，因為有提供實用回應
                _, handoff_meta = _update_handoff_state(request, failed=False)
            else:
                yield json.dumps({"type":"delta","text":"目前知識庫沒有找到相關資訊，建議您點選【轉人工客服】進一步協助。"}) + "\n"
                # 記一次失敗
                _, handoff_meta = _update_handoff_state(request, failed=True)
            yield json.dumps({"type":"handoff","payload": handoff_meta}) + "\n"
            yield json.dumps({"type":"done"}) + "\n"

        resp = StreamingHttpResponse(_guard_stream(_nohit_gen()), content_type="application/x-ndjson; charset=utf-8")
        resp["Cache-Control"] = "no-cache, no-transform"
        resp["X-Accel-Buffering"] = "no"
        return resp

    opening = "根據提供的知識片段，"
    user_block = (
        f"{opening}請回答下列問題。\n\n"
        f"【站內知識】\n{context}\n\n"
        f"【使用者問題】{user_msg}"
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_block}]
    for h in history[-6:]:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.insert(1, h)

    def _generator():
        debug = bool((data or {}).get("debug"))
        # 把 sources 先丟到前端（依環境開關/除錯開關）
        yield json.dumps({"type":"meta","sources": (sources if (SHOW_SOURCES_TO_USER or debug) else [])}) + "\n"

        full_text = []
        in_source_block = False  # 串流即時過濾「來源」區塊
        for raw in chat_with_ollama_stream(messages):
            try:
                piece = json.loads(raw)
            except Exception:
                # 非 JSON（保險）—直接略過或照舊轉發？
                continue

            if piece.get("type") == "delta":
                txt = piece.get("text") or ""
                # 觸發來源段落開始？
                if _SOURCE_LINE_PAT.match(txt.strip()) or txt.strip() in ("來源", "參考來源", "資料來源"):
                    in_source_block = True
                    continue
                # 若正在來源段落中，直到遇到空行才恢復
                if in_source_block:
                    if not txt.strip():
                        in_source_block = False
                    continue

                # 正常輸出 delta
                full_text.append(txt)
                yield json.dumps({"type":"delta","text": txt}) + "\n"

            elif piece.get("type") in ("error", "done"):
                # 直接轉發
                yield raw

        # 串流結束後做換行與 handoff 事件（僅用於計算與整潔，不補發內容）
        merged = normalize_zh_tw("".join(full_text))
        merged = _force_linebreaks(merged)
        merged = _strip_source_section(merged)

        _, handoff_meta = _update_handoff_state(request, failed=False)
        yield json.dumps({"type":"handoff","payload": handoff_meta}) + "\n"
        yield json.dumps({"type":"done"}) + "\n"

    resp = StreamingHttpResponse(
        _guard_stream(_generator()),
        content_type="application/x-ndjson; charset=utf-8"
    )
    # 代理/瀏覽器友善：盡可能避免緩衝與轉碼
    resp["Cache-Control"] = "no-cache, no-transform"
    resp["X-Accel-Buffering"] = "no"  # Nginx：關閉代理端緩衝，SSE/串流更穩
    # ⚠️ 不要設定 Connection（WSGI 不允許 hop-by-hop header）
    return resp

# ====== 知識庫健康檢查：/api/chat/kb_status ======
@csrf_exempt
def api_kb_status(request):
    info = {
        "chromadb_loaded": bool(chromadb),
        "embedder_loaded": bool(_embedder),
        "db_dir": DB_DIR,
        "collection": COLLECTION_NAME,
        "count": None,
        "error": None,
    }
    try:
        if not chromadb or not Settings:
            info["error"] = "chromadb not available"
            return JsonResponse(info)

        if _embedder is None:
            info["error"] = "embedder not loaded (BAAI/bge-small-zh-v1.5)"
            return JsonResponse(info)

        client = chromadb.PersistentClient(path=DB_DIR, settings=Settings(anonymized_telemetry=False))
        try:
            col = client.get_or_create_collection(COLLECTION_NAME)
        except Exception:
            col = client.get_or_create_collection(COLLECTION_NAME)

        # 煙霧測試
        try:
            q = col.query(query_texts=["test"], n_results=1, include=["metadatas", "documents"])
            info["count"] = len((q or {}).get("documents", [[]])[0] or [])
        except Exception as e:
            info["error"] = f"query error: {e}"
    except Exception as e:
        info["error"] = str(e)

    return JsonResponse(info)

# ====== 清除快取端點：/api/chat/clear_cache ======
@csrf_exempt
def api_clear_cache(request):
    clear_cache()
    return JsonResponse({"status": "cache cleared"})