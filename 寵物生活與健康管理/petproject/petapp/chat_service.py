# petapp/chat_service.py
# -*- coding: utf-8 -*-
import os, re, json, requests, traceback
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# ====== 配置參數 ======
# AI 服務配置
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b-instruct")  # 統一使用 1.5b 模型（輕量快速）
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "120"))  # 虛擬機環境增加至120秒
AI_SERVICE_MODE = os.getenv("AI_SERVICE_MODE", "ollama")  # 新增：auto/ollama/fallback/hybrid

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
        _embedder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")  # 自動配置  

        print(f"[AI客服] 初始化成功，資料庫共有 {_collection.count()} 筆資料")
        return True

    except Exception as e:
        print(f"[AI客服] 初始化失敗: {e}")
        return False

def exact_text_search(query):
    """智能文本匹配搜索 - 改進版（返回最佳匹配）"""
    if not init_vector_search():
        return None

    try:
        # 獲取所有數據進行智能匹配
        all_data = _collection.get(include=['documents', 'metadatas'])

        # 清理查詢文本 - 移除標點符號和停用詞
        import re
        query_clean = re.sub(r'[？?！!。，,、\s]', '', query.lower())

        candidates = []  # 存儲候選匹配

        for doc, meta in zip(all_data['documents'], all_data['metadatas']):
            title = meta.get('title', '')
            title_clean = re.sub(r'[？?！!。，,、\s]', '', title.lower())

            # 計算相似度：檢查關鍵詞重疊
            query_chars = set(query_clean)
            title_chars = set(title_clean)

            # 多種匹配策略
            overlap = len(query_chars & title_chars)
            similarity = overlap / max(len(query_chars), len(title_chars)) if max(len(query_chars), len(title_chars)) > 0 else 0

            # 關鍵詞匹配 - 檢查是否包含核心詞彙
            query_words = [query_clean[i:i+2] for i in range(len(query_clean)-1)]  # 提取所有2字詞
            title_words = [title_clean[i:i+2] for i in range(len(title_clean)-1)]

            common_words = set(query_words) & set(title_words)
            word_match_score = len(common_words)

            # 增強語義衝突檢測 - 避免錯誤匹配
            semantic_conflict = False
            severe_conflict = False

            # 嚴重衝突：完全不相關的主題
            severe_conflict_pairs = [
                ('受傷', '排泄'), ('受傷', '嘔吐'), ('受傷', '記仇'), ('受傷', '外出'),
                ('意外', '預防'), ('緊急', '日常'), ('處理受傷', '處理排泄'),
                ('外傷', '大小便'), ('傷口', '廁所'), ('急救', '訓練'),
                ('醫療', '玩具'), ('治療', '食物'), ('包紮', '清潔'),
                ('流血', '嘔吐'), ('骨折', '腹瀉'),
                ('指甲', '洗澡'), ('修剪', '沐浴'), ('剪指甲', '洗澡'),
                ('指甲修剪', '洗澡頻率'), ('指甲護理', '清潔身體'),

                # 新增關鍵衝突對 - 根據用戶回報的錯誤
                ('走失', '輸血'), ('不見', '醫療'), ('外面', '外傷'), ('丟失', '治療'),
                ('用品', '如廁'), ('選擇', '定點'), ('適合', '清潔'), ('商品', '訓練'),
                ('睡覺', '過敏'), ('休息', '皮膚病'), ('昏睡', '寄生蟲'),
                ('洗澡', '記仇'), ('沐浴', '記憶'), ('吹乾', '經驗'), ('清潔', '避免'),
                ('血液', '尋找'), ('配對', '協尋'), ('輸血', '走失'), ('醫院', '收容所'),
                ('獎勵', '寵物用品'), ('制度', '選擇用品'), ('建立', '適合用品'),
                ('絕育', '皮膚病'), ('結紮', '腸胃炎'), ('時機', '牙周病'), ('手術', '關節炎'),
                ('最佳', '疾病'), ('絕育時機', '慢性病'), ('結紮時間', '老化疾病'),
                ('領養', '食器'), ('條件', '水碗'), ('需要', '寵物床'), ('申請', '籠子'),
                ('領養條件', '用品'), ('領養需要', '食具'), ('申請領養', '玩具')
            ]

            # 一般衝突：相關但不同的概念
            general_conflict_pairs = [
                ('居家', '外出'), ('室內', '戶外'), ('家具', '食物'),
                ('訓練', '醫療'), ('玩耍', '治療'), ('健康', '生病')
            ]

            # 檢查嚴重衝突
            for pair in severe_conflict_pairs:
                if (pair[0] in query_clean and pair[1] in title_clean) or (pair[1] in query_clean and pair[0] in title_clean):
                    severe_conflict = True
                    break

            # 檢查一般衝突
            if not severe_conflict:
                for pair in general_conflict_pairs:
                    if (pair[0] in query_clean and pair[1] in title_clean) or (pair[1] in query_clean and pair[0] in title_clean):
                        semantic_conflict = True
                        break

            # 衝突懲罰：嚴重衝突幾乎排除，一般衝突降低評分
            if severe_conflict:
                conflict_penalty = 0.05  # 幾乎排除
            elif semantic_conflict:
                conflict_penalty = 0.3   # 大幅降低
            else:
                conflict_penalty = 1.0

            # 增強正向語義加權 - 專題特定關鍵詞匹配
            positive_boost = 1.0
            topic_specific_keywords = {
                # 受傷相關
                '受傷': ['外傷', '傷口', '急救', '醫療', '處理', '治療', '包紮', '流血', '骨折', '扭傷'],
                '意外': ['緊急', '急救', '處理', '怎麼辦', '立即', '馬上', '快速'],
                '緊急': ['立即', '馬上', '急救', '處理', '送醫', '就醫'],

                # 健康相關
                '嘔吐': ['腹瀉', '生病', '症狀', '醫療', '不適', '食慾'],
                '腹瀉': ['嘔吐', '生病', '症狀', '醫療', '水便', '軟便'],

                # 日常照護
                '訓練': ['行為', '教導', '學習', '指令', '服從', '練習'],
                '指甲': ['修剪', '剪指甲', '護理', '血線', '止血', '過長', '喀喀聲'],
                '修剪': ['指甲', '剪', '血線', '止血粉', '過長', '卡到'],
                '洗澡': ['沐浴', '清潔', '洗髮精', '沐浴乳', '頻率', '皮膚'],
                '清潔': ['洗澡', '梳毛', '衛生', '護理', '美容'],
                '餵食': ['食物', '飼料', '營養', '吃飯', '進食'],

                # 行為問題
                '咬': ['家具', '鞋子', '東西', '玩具', '無聊', '長牙', '焦慮', '替代物'],
                '護食': ['資源', '保護', '本能', '信任', '訓練', '口令'],
                '撲人': ['打招呼', '注意', '轉身', '忽視', '四腳著地'],

                # 醫療健康
                '獸醫': ['醫院', '預約', '服務', '選擇', '醫師', '經驗', '評價', '信任'],
                '疫苗': ['預防針', '注射', '接種', '免疫', '保護', '定期', '健康'],
                '生病': ['症狀', '治療', '醫療', '就醫', '診斷', '藥物', '康復'],
                '健康': ['檢查', '預防', '保健', '營養', '運動', '照護', '管理'],

                # 緊急醫療
                '中毒': ['症狀', '急救', '中毒', '治療', '緊急', '就醫', '毒物'],
                '急救': ['緊急', '處理', '受傷', '中毒', '立即', '急救', '送醫'],
                '受傷': ['外傷', '傷口', '急救', '處理', '緊急', '醫療', '治療'],
                '緊急': ['急救', '立即', '馬上', '處理', '送醫', '危險', '嚴重'],

                # 年齡和飲食
                '幼': ['幼犬', '幼貓', '小狗', '小貓', '年輕', '成長', '發育'],

                # 新增用戶回報問題的關鍵主題
                '走失': ['不見', '丟失', '外面', '尋找', '協尋', '收容所', '警察', '晶片', '名牌'],
                '用品': ['選擇', '適合', '食器', '水碗', '寵物床', '籠子', '玩具', '用具', '設備'],
                '睡覺': ['休息', '昏睡', '嗜睡', '疲倦', '精神', '活力', '正常', '作息'],
                '洗澡完': ['吹乾', '烘乾', '毛髮', '濕氣', '黴菌', '細菌', '長毛'],
                '絕育': ['結紮', '時機', '手術', '年齡', '性成熟', '健康', '獸醫', '最佳'],
                '領養': ['條件', '申請', '資格', '收入', '住家', '經驗', '責任', '承諾'],
                '老': ['老年', '老犬', '老貓', '高齡', '年紀', '衰老', '照護'],
                '飲食': ['餵食', '食物', '營養', '吃', '餵', '飼料', '食慾'],
                '餵食': ['飲食', '食物', '營養', '頻率', '時間', '份量', '方法'],

                # 其他重要
                '領養': ['收養', '認養', '選擇', '條件', '準備', '責任', '愛心'],
                '絕育': ['結紮', '手術', '時機', '好處', '風險', '年齡', '健康'],

                # 環境相關
                '居家': ['家具', '安全', '環境', '注意', '室內', '防護'],
                '外出': ['散步', '運動', '戶外', '遛狗', '活動']
            }

            # 計算主題匹配度
            topic_match_boost = 1.0
            for key, related_words in topic_specific_keywords.items():
                if key in query_clean:
                    match_count = sum(1 for word in related_words if word in title_clean)
                    if match_count >= 2:
                        topic_match_boost = 2.0  # 強匹配
                        break
                    elif match_count == 1:
                        topic_match_boost = 1.5  # 中等匹配

            positive_boost = topic_match_boost

            # 綜合評分：基礎匹配 * 衝突懲罰 * 主題加權
            base_score = similarity * 0.4 + (word_match_score / max(len(query_words), len(title_words))) * 0.6
            total_score = base_score * conflict_penalty * positive_boost

            # 嚴格的匹配條件：確保質量
            should_include = False

            # 條件1：高相似度且無嚴重衝突
            if similarity > 0.7 and not severe_conflict:
                should_include = True

            # 條件2：完全包含關係且高詞匹配
            elif (query_clean in title_clean or title_clean in query_clean) and word_match_score >= 2 and not severe_conflict:
                should_include = True

            # 條件3：主題特定高匹配
            elif word_match_score >= 4 and positive_boost >= 1.5 and not severe_conflict:
                should_include = True

            # 條件4：受傷相關的特殊處理
            elif ('受傷' in query_clean or '意外' in query_clean or '緊急' in query_clean):
                injury_keywords_in_title = sum(1 for keyword in ['受傷', '外傷', '傷口', '急救', '醫療', '處理', '治療'] if keyword in title_clean)
                if injury_keywords_in_title >= 2 and not severe_conflict:
                    should_include = True

            # 條件5：行為問題的特殊處理（如護食、撲人、咬人等）
            elif any(behavior in query_clean for behavior in ['護食', '撲人', '咬人', '亂叫', '亂抓', '亂尿', '咬']):
                behavior_match = False

                # 精確行為匹配
                exact_behaviors = ['護食', '撲人', '咬人', '亂叫', '亂抓', '亂尿']
                for behavior in exact_behaviors:
                    if behavior in query_clean and behavior in title_clean:
                        behavior_match = True
                        break

                # 特殊處理：咬東西的行為
                if '咬' in query_clean and ('咬' in title_clean or '咬東西' in title_clean or '咬家具' in title_clean):
                    # 檢查是否包含具體物品
                    items = ['鞋子', '家具', '東西', '玩具', '沙發', '椅子']
                    for item in items:
                        if item in query_clean and (item in title_clean or '家具' in title_clean or '東西' in title_clean):
                            behavior_match = True
                            break

                if behavior_match and not severe_conflict:
                    should_include = True

            # 條件6：複合關鍵詞特殊匹配（跨主題查詢）
            elif any(combo in query_clean for combo in ['差異', '不同', '比較']):
                # 年齡相關飲食差異
                if ('幼' in query_clean or '老' in query_clean) and ('飲食' in query_clean or '餵食' in query_clean):
                    age_diet_keywords = ['老年', '幼', '飲食', '餵食', '營養', '調整']
                    age_diet_count = sum(1 for keyword in age_diet_keywords if keyword in title_clean)
                    if age_diet_count >= 2 and not severe_conflict:
                        should_include = True

            # 條件7：核心關鍵詞的部分匹配（針對簡短查詢）
            elif len(query_clean) <= 6:  # 簡短查詢
                # 首先檢查單字關鍵詞（最嚴格匹配）
                if len(query_clean) <= 3:  # 單字查詢
                    single_word_keywords = ['獸醫', '醫院', '疫苗', '領養', '訓練', '洗澡']
                    for keyword in single_word_keywords:
                        if keyword == query_clean and keyword in title_clean and not severe_conflict:
                            # 單字匹配直接通過
                            should_include = True
                            break

                # 如果單字匹配失敗，嘗試核心關鍵詞匹配
                if not should_include:
                    core_keywords = [
                        # 行為問題
                        '護食', '撲人', '咬人', '記仇', '咬',
                        # 護理照護
                        '洗澡', '指甲', '訓練', '餵食', '飲食',
                        # 醫療健康
                        '嘔吐', '腹瀉', '獸醫', '醫院', '疫苗', '生病', '健康',
                        # 緊急情況
                        '中毒', '急救', '受傷', '緊急', '意外',
                        # 年齡相關
                        '幼', '老', '幼犬', '老年',
                        # 其他重要
                        '領養', '絕育'
                    ]
                    for keyword in core_keywords:
                        if keyword in query_clean and keyword in title_clean and not severe_conflict:
                            # 簡短查詢降低門檻
                            if word_match_score >= 2 or similarity > 0.4:
                                should_include = True
                                break

            if should_include:
                candidates.append({
                    'doc': doc,
                    'title': title,
                    'score': total_score,
                    'similarity': similarity,
                    'common_words': word_match_score,
                    'conflict_penalty': conflict_penalty,
                    'positive_boost': positive_boost,
                    'severe_conflict': severe_conflict
                })

        # 如果有候選者，選擇最佳匹配
        if candidates:
            # 按評分排序，優先選擇無嚴重衝突的結果
            candidates.sort(key=lambda x: (not x['severe_conflict'], x['score']), reverse=True)
            best_match = candidates[0]

            # 動態調整質量門檻（針對簡短查詢）
            query_length = len(re.sub(r'[？?！!。，,、\s]', '', query.lower()))
            if query_length <= 6:  # 簡短查詢
                min_score = 0.6 if best_match['severe_conflict'] else 0.4
            else:
                min_score = 0.8 if best_match['severe_conflict'] else 0.6

            if best_match['score'] >= min_score:
                print(f"[AI客服] 智能匹配找到最佳結果")
                print(f"  評分: {best_match['score']:.3f}, 相似度: {best_match['similarity']:.3f}")
                print(f"  共同詞: {best_match['common_words']}, 衝突懲罰: {best_match['conflict_penalty']}")
                print(f"  主題加權: {best_match['positive_boost']}, 嚴重衝突: {best_match['severe_conflict']}")
                print(f"  標題: {best_match['title']}")
                # 清理回答格式，移除問題前綴
                cleaned_answer = clean_response_format(best_match['doc'])
                return cleaned_answer
            else:
                print(f"[AI客服] 智能匹配質量不足 (評分: {best_match['score']:.3f} < {min_score})")
                # 顯示前3個候選結果供調試
                for i, candidate in enumerate(candidates[:3]):
                    title_preview = candidate['title'][:20] if len(candidate['title']) > 20 else candidate['title']
                    print(f"  候選{i+1}: 評分{candidate['score']:.3f}, 衝突: {candidate['severe_conflict']}, 標題: {title_preview}")

                # 對於特定查詢類型，降低門檻
                query_length = len(re.sub(r'[？?！!。，,、\s]', '', query.lower()))

                # 單字查詢降低門檻
                if query_length <= 3 and not best_match['severe_conflict'] and best_match['score'] > 0.2:
                    print(f"[AI客服] 單字查詢降低門檻，接受候選答案")
                    cleaned_answer = clean_response_format(best_match['doc'])
                    return cleaned_answer

                # 複合查詢（如差異、比較）降低門檻
                if any(combo in query for combo in ['差異', '不同', '比較']) and best_match['score'] > 0.25:
                    print(f"[AI客服] 複合查詢降低門檻，接受候選答案")
                    cleaned_answer = clean_response_format(best_match['doc'])
                    return cleaned_answer

                print(f"[AI客服] 使用向量搜索")

        return None
    except Exception as e:
        print(f"[AI客服] 智能匹配搜索錯誤: {e}")
        return None

def clean_response_format(response):
    """清理回答格式，讓回答更自然"""
    if not response:
        return response

    import re

    # 移除常見的問題前綴格式
    patterns_to_remove = [
        r'^問題：.*?\n\n',  # 移除 "問題：xxx" 開頭
        r'^問題：.*?\n',   # 移除單行問題前綴
        r'^Q：.*?\n\n',    # 移除 "Q：xxx" 開頭
        r'^Q：.*?\n',      # 移除單行Q前綴
        r'^.*？\s*\n\n',   # 移除以問號結尾的問題行
    ]

    cleaned = response
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)

    # 移除 "回答：" 前綴
    cleaned = re.sub(r'^回答：', '', cleaned)
    cleaned = re.sub(r'^答：', '', cleaned)
    cleaned = re.sub(r'^A：', '', cleaned)

    # 清理多餘的空行
    cleaned = re.sub(r'\n\n+', '\n\n', cleaned)
    cleaned = cleaned.strip()

    return cleaned

def generate_natural_response(query, relevant_docs):
    """即使沒有Ollama也能生成自然回答的智能組合功能"""
    if not relevant_docs:
        return None

    # 取得最相關的文檔
    best_doc = relevant_docs[0]
    best_content = clean_response_format(best_doc['content'])

    # 如果只有一個高品質文檔，直接返回清理後的內容
    if len(relevant_docs) == 1 or best_doc['similarity'] > 0.85:
        return best_content

    # 多文檔智能組合
    print(f"[AI客服] 組合 {len(relevant_docs)} 個相關文檔生成回答")

    # 清理所有相關文檔
    cleaned_docs = []
    for doc in relevant_docs[:3]:  # 最多使用3個文檔
        cleaned = clean_response_format(doc['content'])
        if cleaned and len(cleaned) > 20:  # 過濾太短的內容
            cleaned_docs.append({
                'content': cleaned,
                'similarity': doc['similarity']
            })

    if not cleaned_docs:
        return best_content

    # 智能重組答案
    import re

    # 分析查詢類型來決定組合策略
    if any(keyword in query for keyword in ['如何', '怎麼', '方法', '步驟']):
        # 步驟類問題：組合建議
        combined_tips = []
        for doc in cleaned_docs:
            content = doc['content']
            # 提取建議和方法
            sentences = re.split(r'[。！？\n]', content)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10 and any(word in sentence for word in ['建議', '應該', '可以', '需要', '避免']):
                    if sentence not in combined_tips:
                        combined_tips.append(sentence)

        if combined_tips:
            return '。'.join(combined_tips[:3]) + '。'

    elif any(keyword in query for keyword in ['什麼', '哪些', '有什麼']):
        # 列舉類問題：提取關鍵點
        key_points = []
        for doc in cleaned_docs:
            content = doc['content']
            # 提取關鍵信息
            sentences = re.split(r'[。！？\n]', content)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 8 and sentence not in key_points:
                    key_points.append(sentence)

        if key_points:
            return '。'.join(key_points[:2]) + '。'

    elif any(keyword in query for keyword in ['可以', '能否', '會不會', '是否']):
        # 是非類問題：給出明確答案加解釋
        first_sentence = re.split(r'[。！？\n]', best_content)[0].strip()
        if first_sentence:
            # 如果有其他相關信息，補充說明
            if len(cleaned_docs) > 1:
                additional = re.split(r'[。！？\n]', cleaned_docs[1]['content'])[0].strip()
                if additional and additional != first_sentence:
                    return f"{first_sentence}。{additional}。"
            return f"{first_sentence}。"

    # 默認：返回最佳匹配的清理內容
    return best_content

def direct_text_search(query):
    """簡化的AI客服 - 優先使用RAG管道"""
    try:
        print(f"[AI客服] 處理查詢: {query}")

        # 1. 優先使用RAG管道（自然AI生成）
        rag_result = rag_search_and_generate(query)
        if rag_result:
            return rag_result

        # 2. 備用：基礎向量搜索
        print(f"[AI客服] RAG失敗，使用備用搜索...")
        search_results = simple_search(query, top_k=3)

        if search_results and len(search_results) > 0:
            # 返回最相關的文檔
            best_result = search_results[0]
            if best_result['similarity'] > 0.4:
                print(f"[AI客服] 使用備用答案，相似度: {best_result['similarity']}")
                return best_result['content']

        print(f"[AI客服] 所有方法都失敗")
        return None

    except Exception as e:
        print(f"[AI客服] 處理錯誤: {e}")
        return None

def generate_intelligent_response(query, relevant_docs):
    """使用Ollama生成智能回答"""
    try:
        import requests

        # 構建上下文
        context_parts = []
        for i, doc in enumerate(relevant_docs[:3]):  # 最多使用3個文檔
            context_parts.append(f"參考資料{i+1}：{doc['content']}")

        context = "\n\n".join(context_parts)

        # 構建prompt
        prompt = f"""你是一個專業的寵物照護客服助理。請根據以下參考資料回答用戶問題。

參考資料：
{context}

用戶問題：{query}

請用繁體中文回答，要求：
1. 基於參考資料提供準確答案
2. 如果參考資料不足以回答問題，請誠實說明
3. 保持友善和專業的語調
4. 回答要簡潔明確

回答："""

        # 調用Ollama API
        ollama_response = requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                'model': OLLAMA_MODEL,
                'prompt': prompt,
                'stream': False
            },
            timeout=OLLAMA_TIMEOUT_SEC
        )

        if ollama_response.status_code == 200:
            response_data = ollama_response.json()
            answer = response_data.get('response', '').strip()

            if answer:
                print(f"[AI客服] Ollama智能生成成功")
                return answer
            else:
                print(f"[AI客服] Ollama返回空答案")
                # 備用：返回最相關的文檔
                return relevant_docs[0]['content']
        else:
            print(f"[AI客服] Ollama API錯誤: {ollama_response.status_code}")
            # 備用：返回最相關的文檔
            return relevant_docs[0]['content']

    except requests.exceptions.Timeout:
        print(f"[AI客服] Ollama連接超時(>{OLLAMA_TIMEOUT_SEC}秒)，返回None讓上級函數處理")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[AI客服] 無法連接到Ollama服務 ({OLLAMA_CHAT_URL})，返回None讓上級函數處理")
        return None
    except Exception as e:
        print(f"[AI客服] Ollama生成錯誤: {e}，返回None讓上級函數處理")
        return None

def simple_search(query, top_k=5):
    """優化版chroma_db向量檢索"""
    if not init_vector_search():
        return []

    try:
        # 執行檢索，增加檢索數量以提高準確性
        results = _collection.query(
            query_texts=[query],
            n_results=top_k * 2,  # 檢索更多結果再篩選
            include=["documents", "metadatas", "distances"]
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # 處理結果
        matched_docs = []
        for doc, meta, dist in zip(docs, metas, distances):
            distance = abs(float(dist))
            source = meta.get('source', '')

            # 改進的相似度計算
            if distance <= 0.6:
                base_similarity = 1.0 - distance  # 高相似度
            elif distance <= 1.0:
                base_similarity = 0.7 - (distance - 0.6) * 0.5  # 中等相似度
            elif distance <= 1.5:
                base_similarity = 0.5 - (distance - 1.0) * 0.4  # 低相似度
            else:
                base_similarity = max(0.1, 0.3 - (distance - 1.5) * 0.2)  # 很低相似度

            # 移除不合理的數據來源加權，保持原始相似度
            final_similarity = base_similarity

            # 僅用於標記數據類型
            if 'platform_manual' in source:
                data_type = 'platform'
            elif 'faq' in source or 'qa' in source:
                data_type = 'qa'
            else:
                data_type = 'other'

            # 提高質量門檻
            min_threshold = 0.2

            if final_similarity > min_threshold:
                matched_docs.append({
                    'content': doc,
                    'title': meta.get('title', '寵物知識'),
                    'similarity': final_similarity,
                    'source': source,
                    'id': meta.get('id', ''),
                    'original_distance': distance,
                    'data_type': data_type
                })

        # 按數據類型和相似度排序
        matched_docs.sort(key=lambda x: (x['data_type'] == 'platform', x['data_type'] == 'qa', x['similarity']), reverse=True)

        # 調試信息
        print(f"[AI客服] chroma_db檢索到 {len(matched_docs)} 筆相關資料")
        for i, doc in enumerate(matched_docs[:3]):
            print(f"  {i+1}. 類型: {doc['data_type']}, 相似度: {doc['similarity']:.3f}, 距離: {doc['original_distance']:.3f}")

        return matched_docs[:top_k]

    except Exception as e:
        print(f"[AI客服] chroma_db檢索錯誤: {e}")
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

# 移除不再使用的AI模式相關函數，簡化系統架構

def fallback_response(question):
    """強化版回退回答方案（無需AI模型的智能匹配）"""

    # 優先匹配系統功能問題（更精確的模式）
    system_keywords = {
        "毛日好.*功能|毛日好.*平台|毛日好.*系統|毛日好.*介紹|這個.*平台.*功能|平台.*有什麼.*功能|系統.*功能|網站.*功能": "🏠 毛日好寵物生活管理平台\n\n主要功能：\n• 寵物檔案管理\n• 健康記錄追蹤\n• 獸醫預約服務\n• 領養資訊平台\n• AI智能客服\n\n如需詳細操作說明，歡迎繼續提問！",

        "註冊|如何註冊|建立帳號|加入會員": "📝 毛日好註冊步驟\n\n1. 點擊右上角「註冊」按鈕\n2. 填寫基本資料（姓名、Email、密碼）\n3. 點擊「註冊」完成\n4. 至信箱確認Email驗證\n5. 登入開始使用\n\n💡 也可使用Google帳號一鍵註冊！",

        "登入|如何登入|無法登入|忘記密碼": "🔑 登入相關說明\n\n登入方式：\n1. Email + 密碼登入\n2. Google帳號登入\n\n忘記密碼：\n1. 點擊「忘記密碼？」\n2. 輸入註冊Email\n3. 至信箱點擊重設連結\n4. 設定新密碼\n\n如仍有問題，請聯繫客服協助。",

        "新增寵物|新增.*寵物|寵物.*新增|寵物.*資料|添加寵物|加入寵物": "🐾 新增寵物資料步驟\n\n1. 登入毛日好平台\n2. 進入「我的毛孩們」頁面\n3. 點擊「新增寵物」或「+」按鈕\n4. 填寫寵物基本資料：\n   • 寵物名稱\n   • 種類（狗/貓/其他）\n   • 品種\n   • 性別\n   • 出生日期\n   • 體重\n5. 上傳寵物照片（可選）\n6. 點擊「儲存」完成新增\n\n📝 建議填寫完整資料以便管理！",

        "編輯寵物|修改寵物|更新寵物|寵物.*編輯|寵物.*修改": "✏️ 編輯寵物資料步驟\n\n1. 進入「我的毛孩們」頁面\n2. 找到要編輯的寵物\n3. 點擊寵物卡片的「設定」按鈕\n4. 選擇「編輯資料」\n5. 修改需要的資訊\n6. 點擊「儲存」保存變更\n\n💡 隨時更新寵物資料有助健康管理！",

        "刪除寵物|移除寵物|寵物.*刪除|寵物.*移除": "🗑️ 刪除寵物資料步驟\n\n1. 進入「我的毛孩們」頁面\n2. 找到要刪除的寵物\n3. 點擊寵物卡片的「設定」按鈕\n4. 選擇「刪除寵物」\n5. 確認刪除操作\n\n⚠️ 刪除後資料無法復原，請謹慎操作！",

        "健康記錄|健康.*記錄|記錄.*健康|寵物.*健康": "📋 寵物健康記錄管理\n\n1. 選擇寵物後點擊「健康記錄」\n2. 可記錄的項目：\n   • 體重記錄\n   • 體溫記錄\n   • 疫苗接種\n   • 驅蟲記錄\n   • 醫療記錄\n   • 日常生活記錄\n3. 點擊對應項目進行新增\n4. 填寫詳細資訊並儲存\n\n📊 定期記錄有助追蹤寵物健康狀況！"
    }

    # 寵物照護核心知識庫
    pet_care_keywords = {
        "餵食|食物|飼料|營養|吃|餵|餓|食慾": "🍽️ 寵物餵食指南\n\n基本原則：\n• 定時定量餵食\n• 選擇適齡專用飼料\n• 保持充足飲水\n• 避免人類食物\n\n餵食時間建議：\n• 幼齡：一日3-4餐\n• 成年：一日2餐\n• 老年：少量多餐\n\n⚠️ 巧克力、洋蔥、葡萄等對寵物有毒！",

        "健康|生病|疾病|症狀|不舒服|檢查|醫療": "🏥 寵物健康管理\n\n預防保健：\n• 定期健康檢查（年輕寵物1年1次，老年寵物6個月1次）\n• 按時接種疫苗\n• 定期驅蟲\n• 維持環境清潔\n\n緊急症狀須立即就醫：\n• 嘔吐、腹瀉持續\n• 食慾不振超過24小時\n• 呼吸困難\n• 行動異常\n\n💡 使用毛日好預約功能找到附近獸醫院！",

        "訓練|行為|吠叫|咬|亂叫|教|學習|服從": "🎓 寵物行為訓練\n\n基本訓練原則：\n• 正向鼓勵勝於懲罰\n• 保持指令一致性\n• 耐心重複練習\n• 適時給予獎勵\n\n常見問題處理：\n• 亂吠：轉移注意力，不要大聲制止\n• 咬東西：提供適當玩具\n• 不聽話：建立明確規則\n\n🐕 幼犬黃金訓練期：3-14週齡",

        "洗澡|清潔|衛生|梳毛|護理|美容|毛髮|指甲": "🛁 寵物清潔護理\n\n洗澡頻率：\n• 狗：1-2週一次\n• 貓：自行清潔，特殊情況才洗\n• 水溫：37-38°C\n\n日常護理：\n• 每日梳毛（長毛品種需更頻繁）\n• 清潔牙齒（2-3天一次）\n• 清理耳朵（週檢查）\n• 修剪指甲（2-3週一次）\n\n🧴 使用寵物專用清潔用品！",

        "體重|紀錄|記錄|重量|胖|瘦": "⚖️ 寵物體重管理\n\n記錄方法：\n• 固定時間測量（建議早餐前）\n• 使用精準秤具\n• 記錄在毛日好健康紀錄\n• 觀察體態變化\n\n理想體重判斷：\n• 可摸到但不明顯看到肋骨\n• 腰部有明顯收縮\n• 從上方看呈沙漏型\n\n📊 體重管理幫助預防疾病！",

        "運動|散步|活動|玩|精力|累": "🏃 寵物運動需求\n\n運動重要性：\n• 維持健康體重\n• 促進心血管健康\n• 消耗多餘精力\n• 增進親密關係\n\n運動建議：\n• 小型犬：每日30分鐘\n• 中型犬：每日60分鐘\n• 大型犬：每日90分鐘以上\n• 貓咪：室內遊戲15-20分鐘×2-3次\n\n🌡️ 炎熱天氣避免中午時段運動！",


        "疫苗|預防針|接種|免疫": "💉 寵物疫苗接種\n\n核心疫苗（必須）：\n狗：狂犬病、犬瘟熱、腺病毒、小病毒\n貓：狂犬病、貓瘟、卡里西病毒、疱疹病毒\n\n接種時程：\n• 首次：6-8週齡開始\n• 補強：間隔2-4週\n• 年度補強：依獸醫建議\n\n📅 使用毛日好記錄疫苗時程，不錯過重要接種！",

        "懷孕|生產|繁殖|配種|生小孩": "🤱 寵物繁殖須知\n\n懷孕期照護：\n• 狗：懷孕期約63天\n• 貓：懷孕期約65天\n• 增加營養攝取\n• 減少激烈運動\n• 定期產檢\n\n生產準備：\n• 準備舒適生產環境\n• 備妥緊急聯絡獸醫\n• 觀察生產徵兆\n\n⚠️ 建議在專業獸醫指導下進行！"
    }

    # 季節性照護建議
    seasonal_keywords = {
        "夏天|熱|中暑|降溫": "☀️ 夏季寵物照護\n\n防中暑措施：\n• 提供充足陰涼處\n• 隨時準備新鮮水源\n• 避免中午外出\n• 可準備降溫墊\n• 注意室內通風\n\n中暑症狀：喘氣、流口水、體溫過高\n🚨 發現中暑立即就醫！",

        "冬天|冷|保暖|禦寒": "❄️ 冬季寵物照護\n\n保暖措施：\n• 提供溫暖睡窩\n• 短毛品種可穿衣物\n• 減少洗澡頻率\n• 注意室內溫度\n• 增加熱量攝取\n\n🧥 選擇透氣、合身的寵物衣物！"
    }

    # 緊急情況處理
    emergency_keywords = {
        "嘔吐.*腹瀉|腹瀉.*嘔吐|嘔吐.*處理|腹瀉.*處理|拉肚子|吐|嘔": "🚨 寵物嘔吐腹瀉處理\n\n**立即就醫情況：**\n• 持續嘔吐超過24小時\n• 嚴重腹瀉伴隨血絲\n• 同時出現嘔吐和腹瀉\n• 精神萎靡、不吃不喝\n• 脫水症狀(牙齦乾燥、皮膚失去彈性)\n\n**緊急處理：**\n1. 暫停餵食12-24小時\n2. 提供少量清水\n3. 觀察症狀變化\n4. 記錄嘔吐腹瀉次數\n5. 儘速就醫\n\n⚠️ 幼犬幼貓更需要立即就醫！",

        "中毒|吃壞|誤食|急救": "🚨 緊急狀況處理\n\n立即就醫徵象：\n• 持續嘔吐或腹瀉\n• 誤食有毒物質\n• 呼吸困難\n• 意識不清\n• 大量出血\n\n急救措施：\n1. 保持冷靜\n2. 立即聯絡獸醫\n3. 依指示進行初步處理\n4. 儘速送醫\n\n☎️ 建議預存24小時急診獸醫電話！"
    }

    # 按優先級檢查所有關鍵字庫
    all_keywords = [system_keywords, emergency_keywords, pet_care_keywords, seasonal_keywords]

    for keyword_dict in all_keywords:
        for pattern, response in keyword_dict.items():
            if re.search(pattern, question, re.IGNORECASE):
                return response

    # 如果沒有匹配到，提供通用建議
    return "🤖 毛日好AI客服\n\n很抱歉，我無法理解您的問題。\n\n您可以詢問：\n• 寵物餵食、健康、訓練\n• 平台功能使用\n• 註冊登入相關\n• 預約獸醫服務\n\n💬 或點擊下方【轉人工客服】獲得專人協助！"

def rag_search_and_generate(query, top_k=3):
    """簡化的RAG管道：參考RAGpipeline.py的方法"""
    if not init_vector_search():
        return None

    try:
        print(f"[RAG] 檢索查詢: {query}")

        # 1. 檢索相關文檔 - 參考RAGpipeline.py第20行
        results = _collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas"]
        )

        docs = results.get("documents", [[]])[0]
        if not docs:
            print(f"[RAG] 沒有找到相關文檔")
            return None

        # 2. 組合上下文 - 參考RAGpipeline.py第21行
        context = " ".join(docs)
        print(f"[RAG] 找到 {len(docs)} 個文檔，組合上下文")

        # 3. 建構提示詞 - 參考RAGpipeline.py第24行
        prompt = f"根據以下資料回答問題:\n\n{context}\n\n問題: {query}"

        # 4. 調用Ollama - 參考RAGpipeline.py第25行
        import ollama

        response = ollama.chat(
            model=OLLAMA_MODEL,  # 直接使用配置中的模型名稱
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response["message"]["content"].strip()

        if answer and len(answer) > 10:
            print(f"[RAG] 成功生成: {answer[:50]}...")
            return answer
        else:
            print(f"[RAG] 生成答案太短")
            return None

    except Exception as e:
        print(f"[RAG] 錯誤: {e}")
        return None

@csrf_exempt
@require_POST
def api_chat(request):
    """AI客服主要API"""
    try:
        # 解析請求
        try:
            body = request.body.decode('utf-8')
            data = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"[AI客服] 請求解析錯誤: {e}")
            return JsonResponse({"response": "請求格式錯誤"})

        user_question = data.get("message", "").strip()

        if not user_question:
            return JsonResponse({"response": "請輸入您的問題"})

        print(f"[AI客服] 收到問題: {user_question}")

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

            "預約.*獸醫|獸醫.*預約|預約.*門診|門診.*預約": "毛日好預約獸醫門診：\n1. 點擊「預約門診」功能\n2. 選擇獸醫院和醫師\n3. 挑選可預約時段\n4. 填寫就診資訊和聯絡方式\n5. 確認預約資訊並送出\n6. 獸醫院會確認預約時間",

            "如何瀏覽領養資訊|瀏覽領養資訊|領養資訊.*瀏覽": "🐾 領養資訊瀏覽\n\n1. 點擊「空心愛心領養」頁面\n2. 瀏覽可領養的寵物\n3. 使用篩選功能(品種、年齡、地區)\n4. 點擊寵物卡片查看詳細資訊\n5. 聯絡送養人或機構\n\n💡 也可以發佈送養資訊幫助寵物找到新家！",

            "如何.*送養|發佈.*送養|送養.*流程|我要送養": "📝 發佈送養資訊\n\n1. 進入「空心愛心領養」頁面\n2. 點擊「我要送養」\n3. 填寫寵物詳細資訊\n4. 上傳清晰照片\n5. 說明送養原因和要求\n6. 留下聯絡方式\n7. 提交審核\n\n💝 幫助毛孩找到溫暖的家！",

            "其他.*領養.*管道|領養.*管道|還有.*領養|其他.*領養.*途徑|領養.*途徑": "🏠 其他領養管道\n\n除了毛日好平台，您還可以透過：\n\n1. **官方收容所**\n   • 各縣市動物收容所\n   • 台灣動物緊急救援小組\n\n2. **民間救援組織**\n   • 流浪動物花園協會\n   • 台灣之心愛護動物協會\n   • 各地動物救援協會\n\n3. **社群平台**\n   • Facebook領養社團\n   • Instagram救援帳號\n\n4. **動物醫院**\n   • 部分獸醫院提供中途資訊\n\n⚠️ 無論透過何種管道，都要確認：\n• 寵物健康狀況\n• 疫苗接種記錄\n• 是否已絕育\n• 領養合約內容",

            "領養流程|領養.*步驟|如何領養": "📋 領養流程指南\n\n標準領養流程：\n1. 線上瀏覽寵物資訊\n2. 聯絡送養方表達意願\n3. 安排實地見面\n4. 填寫領養申請表\n5. 等待審核通過\n6. 簽署領養協議\n7. 完成領養手續\n\n💡 建議準備：\n• 身分證明文件\n• 居住證明\n• 家庭成員同意書\n• 經濟能力證明"
        }

        for pattern, response in priority_keywords.items():
            if re.search(pattern, user_question, re.IGNORECASE):
                return JsonResponse({"response": response})

        # 使用統一的chroma_db向量搜索
        print("[AI客服] 使用chroma_db統一向量搜索")
        try:
            vector_result = direct_text_search(user_question)
            if vector_result:
                print(f"[AI客服] chroma_db搜索成功")
                return JsonResponse({"response": vector_result})
        except Exception as e:
            print(f"[AI客服] chroma_db搜索失敗: {e}")

        # 向量搜索失敗，使用關鍵字匹配兜底
        print("[AI客服] 使用關鍵字匹配兜底")
        fallback = fallback_response(user_question)
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