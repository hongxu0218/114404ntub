"""
網站訪問追蹤 Middleware
使用 Cache 記錄到訪數（基於 IP 地址，每日去重）
"""

from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta


class VisitTrackingMiddleware(MiddlewareMixin):
    """追蹤網站訪問記錄（使用 Cache，基於 IP）"""

    # 排除不需要追蹤的路徑
    EXCLUDED_PATHS = [
        '/static/',
        '/media/',
        '/admin/jsi18n/',
        '/favicon.ico',
        '/__debug__/',
    ]

    def get_client_ip(self, request):
        """獲取客戶端真實 IP 地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # 如果有代理，取第一個 IP
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def process_request(self, request):
        """處理每個請求，記錄訪問（基於 IP，每日去重）"""

        # 檢查是否為排除路徑
        path = request.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return None

        # 獲取客戶端 IP
        client_ip = self.get_client_ip(request)
        if not client_ip:
            return None

        try:
            now = timezone.now()
            today = now.date()

            # 檢查今天是否已記錄過此 IP（每日只計算一次）
            today_ip_key = f'visit_ip_{today}_{client_ip}'
            if cache.get(today_ip_key):
                # 今天已經記錄過此 IP，不重複計算
                return None

            # 標記此 IP 今天已訪問（到今天結束前有效）
            seconds_until_midnight = (
                datetime.combine(today + timedelta(days=1), datetime.min.time()) - now
            ).total_seconds()
            cache.set(today_ip_key, True, int(seconds_until_midnight))

            # 記錄今日訪問的 IP 集合（用於統計獨立訪客數）
            today_ips_key = f'visits_ips_{today}'
            today_ips = cache.get(today_ips_key, set())
            today_ips.add(client_ip)
            cache.set(today_ips_key, today_ips, 86400)  # 24小時過期

            # 記錄過去7天的每日訪問 IP 集合
            for i in range(7):
                date = today - timedelta(days=i)
                date_ips_key = f'visits_ips_{date}'
                if not cache.get(date_ips_key):
                    # 如果該日期的 cache 不存在，初始化為空集合
                    cache.set(date_ips_key, set(), 86400 * 8)  # 保留8天

            # 更新總訪問數（累計獨立訪客數）
            total_key = 'visits_total'
            cache.set(total_key, cache.get(total_key, 0) + 1, None)  # 永久保存

        except Exception as e:
            # 記錄失敗不應影響正常請求
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to track visit: {e}")

        return None
