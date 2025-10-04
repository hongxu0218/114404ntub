"""
測試訪問追蹤功能
檢查為什麼同一 IP 會被重複計算
"""

import os
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta

def test_visit_tracking():
    print("=" * 60)
    print("測試訪問追蹤功能")
    print("=" * 60)

    # 清空快取重新開始
    cache.clear()
    print("\n✅ 已清空快取\n")

    # 模擬測試
    today = timezone.now().date()
    test_ip = "127.0.0.1"

    print(f"測試日期: {today}")
    print(f"測試 IP: {test_ip}\n")

    # 第一次訪問 - 模擬訪問首頁
    print("-" * 60)
    print("第 1 次訪問（首頁）")
    print("-" * 60)

    ip_key = f'visit_ip_{today}_{test_ip}'

    # 檢查是否已記錄
    if cache.get(ip_key):
        print(f"❌ IP 已記錄過，不應該再計算")
    else:
        print(f"✅ IP 第一次訪問，開始記錄")

        # 標記 IP
        now = timezone.now()
        seconds_until_midnight = (
            datetime.combine(today + timedelta(days=1), datetime.min.time()) - now
        ).total_seconds()
        cache.set(ip_key, True, int(seconds_until_midnight))
        print(f"   - 已設定快取，過期時間: {int(seconds_until_midnight)} 秒")

        # 更新總訪問數
        total = cache.get('visits_total', 0) + 1
        cache.set('visits_total', total, None)
        print(f"   - 總訪問數: {total}")

    # 驗證快取是否設定成功
    print(f"\n驗證快取: cache.get('{ip_key}') = {cache.get(ip_key)}")

    # 第二次訪問 - 模擬訪問 social 頁面
    print("\n" + "-" * 60)
    print("第 2 次訪問（social 頁面）")
    print("-" * 60)

    if cache.get(ip_key):
        print(f"✅ IP 已記錄過，不重複計算")
        print(f"   - 總訪問數維持: {cache.get('visits_total', 0)}")
    else:
        print(f"❌ 錯誤！快取遺失，IP 會被重複計算")
        total = cache.get('visits_total', 0) + 1
        cache.set('visits_total', total, None)
        print(f"   - 總訪問數錯誤增加至: {total}")

    # 第三次訪問 - 模擬訪問 adoptions 頁面
    print("\n" + "-" * 60)
    print("第 3 次訪問（adoptions 頁面）")
    print("-" * 60)

    if cache.get(ip_key):
        print(f"✅ IP 已記錄過，不重複計算")
        print(f"   - 總訪問數維持: {cache.get('visits_total', 0)}")
    else:
        print(f"❌ 錯誤！快取遺失，IP 會被重複計算")
        total = cache.get('visits_total', 0) + 1
        cache.set('visits_total', total, None)
        print(f"   - 總訪問數錯誤增加至: {total}")

    # 最終結果
    print("\n" + "=" * 60)
    print("測試結果總結")
    print("=" * 60)
    final_total = cache.get('visits_total', 0)
    print(f"最終總訪問數: {final_total}")

    if final_total == 1:
        print("✅ 測試通過！同一 IP 只計算一次")
    else:
        print(f"❌ 測試失敗！同一 IP 被計算了 {final_total} 次")

    # 檢查快取表內容
    print("\n" + "=" * 60)
    print("檢查 cache_table 資料表")
    print("=" * 60)

    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT cache_key, expires FROM cache_table WHERE cache_key LIKE %s LIMIT 10", [f'%{today}%'])
        rows = cursor.fetchall()
        if rows:
            print("快取資料:")
            for row in rows:
                print(f"  - Key: {row[0][:50]}... | Expires: {row[1]}")
        else:
            print("⚠️ 沒有找到相關的快取資料")

if __name__ == '__main__':
    test_visit_tracking()
