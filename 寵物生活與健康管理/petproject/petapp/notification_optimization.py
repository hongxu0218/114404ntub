# petapp/notification_optimization.py
"""
通知系統優化解決方案
處理大量通知的性能和存儲問題
"""

from django.db import models
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from .models import Notification
import logging

logger = logging.getLogger(__name__)


class NotificationManager:
    """通知管理器 - 處理大規模通知的優化邏輯"""

    # 配置參數
    DEFAULT_PAGE_SIZE = 20
    MAX_NOTIFICATIONS_PER_USER = 1000  # 每用戶最大通知數
    AUTO_CLEANUP_DAYS = 90  # 自動清理天數

    @staticmethod
    def get_user_notifications(user, page=1, page_size=None, unread_only=False):
        """
        獲取用戶通知（分頁）

        Args:
            user: 用戶對象
            page: 頁碼（從1開始）
            page_size: 每頁數量
            unread_only: 只獲取未讀通知

        Returns:
            dict: 包含通知列表和分頁信息
        """
        if page_size is None:
            page_size = NotificationManager.DEFAULT_PAGE_SIZE

        # 基礎查詢，使用索引優化
        queryset = Notification.objects.filter(
            recipient=user
        ).select_related('sender', 'post', 'comment').order_by('-created_at')

        if unread_only:
            queryset = queryset.filter(is_read=False)

        # 分頁處理
        paginator = Paginator(queryset, page_size)

        try:
            notifications_page = paginator.page(page)
        except Exception:
            notifications_page = paginator.page(1)

        # 格式化通知數據
        notifications = []
        for notification in notifications_page:
            notifications.append({
                'id': notification.id,
                'type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'time': NotificationManager._format_time_ago(notification.created_at),
                'is_read': notification.is_read,
                'sender': notification.sender.username if notification.sender else '系統',
                'created_at': notification.created_at.isoformat(),
                'url': NotificationManager._get_notification_url(notification)
            })

        return {
            'notifications': notifications,
            'pagination': {
                'current_page': notifications_page.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': notifications_page.has_next(),
                'has_previous': notifications_page.has_previous(),
                'per_page': page_size
            }
        }

    @staticmethod
    def get_unread_count(user):
        """獲取用戶未讀通知數量（優化版）"""
        try:
            # 使用數據庫計數，避免載入所有對象
            return Notification.objects.filter(
                recipient=user,
                is_read=False
            ).count()
        except Exception as e:
            logger.error(f"獲取未讀通知數量失敗: {e}")
            return 0

    @staticmethod
    def mark_notifications_read(user, notification_ids=None):
        """
        批量標記通知為已讀

        Args:
            user: 用戶對象
            notification_ids: 通知ID列表，None表示全部

        Returns:
            int: 更新的通知數量
        """
        try:
            queryset = Notification.objects.filter(
                recipient=user,
                is_read=False
            )

            if notification_ids:
                queryset = queryset.filter(id__in=notification_ids)

            updated_count = queryset.update(is_read=True)
            logger.info(f"用戶 {user.username} 標記了 {updated_count} 個通知為已讀")
            return updated_count

        except Exception as e:
            logger.error(f"標記通知已讀失敗: {e}")
            return 0

    @staticmethod
    def cleanup_old_notifications(user, days=None):
        """
        清理用戶的舊通知

        Args:
            user: 用戶對象
            days: 清理天數，None使用默認值

        Returns:
            int: 清理的通知數量
        """
        if days is None:
            days = NotificationManager.AUTO_CLEANUP_DAYS

        cutoff_date = timezone.now() - timedelta(days=days)

        try:
            # 只清理已讀的舊通知
            deleted_count = Notification.objects.filter(
                recipient=user,
                is_read=True,
                created_at__lt=cutoff_date
            ).delete()[0]

            logger.info(f"清理用戶 {user.username} 的 {deleted_count} 個舊通知")
            return deleted_count

        except Exception as e:
            logger.error(f"清理舊通知失敗: {e}")
            return 0

    @staticmethod
    def aggregate_similar_notifications(user):
        """
        聚合相似通知（如多個按讚通知）

        Args:
            user: 用戶對象

        Returns:
            int: 聚合的通知數量
        """
        try:
            aggregated_count = 0

            # 聚合同類型的未讀通知
            notification_types = ['like', 'comment_like', 'follow']

            for notif_type in notification_types:
                # 查找同類型的多個通知
                notifications = Notification.objects.filter(
                    recipient=user,
                    notification_type=notif_type,
                    is_read=False
                ).order_by('-created_at')

                if notifications.count() > 3:  # 超過3個則聚合
                    # 保留最新的3個，聚合其他的
                    keep_notifications = list(notifications[:3])
                    old_notifications = notifications[3:]

                    if old_notifications:
                        # 創建聚合通知
                        count = old_notifications.count()
                        Notification.objects.create(
                            recipient=user,
                            notification_type=notif_type,
                            title=f'您有 {count + 3} 個{dict(Notification.NOTIFICATION_TYPES)[notif_type]}',
                            message=f'包括來自多位用戶的互動通知',
                            is_read=False
                        )

                        # 刪除舊通知
                        deleted = old_notifications.delete()[0]
                        aggregated_count += deleted

                        logger.info(f"聚合了 {deleted} 個 {notif_type} 通知")

            return aggregated_count

        except Exception as e:
            logger.error(f"聚合通知失敗: {e}")
            return 0

    @staticmethod
    def _format_time_ago(created_at):
        """格式化時間顯示"""
        time_diff = timezone.now() - created_at

        if time_diff.days > 7:
            return created_at.strftime('%Y-%m-%d')
        elif time_diff.days > 0:
            return f'{time_diff.days}天前'
        elif time_diff.seconds > 3600:
            return f'{time_diff.seconds // 3600}小時前'
        elif time_diff.seconds > 60:
            return f'{time_diff.seconds // 60}分鐘前'
        else:
            return '剛剛'

    @staticmethod
    def _get_notification_url(notification):
        """獲取通知相關的URL"""
        if notification.post:
            return f'/social/post/{notification.post.id}/'
        elif notification.notification_type.startswith('appointment'):
            # 根據接收者身份決定跳轉頁面
            try:
                vet_profile = notification.recipient.vet_profile
                if vet_profile:
                    # 如果是診所管理員，跳轉到診所預約管理頁面
                    if vet_profile.is_clinic_admin:
                        return '/clinic/appointments/'
                    # 如果是獸醫師，跳轉到獸醫預約頁面
                    else:
                        return '/vet/appointments/'
            except:
                pass
            # 飼主收到的預約通知跳轉到飼主預約頁面
            return '/appointments/my/'
        else:
            return '#'


class NotificationArchive(models.Model):
    """
    通知歸檔表 - 存儲舊通知的摘要信息
    用於長期數據保存而不影響主表性能
    """
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='用戶')
    archive_date = models.DateField(verbose_name='歸檔日期')
    notification_type = models.CharField(max_length=30, verbose_name='通知類型')
    count = models.PositiveIntegerField(verbose_name='數量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '通知歸檔'
        verbose_name_plural = '通知歸檔'
        indexes = [
            models.Index(fields=['user', 'archive_date']),
            models.Index(fields=['notification_type']),
        ]
        unique_together = ['user', 'archive_date', 'notification_type']