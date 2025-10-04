"""
網站訪問追蹤 Middleware
使用 Cache 記錄到訪數（不使用資料庫）
"""

from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta


class VisitTrackingMiddleware(MiddlewareMixin):
    """追蹤網站訪問記錄（使用 Cache）"""

    # 排除不需要追蹤的路徑
    EXCLUDED_PATHS = [
        '/static/',
        '/media/',
        '/admin/jsi18n/',
        '/favicon.ico',
        '/__debug__/',
    ]

    def process_request(self, request):
        """處理每個請求，記錄訪問"""

        # 檢查是否為排除路徑
        path = request.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return None

        # 獲取或創建 session key
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        try:
            now = timezone.now()
            today = now.date()

            # 檢查是否為重複訪問（同一 session 5分鐘內不重複計算）
            recent_visit_key = f'visit_check_{session_key}_{path}'
            if cache.get(recent_visit_key):
                return None

            # 標記此次訪問（5分鐘內不重複計算）
            cache.set(recent_visit_key, True, 300)  # 300秒 = 5分鐘

            # 記錄今日訪問（使用 session_key 去重）
            today_sessions_key = f'visits_sessions_{today}'
            today_sessions = cache.get(today_sessions_key, set())
            today_sessions.add(session_key)
            cache.set(today_sessions_key, today_sessions, 86400)  # 24小時過期

            # 記錄過去7天的每日訪問
            for i in range(7):
                date = today - timedelta(days=i)
                date_sessions_key = f'visits_sessions_{date}'
                if not cache.get(date_sessions_key):
                    # 如果該日期的 cache 不存在，初始化為空集合
                    cache.set(date_sessions_key, set(), 86400 * 8)  # 保留8天

            # 更新總訪問數
            total_key = 'visits_total'
            cache.set(total_key, cache.get(total_key, 0) + 1, None)  # 永久保存

        except Exception as e:
            # 記錄失敗不應影響正常請求
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to track visit: {e}")

        return None
