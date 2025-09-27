# petapp/notification_views.py
"""
改進版通知 API
支持分頁、性能優化和大規模數據處理
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.core.cache import cache
from django.conf import settings
import json
import logging

from .notification_optimization import NotificationManager

logger = logging.getLogger(__name__)


@login_required
def get_notifications_paginated_api(request):
    """
    獲取分頁通知列表 API
    支持分頁、篩選和性能優化
    """
    try:
        # 獲取參數
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)  # 限制最大每頁數量
        unread_only = request.GET.get('unread_only', 'false').lower() == 'true'

        # 使用緩存鍵
        cache_key = f"notifications_{request.user.id}_{page}_{page_size}_{unread_only}"

        # 嘗試從緩存獲取
        cached_result = cache.get(cache_key)
        if cached_result and not unread_only:  # 未讀通知不使用緩存
            return JsonResponse({
                'success': True,
                'cached': True,
                **cached_result
            })

        # 獲取通知數據
        result = NotificationManager.get_user_notifications(
            user=request.user,
            page=page,
            page_size=page_size,
            unread_only=unread_only
        )

        # 緩存結果（5分鐘）
        if not unread_only:
            cache.set(cache_key, result, 300)

        return JsonResponse({
            'success': True,
            'cached': False,
            **result
        })

    except Exception as e:
        logger.error(f"獲取通知失敗: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'notifications': [],
            'pagination': {
                'current_page': 1,
                'total_pages': 1,
                'total_count': 0,
                'has_next': False,
                'has_previous': False,
                'per_page': 20
            }
        })


@login_required
def get_notification_count_optimized_api(request):
    """
    獲取未讀通知數量 API（優化版）
    使用緩存和高效查詢
    """
    try:
        # 使用用戶ID作為緩存鍵
        cache_key = f"notification_count_{request.user.id}"

        # 嘗試從緩存獲取
        count = cache.get(cache_key)

        if count is None:
            # 緩存未命中，從數據庫查詢
            count = NotificationManager.get_unread_count(request.user)

            # 緩存結果（1分鐘）
            cache.set(cache_key, count, 60)

        return JsonResponse({
            'success': True,
            'count': count,
            'cached': count is not None
        })

    except Exception as e:
        logger.error(f"獲取通知數量失敗: {e}")
        return JsonResponse({
            'success': False,
            'count': 0,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def mark_notifications_read_bulk_api(request):
    """
    批量標記通知為已讀 API
    支持單個或多個通知
    """
    try:
        data = json.loads(request.body) if request.body else {}
        notification_ids = data.get('notification_ids', None)  # None 表示全部

        # 標記通知為已讀
        updated_count = NotificationManager.mark_notifications_read(
            user=request.user,
            notification_ids=notification_ids
        )

        # 清除相關緩存
        cache_pattern = f"notification*{request.user.id}*"
        cache.delete_many([
            f"notification_count_{request.user.id}",
            f"notifications_{request.user.id}_*"
        ])

        # 記錄操作
        action = "全部" if notification_ids is None else f"{len(notification_ids)}個"
        logger.info(f"用戶 {request.user.username} 標記了{action}通知為已讀")

        return JsonResponse({
            'success': True,
            'message': f'已標記 {updated_count} 個通知為已讀',
            'updated_count': updated_count
        })

    except Exception as e:
        logger.error(f"標記通知已讀失敗: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': '操作失敗，請稍後再試'
        })


@login_required
@require_http_methods(["POST"])
def notification_click_redirect_api(request, notification_id):
    """
    通知點擊跳轉 API
    點擊通知時標記為已讀並返回目標URL
    """
    try:
        from .models import Notification

        # 獲取通知
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )

        # 標記為已讀
        if not notification.is_read:
            notification.mark_as_read()

            # 清除相關緩存
            cache.delete(f"notification_count_{request.user.id}")

        # 獲取目標URL
        target_url = notification.get_target_url()

        return JsonResponse({
            'success': True,
            'target_url': target_url,
            'notification_type': notification.notification_type,
            'title': notification.title
        })

    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '通知不存在或無權限',
            'target_url': '/notifications/'
        })
    except Exception as e:
        logger.error(f"通知跳轉失敗: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'target_url': '/notifications/'
        })


@login_required
def notification_statistics_api(request):
    """
    獲取用戶通知統計信息 API
    """
    try:
        # 使用緩存鍵
        cache_key = f"notification_stats_{request.user.id}"

        # 嘗試從緩存獲取
        stats = cache.get(cache_key)

        if stats is None:
            from django.db.models import Count
            from .models import Notification
            from django.utils import timezone
            from datetime import timedelta

            # 統計用戶通知信息
            total = Notification.objects.filter(recipient=request.user).count()
            unread = Notification.objects.filter(recipient=request.user, is_read=False).count()

            # 按類型統計
            type_stats = list(Notification.objects.filter(
                recipient=request.user
            ).values('notification_type').annotate(
                count=Count('id')
            ).order_by('-count'))

            # 最近活動統計
            now = timezone.now()
            recent_stats = {
                'today': Notification.objects.filter(
                    recipient=request.user,
                    created_at__gte=now - timedelta(days=1)
                ).count(),
                'week': Notification.objects.filter(
                    recipient=request.user,
                    created_at__gte=now - timedelta(days=7)
                ).count(),
                'month': Notification.objects.filter(
                    recipient=request.user,
                    created_at__gte=now - timedelta(days=30)
                ).count(),
            }

            stats = {
                'total_notifications': total,
                'unread_notifications': unread,
                'read_notifications': total - unread,
                'read_rate': ((total - unread) / total * 100) if total > 0 else 0,
                'type_distribution': type_stats,
                'recent_activity': recent_stats
            }

            # 緩存結果（10分鐘）
            cache.set(cache_key, stats, 600)

        return JsonResponse({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        logger.error(f"獲取通知統計失敗: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@method_decorator(login_required, name='dispatch')
class NotificationPreferencesView(View):
    """
    通知偏好設定 API
    允許用戶設定通知類型偏好
    """

    def get(self, request):
        """獲取用戶通知偏好"""
        try:
            # 這裡可以從 UserProfile 或專門的偏好表獲取
            # 暫時返回默認設定
            preferences = {
                'email_notifications': True,
                'push_notifications': True,
                'notification_types': {
                    'follow': True,
                    'like': True,
                    'comment': True,
                    'appointment_created': True,
                    'appointment_confirmed': True,
                    'pet_health_reminder': True,
                    'system': True,
                },
                'quiet_hours': {
                    'enabled': False,
                    'start_time': '22:00',
                    'end_time': '08:00'
                },
                'max_daily_notifications': 50
            }

            return JsonResponse({
                'success': True,
                'preferences': preferences
            })

        except Exception as e:
            logger.error(f"獲取通知偏好失敗: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    def post(self, request):
        """更新用戶通知偏好"""
        try:
            data = json.loads(request.body)

            # 這裡應該保存到數據庫
            # 暫時只記錄日誌
            logger.info(f"用戶 {request.user.username} 更新了通知偏好: {data}")

            return JsonResponse({
                'success': True,
                'message': '通知偏好已更新'
            })

        except Exception as e:
            logger.error(f"更新通知偏好失敗: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e),
                'message': '更新失敗，請稍後再試'
            })