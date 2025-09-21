# petapp/templatetags/schedule_filters.py
from django import template

register = template.Library()

@register.filter
def filter_by_doctor(schedules, doctor):
    """篩選指定醫師的排班"""
    return schedules.filter(doctor=doctor)

@register.filter
def get_weekday_name(weekday_num):
    """獲取週幾的中文名稱"""
    weekday_names = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
    try:
        return weekday_names[int(weekday_num)]
    except (ValueError, IndexError):
        return f'週{weekday_num}'

@register.filter
def schedule_status_class(status):
    """獲取排班狀態對應的CSS類名"""
    status_classes = {
        'draft': 'secondary',
        'pending': 'warning', 
        'approved': 'info',
        'active': 'success',
        'expired': 'light',
        'cancelled': 'danger',
        'suspended': 'warning'
    }
    return status_classes.get(status, 'secondary')

@register.filter
def conflict_severity_class(conflicts):
    """獲取衝突嚴重程度對應的CSS類名"""
    if not conflicts:
        return 'success'
    
    conflict_count = len(conflicts) if isinstance(conflicts, list) else 0
    
    if conflict_count >= 3:
        return 'danger'
    elif conflict_count >= 1:
        return 'warning'
    else:
        return 'success'

@register.filter
def get_item(dictionary, key):
    """從字典中獲取指定鍵的值"""
    if not dictionary:
        return None
    
    # 處理字典類型
    if hasattr(dictionary, 'get'):
        # 先嘗試原始鍵
        result = dictionary.get(key)
        if result is not None:
            return result
        
        # 如果原始鍵沒找到，嘗試字串鍵
        str_key = str(key)
        result = dictionary.get(str_key)
        if result is not None:
            return result
        
        # 如果是字串鍵，嘗試轉為整數鍵
        if isinstance(key, str) and key.isdigit():
            int_key = int(key)
            return dictionary.get(int_key)
    
    # 處理字串鍵的字典
    try:
        return dictionary[str(key)]
    except (KeyError, TypeError):
        try:
            return dictionary[key]
        except (KeyError, TypeError):
            return None