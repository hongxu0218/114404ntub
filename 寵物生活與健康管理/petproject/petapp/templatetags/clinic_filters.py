# petapp/templatetags/clinic_filters.py
"""
診所排班系統專用的Django模板過濾器
"""

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    從字典中根據鍵值取得項目
    
    用法：
    {{ my_dict|get_item:key_name }}
    {% for item in my_dict|get_item:key_name %}
    
    Args:
        dictionary: 字典物件
        key: 鍵值
        
    Returns:
        字典中對應鍵值的項目，如果不存在則返回空列表
    """
    if not dictionary:
        return []
    
    try:
        # 嘗試轉換key為整數（針對weekday等數字鍵）
        if isinstance(key, str) and key.isdigit():
            key = int(key)
        
        # 從字典中取得項目
        result = dictionary.get(key, [])
        
        # 如果是QuerySet，轉換為列表以便在模板中使用
        if hasattr(result, 'all'):
            return list(result.all())
        
        return result if result is not None else []
        
    except (TypeError, ValueError, AttributeError):
        return []

@register.filter
def get_dict_item(dictionary, key):
    """
    專門處理嵌套字典的過濾器
    適用於 team_schedules[doctor][day] 這種結構
    
    用法：
    {{ team_schedules|get_dict_item:doctor|get_dict_item:day }}
    """
    if not dictionary or not key:
        return {}
    
    try:
        return dictionary.get(key, {})
    except (TypeError, AttributeError):
        return {}

@register.filter
def weekday_name(weekday_num):
    """
    將星期數字轉換為中文名稱
    
    用法：
    {{ 0|weekday_name }}  -> 星期一
    """
    weekdays = {
        0: '星期一',
        1: '星期二', 
        2: '星期三',
        3: '星期四',
        4: '星期五',
        5: '星期六',
        6: '星期日'
    }
    return weekdays.get(weekday_num, f'星期{weekday_num}')

@register.filter
def time_format(time_obj):
    """
    格式化時間顯示
    
    用法：
    {{ schedule.start_time|time_format }}  -> 09:00
    """
    if not time_obj:
        return ''
    
    try:
        if isinstance(time_obj, str):
            return time_obj[:5]  # 取前5個字符 "HH:MM"
        return time_obj.strftime('%H:%M')
    except (AttributeError, ValueError):
        return str(time_obj)[:5]

@register.filter
def schedule_duration(start_time, end_time):
    """
    計算排班時長（小時）
    
    用法：
    {{ schedule.start_time|schedule_duration:schedule.end_time }}
    """
    if not start_time or not end_time:
        return 0
    
    try:
        from datetime import datetime, time
        
        # 處理字符串時間
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time[:5], '%H:%M').time()
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time[:5], '%H:%M').time()
        
        # 計算時長
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        duration_minutes = end_minutes - start_minutes
        
        return round(duration_minutes / 60, 1)
        
    except (ValueError, AttributeError):
        return 0

@register.filter
def add_minutes(time_obj, minutes):
    """
    為時間物件增加分鐘數
    
    用法：
    {{ schedule.start_time|add_minutes:30 }}
    """
    if not time_obj or not minutes:
        return time_obj
    
    try:
        from datetime import datetime, timedelta
        
        if isinstance(time_obj, str):
            time_obj = datetime.strptime(time_obj[:5], '%H:%M').time()
        
        # 轉換為datetime進行計算
        dt = datetime.combine(datetime.today(), time_obj)
        dt += timedelta(minutes=int(minutes))
        
        return dt.time()
        
    except (ValueError, AttributeError, TypeError):
        return time_obj

@register.filter
def is_current_time(start_time, end_time):
    """
    檢查當前時間是否在排班時間內
    
    用法：
    {% if schedule.start_time|is_current_time:schedule.end_time %}
    """
    if not start_time or not end_time:
        return False
    
    try:
        from datetime import datetime, time
        
        now = datetime.now().time()
        
        # 處理字符串時間
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time[:5], '%H:%M').time()
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time[:5], '%H:%M').time()
        
        return start_time <= now <= end_time
        
    except (ValueError, AttributeError):
        return False

@register.simple_tag
def get_schedule_for_doctor_day(schedules_dict, doctor, day):
    """
    簡單標籤：取得特定醫師和日期的排班
    
    用法：
    {% get_schedule_for_doctor_day team_schedules doctor 1 as day_schedules %}
    {% for schedule in day_schedules %}
    """
    try:
        return schedules_dict.get(doctor, {}).get(day, [])
    except (AttributeError, TypeError):
        return []

@register.inclusion_tag('clinic/partials/schedule_block.html')
def render_schedule_block(schedule):
    """
    包含標籤：渲染排班區塊
    
    用法：
    {% render_schedule_block schedule %}
    """
    return {
        'schedule': schedule,
        'is_current': schedule.start_time <= timezone.now().time() <= schedule.end_time if schedule else False
    }

@register.filter
def dict_keys(dictionary):
    """
    取得字典的所有鍵值
    
    用法：
    {% for key in my_dict|dict_keys %}
    """
    if not dictionary:
        return []
    
    try:
        return list(dictionary.keys())
    except AttributeError:
        return []

@register.filter
def dict_values(dictionary):
    """
    取得字典的所有值
    
    用法：
    {% for value in my_dict|dict_values %}
    """
    if not dictionary:
        return []
    
    try:
        return list(dictionary.values())
    except AttributeError:
        return []