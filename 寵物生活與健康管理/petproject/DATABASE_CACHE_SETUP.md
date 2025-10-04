# 💾 資料庫快取設定手冊（虛擬機適用）

## 📅 更新日期
2025-10-04

## 🎯 目的

- 網站到訪數統計
- 通知系統快取
- 提升系統效能

**適用環境**：Windows 11 虛擬機、不支援巢狀虛擬化的環境

---

### ✅ 資料庫快取的優勢
- **不需要額外服務**（不用 Docker/Redis）
- **設定簡單**（只需一行指令）
- **資料持久化**（重啟不會遺失）
- **效能足夠**（對中小型專案完全夠用）
- **跨平台**（任何支援 Django 的環境都可用）

---

## 🚀 快速設定（3 步驟）

### 步驟 1：修改 settings.py

找到 `petproject/settings.py`，將 Cache 設定區塊（約第 159 行）**替換為**：

```python
# ===== Cache 快取設定 (用於到訪數等功能) =====
# 使用資料庫快取（適用於虛擬機環境，不需要 Docker/Redis）
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',  # 快取資料表名稱
    }
}
```

### 步驟 2：建立快取資料表

在專案目錄執行：

```bash
cd D:\114404ntub\寵物生活與健康管理\petproject
python manage.py createcachetable
```

**預期輸出**：
```
（無輸出代表成功）
```

### 步驟 3：測試快取功能

```bash
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'OK', 30); result = cache.get('test'); print('Database cache OK!' if result == 'OK' else 'FAIL'); cache.delete('test')"
```

**預期輸出**：
```
Database cache OK!
```

✅ 看到此訊息代表設定成功！

---

## 📊 資料庫快取 vs Redis 快取

| 比較項目 | 資料庫快取 | Redis 快取 |
|---------|-----------|-----------|
| **安裝難度** | ⭐ 極簡單（1行指令） | ⭐⭐⭐ 需要 Docker |
| **效能** | ⭐⭐⭐ 中等（夠用） | ⭐⭐⭐⭐⭐ 極快 |
| **資源佔用** | ⭐⭐⭐⭐ 低 | ⭐⭐⭐ 中 |
| **持久化** | ✅ 自動持久化 | ✅ 可設定持久化 |
| **虛擬機支援** | ✅ 完全支援 | ❌ 需要 WSL2 |
| **適用場景** | 中小型專案、虛擬機 | 高流量、生產環境 |

**結論**：對於虛擬機環境或中小型專案，資料庫快取是最佳選擇！

---

## 🔍 快取資料表說明

### 資料表結構

執行 `createcachetable` 後，會在資料庫建立 `cache_table` 表：

```sql
CREATE TABLE cache_table (
    cache_key VARCHAR(255) PRIMARY KEY,
    value LONGTEXT,
    expires DATETIME
);
```

### 資料表內容範例

| cache_key | value | expires |
|-----------|-------|---------|
| `visits_total` | `1234` | `9999-12-31 23:59:59` |
| `visits_sessions_2025-10-04` | `{set of session_ids}` | `2025-10-05 00:00:00` |
| `notifications_user_123` | `{cached data}` | `2025-10-04 12:35:00` |

---

## 📈 專案中使用快取的功能

### ✅ 已配置快取的功能：

1. **網站到訪數統計** (`petapp/middleware.py`)
   - 記錄總訪問數：`cache.set('visits_total', count, None)`
   - 記錄今日訪問：`cache.set(f'visits_sessions_{today}', sessions, 86400)`
   - 記錄本週訪問：自動整合過去 7 天資料

2. **管理後台儀表板** (`petapp/admin_dashboard.py`)
   - 讀取總訪問數：`cache.get('visits_total', 0)`
   - 讀取今日訪問數：`len(cache.get(f'visits_sessions_{today}', set()))`
   - 計算本週訪問數：整合 7 天的 session 資料

3. **通知系統** (`petapp/notification_views.py`)
   - 快取通知列表：5 分鐘
   - 快取未讀數量：1 分鐘
   - 快取統計資料：10 分鐘

### 快取策略

| 資料類型 | 過期時間 | 說明 |
|---------|---------|------|
| 總訪問數 | 永久 | 不過期，累積計數 |
| 每日訪問 session | 24 小時 | 隔天自動清除 |
| 週訪問 session | 8 天 | 保留一週資料 |
| 通知列表 | 5 分鐘 | 定期更新 |
| 未讀數量 | 1 分鐘 | 即時性要求高 |

---

## 🛠️ 管理與維護

### 查看快取資料表

```bash
# 進入 Django shell
python manage.py shell

# 查看快取內容
from django.core.cache import cache
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT cache_key, expires FROM cache_table LIMIT 10")
    for row in cursor.fetchall():
        print(f"Key: {row[0]}, Expires: {row[1]}")
```

### 清空所有快取

```bash
python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('Cache cleared!')"
```

### 刪除特定快取

```bash
python manage.py shell -c "from django.core.cache import cache; cache.delete('visits_total'); print('Deleted!')"
```

### 查看快取統計

```sql
-- 使用 MySQL/MariaDB
SELECT COUNT(*) as total_keys FROM cache_table;
SELECT COUNT(*) as expired_keys FROM cache_table WHERE expires < NOW();
```

---

## 🔧 進階設定

### 自動清理過期快取

Django 會自動清理過期的快取項目，但你可以手動觸發：

```bash
# 建立定時任務（使用 django-apscheduler）
# 在 petapp/management/commands/ 建立 clean_cache.py
```

```python
from django.core.management.base import BaseCommand
from django.core.cache import cache

class Command(BaseCommand):
    help = '清理過期的快取資料'

    def handle(self, *args, **options):
        # Django 的資料庫快取會自動清理過期項目
        # 這裡可以加入自訂邏輯
        self.stdout.write(self.style.SUCCESS('快取清理完成'))
```

### 設定快取前綴（多專案共用資料庫）

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
        'KEY_PREFIX': 'petproject',  # 快取鍵前綴
        'VERSION': 1,  # 版本號
    }
}
```

### 設定超時時間

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
        'TIMEOUT': 300,  # 預設超時 5 分鐘（可被覆蓋）
        'OPTIONS': {
            'MAX_ENTRIES': 1000,  # 最大快取項目數
        }
    }
}
```

---

## 🚀 部署到虛擬機

### Windows 11 虛擬機部署步驟

#### 1. 確認資料庫連線
確保 `settings.py` 中的資料庫設定正確：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='3306'),
    }
}
```

#### 2. 執行遷移
```bash
python manage.py migrate
```

#### 3. 建立快取資料表
```bash
python manage.py createcachetable
```

#### 4. 測試快取
```bash
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'OK'); print('OK' if cache.get('test') == 'OK' else 'FAIL')"
```

#### 5. 啟動服務
```bash
python manage.py runserver 0.0.0.0:8000
```

---

## ❓ 常見問題

### Q1: 快取資料表建立失敗

**錯誤訊息**：
```
django.db.utils.OperationalError: (1050, "Table 'cache_table' already exists")
```

**解決方法**：
```bash
# 刪除舊的快取表
python manage.py dbshell
DROP TABLE cache_table;
exit

# 重新建立
python manage.py createcachetable
```

---

### Q2: 快取資料表佔用空間過大

**檢查資料表大小**：
```sql
SELECT
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.TABLES
WHERE table_name = 'cache_table';
```

**清理過期資料**：
```sql
DELETE FROM cache_table WHERE expires < NOW();
```

---

### Q3: 快取讀取速度慢

**優化建議**：

1. **建立索引**：
```sql
CREATE INDEX idx_expires ON cache_table(expires);
```

2. **定期清理**：
```bash
# 建立 cron job（Linux）或計畫任務（Windows）
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('DELETE FROM cache_table WHERE expires < NOW()')"
```

3. **調整 MySQL 設定**：
```ini
# my.cnf
[mysqld]
query_cache_size = 64M
query_cache_type = 1
```

---

### Q4: 如何切換回 Redis？

如果未來虛擬機支援 Docker 或部署到實體機器，可以切換回 Redis：

1. 安裝 Docker 和 Redis（參考 `DOCKER_REDIS_SETUP.md`）
2. 修改 `settings.py`：
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```
3. 重啟 Django

**無需修改程式碼**，Django 會自動切換快取後端！

---

### Q5: 多個 Django 專案共用資料庫如何避免快取衝突？

**方法 1：使用不同的資料表名稱**
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'petproject_cache',  # 不同的表名
    }
}
```

**方法 2：使用快取前綴**
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
        'KEY_PREFIX': 'petproject_',  # 專案前綴
    }
}
```

---

## 📊 效能測試

### 測試腳本

```python
# test_cache_performance.py
import time
from django.core.cache import cache

# 寫入測試
start = time.time()
for i in range(1000):
    cache.set(f'test_key_{i}', f'value_{i}', 60)
write_time = time.time() - start

# 讀取測試
start = time.time()
for i in range(1000):
    cache.get(f'test_key_{i}')
read_time = time.time() - start

# 清理
cache.clear()

print(f'寫入 1000 筆：{write_time:.2f} 秒')
print(f'讀取 1000 筆：{read_time:.2f} 秒')
```

**執行**：
```bash
python manage.py shell < test_cache_performance.py
```

### 預期效能

| 操作 | 資料庫快取 | Redis 快取 |
|-----|----------|-----------|
| 寫入 1000 筆 | ~2-5 秒 | ~0.5 秒 |
| 讀取 1000 筆 | ~1-3 秒 | ~0.3 秒 |
| 單次操作 | ~2-5 ms | ~0.5 ms |

**結論**：資料庫快取比 Redis 慢 5-10 倍，但對中小型專案（每秒數十個請求）完全夠用！

---

## 🎯 最佳實踐

### 1. 合理設定過期時間
```python
# 短期資料（1-5 分鐘）
cache.set('notification_count', count, 60)

# 中期資料（1 小時）
cache.set('user_stats', stats, 3600)

# 長期資料（1 天）
cache.set('daily_visits', visits, 86400)

# 永久資料（直到手動刪除）
cache.set('total_visits', total, None)
```

### 2. 使用有意義的鍵名
```python
# ❌ 不好的鍵名
cache.set('data', value)
cache.set('temp', value)

# ✅ 好的鍵名
cache.set('visits_sessions_2025-10-04', sessions)
cache.set('notifications_user_123', notifications)
cache.set('stats_weekly_2025-W40', stats)
```

### 3. 處理快取失敗
```python
try:
    result = cache.get('some_key')
    if result is None:
        # 快取未命中，從資料庫讀取
        result = expensive_database_query()
        cache.set('some_key', result, 300)
except Exception as e:
    # 快取失敗不應影響功能
    logger.error(f'Cache error: {e}')
    result = expensive_database_query()
```

### 4. 定期監控快取表大小
```python
# monitoring.py
from django.db import connection

def check_cache_size():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                COUNT(*) as total_keys,
                SUM(LENGTH(value)) as total_size
            FROM cache_table
        """)
        row = cursor.fetchone()
        print(f'快取鍵數量: {row[0]}')
        print(f'快取大小: {row[1] / 1024 / 1024:.2f} MB')
```

---

## 📝 檢查清單

部署前確認：

- [ ] `settings.py` 已設定資料庫快取
- [ ] 執行 `python manage.py createcachetable`
- [ ] 測試快取讀寫功能
- [ ] 確認資料庫連線正常
- [ ] 檢查快取表已建立（`SHOW TABLES LIKE 'cache_table'`）
- [ ] 測試到訪數統計功能
- [ ] 測試通知快取功能
- [ ] 啟動專案並訪問網站

---

## 🔄 從 Redis 遷移到資料庫快取

如果之前使用 Redis，現在要切換：

### 步驟 1：修改 settings.py
```python
# 從這個
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        ...
    }
}

# 改為這個
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
    }
}
```

### 步驟 2：建立快取表
```bash
python manage.py createcachetable
```

### 步驟 3：重啟服務
```bash
python manage.py runserver
```

**注意**：切換後舊的快取資料會遺失（Redis 中的資料），但這是正常的，系統會自動重建。

---

## 📚 參考資源

- [Django Cache Framework 官方文檔](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Database Caching 詳細說明](https://docs.djangoproject.com/en/stable/topics/cache/#database-caching)
- [Cache API 參考](https://docs.djangoproject.com/en/stable/topics/cache/#the-low-level-cache-api)

---

## 👨‍💻 維護資訊

- **建立日期**: 2025-10-04
- **最後更新**: 2025-10-04
- **版本**: v1.0
- **適用環境**: Windows 11 虛擬機、不支援 Docker 的環境
- **維護者**: Claude Code

---

## 🎉 總結

使用資料庫快取的優勢：
✅ **零依賴** - 不需要 Docker/Redis/其他服務
✅ **簡單設定** - 只需 1 行指令
✅ **虛擬機友善** - 完全支援虛擬機環境
✅ **效能足夠** - 中小型專案完全夠用
✅ **資料持久** - 重啟不會遺失
✅ **易於維護** - 直接用 SQL 管理

**完美適合你的 Windows 11 虛擬機環境！** 🚀
