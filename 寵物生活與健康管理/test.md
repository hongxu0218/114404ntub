from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta

# 測試 1: 基本快取讀寫
cache.set('test', 'OK', 60)
print(f"測試 1 - 基本快取: {cache.get('test')}")  # 應該顯示 OK

# 測試 2: 模擬 IP 追蹤
today = timezone.now().date()
test_ip = '192.168.1.100'
ip_key = f'visit_ip_{today}_{test_ip}'

# 第一次訪問
if not cache.get(ip_key):
    cache.set(ip_key, True, 86400)
    print(f"測試 2 - 第一次訪問: 已記錄 IP {test_ip}")
else:
     print(f"測試 2 - 重複訪問: IP {test_ip} 今天已訪問過")

# 再次檢查（模擬第二次訪問）
if cache.get(ip_key):
    print(f"測試 3 - 檢查快取: IP {test_ip} 的記錄存在 ✅")
else:
    print(f"測試 3 - 檢查快取: IP {test_ip} 的記錄不存在 ❌")

# 測試 4: 查看實際儲存的值
print(f"測試 4 - 實際值: {cache.get(ip_key)}")

# 清理測試資料
cache.delete('test')
cache.delete(ip_key)

print("\n測試完成，已清理測試資料")
