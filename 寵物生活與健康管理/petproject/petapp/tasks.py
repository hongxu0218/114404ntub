# petapp/tasks.py
from celery import shared_task
from .adoption_sync import AdoptionDataSyncService
import logging

logger = logging.getLogger(__name__)

@shared_task
def sync_adoption_data():
    """定時同步動物認領養資料"""
    try:
        sync_service = AdoptionDataSyncService()
        success, message = sync_service.sync_all_data()
        
        if success:
            logger.info(f"定時同步成功: {message}")
        else:
            logger.error(f"定時同步失敗: {message}")
        
        return {'success': success, 'message': message}
    
    except Exception as e:
        logger.error(f"定時同步異常: {e}")
        return {'success': False, 'message': str(e)}