#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修復向量資料庫 - 重建以匹配 768 維模型
"""
import os
import shutil
import sys

def fix_vector_db():
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        from chromadb.config import Settings

        print("載入嵌入模型...")
        embedder = SentenceTransformer('BAAI/bge-base-zh-v1.5')
        print(f'模型維度: {embedder.get_sentence_embedding_dimension()}')

        DB_DIR = 'rag/chroma_db'
        COLLECTION_NAME = 'faq_with_training'

        # 刪除舊資料庫
        if os.path.exists(DB_DIR):
            shutil.rmtree(DB_DIR)
            print('已刪除舊的向量資料庫')

        print("建立新的向量資料庫...")
        client = chromadb.PersistentClient(
            path=DB_DIR,
            settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_or_create_collection(COLLECTION_NAME)

        # FAQ 資料 - 使用繁體中文
        faq_data = [
            {
                'id': 'Q1',
                'question': '寵物健康紀錄怎麼填寫？',
                'answer': '''寵物健康紀錄填寫的內容包括：

1. 基本生理數值檢查
2. 觀察食慾和活動力狀況
3. 定期測量體溫
4. 記錄每日排便和小便情況
5. 疫苗接種和定期健康檢查
6. 注意特殊症狀紀錄
7. 體重變化和成長記錄
8. 行為異常和情緒變化
9. 運動時間和強度記錄

注意事項：
• 出現多個症狀應立即就醫
• 幼齡和高齡寵物需特別注意
• 症狀持續超過24小時建議就醫'''
            },
            {
                'id': 'Q2',
                'question': '如何幫寵物洗澡？',
                'answer': '''正確幫寵物洗澡的步驟：

準備工作：
1. 準備適溫的洗澡水（38-40度C）
2. 準備寵物專用洗毛精
3. 毛巾和吹風機

洗澡步驟：
1. 先用溫水沖洗寵物全身
2. 避免水進入耳朵和眼睛
3. 輕輕按摩並清潔毛髮
4. 徹底沖洗乾淨
5. 用毛巾輕拍吸水
6. 徹底吹乾避免感冒

洗澡頻率：
• 狗狗：每1-2個月一次
• 貓咪：通常不需要經常洗澡

注意事項：
• 幼齡、生病或懷孕的寵物應避免洗澡
• 使用寵物專用洗毛精
• 確保完全吹乾，避免感冒'''
            },
            {
                'id': 'Q3',
                'question': '寵物疫苗接種時程？',
                'answer': '''寵物疫苗接種的完整時程：

幼犬疫苗時程：
• 6-8週：第一劑疫苗
• 10-12週：第二劑疫苗
• 14-16週：第三劑疫苗
• 16週以後：狂犬病疫苗

幼貓疫苗時程：
• 8-10週：第一劑疫苗
• 12-14週：第二劑疫苗
• 16週以後：狂犬病疫苗

注意事項：
• 疫苗前確保寵物身體健康
• 避免在疫苗期間洗澡
• 建立完整的疫苗紀錄'''
            },
            {
                'id': 'Q4',
                'question': '如何在社群中按讚和留言？',
                'answer': '''在毛日好社群中進行互動的步驟：

按讚功能：
1. 在社群動態頁面瀏覽貼文
2. 點擊貼文下方的愛心圖示即可按讚
3. 再次點擊可以取消按讚
4. 按讚數會即時更新顯示

留言功能：
1. 點擊貼文下方的留言圖示
2. 在留言輸入框中寫下你的想法
3. 點擊發送按鈕提交留言
4. 也可以使用Ctrl+Enter快速發送留言
5. 可以對其他人的留言按讚

注意事項：
• 需要登入會員才能按讚和留言
• 請保持友善的互動環境
• 可以隨時刪除自己的留言'''
            },
            {
                'id': 'Q5',
                'question': '社群功能有哪些？',
                'answer': '''毛日好社群提供以下功能：

發文功能：
1. 分享寵物照片和生活動態
2. 撰寫寵物照護心得
3. 發布寵物相關問題求助

互動功能：
1. 按讚：對喜歡的貼文按讚支持
2. 留言：與其他寵物家長交流討論
3. 分享：將實用內容分享給朋友

瀏覽功能：
1. 瀏覽其他用戶的寵物動態
2. 搜尋特定主題的貼文
3. 查看熱門貼文排行

個人檔案：
1. 編輯個人資料和寵物資訊
2. 查看自己的發文記錄
3. 管理追蹤和粉絲

注意事項：
• 所有功能都需要註冊登入
• 遵守社群守則，維護友善環境'''
            },
            {
                'id': 'Q6',
                'question': '如何發布寵物動態貼文？',
                'answer': '''發布寵物動態貼文的步驟：

發文步驟：
1. 進入「毛日好社群」頁面
2. 在發文區域點擊「分享你的想法...」
3. 輸入想要分享的內容
4. 可以上傳寵物照片或影片
5. 選擇適當的標籤分類
6. 點擊「發布」按鈕完成

內容建議：
• 分享寵物可愛瞬間
• 記錄寵物成長過程
• 分享照護心得和經驗
• 提問寵物相關疑問
• 推薦好用的寵物用品

發文技巧：
1. 加上相關標籤提高曝光
2. 搭配清楚的照片更吸引人
3. 內容真實有趣容易引起共鳴

注意事項：
• 確保照片清晰且適當
• 內容積極正面
• 尊重其他用戶隱私'''
            }
        ]

        print("準備文檔和向量...")
        documents = []
        metadatas = []
        ids = []

        for faq in faq_data:
            doc_text = f"問題：{faq['question']}\n\n回答：{faq['answer']}"
            documents.append(doc_text)
            metadatas.append({
                'id': faq['id'],
                'title': faq['question'],
                'source': 'FAQ'
            })
            ids.append(f"faq_{faq['id']}")

        print("建立向量並儲存...")
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f'向量資料庫重建完成！總文檔數: {collection.count()}')

        # 測試查詢
        print("\n測試查詢...")
        test_queries = ['如何按讚', '留言功能', '社群互動']

        for query in test_queries:
            results = collection.query(
                query_texts=[query],
                n_results=2,
                include=['documents', 'metadatas', 'distances']
            )

            print(f'\n查詢「{query}」:')
            if results and results['documents']:
                for i, (doc, meta, dist) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    similarity = 1 - dist
                    print(f'  {i+1}. 相似度: {similarity:.3f}')
                    print(f'     標題: {meta["title"]}')

        return True

    except Exception as e:
        print(f'錯誤: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("修復向量資料庫")
    print("=" * 50)

    if fix_vector_db():
        print("\n修復完成！請重新啟動 Django 服務測試 AI 客服功能。")
    else:
        print("\n修復失敗，請檢查錯誤訊息。")