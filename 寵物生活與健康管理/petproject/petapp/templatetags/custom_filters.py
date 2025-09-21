from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def mul(value, arg):
    """Multiplies the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def basename(value):
    """Returns the base filename without path prefixes."""
    import os
    if hasattr(value, 'name'):
        # For FileField objects, get the name attribute
        filename = value.name
    else:
        # For string paths
        filename = str(value)

    # Get just the filename without directory path
    return os.path.basename(filename)

@register.filter
def translate_frequency(value):
    """Translates medication frequency from English to Chinese."""
    frequency_map = {
        'bid': '一日兩次',
        'tid': '一日三次',
        'qid': '一日四次',
        'qd': '一日一次',
        'q12h': '每12小時一次',
        'q8h': '每8小時一次',
        'q6h': '每6小時一次',
        'prn': '需要時使用',
        'stat': '立即使用',
        'hs': '睡前使用',
        'ac': '飯前使用',
        'pc': '飯後使用'
    }
    return frequency_map.get(str(value).lower(), value)

@register.filter
def translate_route(value):
    """Translates administration route from English to Chinese."""
    route_map = {
        'oral': '口服',
        'topical': '外用',
        'iv': '靜脈注射',
        'im': '肌肉注射',
        'sc': '皮下注射',
        'po': '口服',
        'eye': '眼部給藥',
        'ear': '耳部給藥',
        'nasal': '鼻部給藥',
        'rectal': '直腸給藥',
        'inhalation': '吸入給藥'
    }
    return route_map.get(str(value).lower(), value)

