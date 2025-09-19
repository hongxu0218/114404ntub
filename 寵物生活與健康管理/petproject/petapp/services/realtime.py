# petapp/services/realtime.py
# -*- coding: utf-8 -*-
"""
簡單的 Redis Pub/Sub 推播工具，用於 SSE / WebSocket 後端發佈事件。

使用方式：
    from petapp.services.realtime import publish_update
    publish_update({"type": "ticket_created", "id": 123}, channel="staff:handoff")

必要設定：
    在 settings.py 設定
        REDIS_URL = "redis://127.0.0.1:6379/0"
    （若使用 TLS，改用 rediss://）
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import redis
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# 允許從環境 / settings 覆蓋
REDIS_URL: str = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")

_redis_client: Optional[redis.Redis] = None


def _get_client() -> redis.Redis:
    """
    取得全域 Redis 連線（懶載入 + ping 驗證）。
    連線失敗會拋出例外，方便在啟動或測試階段及早發現問題。
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(REDIS_URL)
        try:
            _redis_client.ping()
        except Exception as exc:
            logger.error("Realtime: 無法連線至 Redis：%s (url=%s)", exc, REDIS_URL)
            raise
    return _redis_client


def _to_json(payload: Any) -> str:
    """
    將 payload 轉為 JSON 字串；自動處理 datetime 等不可序列化物件。
    """
    def _default(o: Any) -> str:
        try:
            if hasattr(o, "isoformat"):
                return o.isoformat()
        except Exception:
            pass
        return str(o)

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=_default)


def publish_update(payload: Dict[str, Any], channel: str) -> None:
    """
    對指定頻道發佈一則事件（JSON 字串）。

    建議 payload 格式：
        {
          "type": "message_created" | "ticket_created" | "ticket_updated" | "ticket_closed" | ...,
          ... 其他欄位 ...,
          # 可不帶，函式會自動補
          "ts": "2025-09-17T09:00:00+08:00"
        }

    參數：
        payload: 事件內容（dict）
        channel: 頻道名稱，例如 "staff:handoff" 或 f"ticket:{ticket_id}"
    """
    if not isinstance(payload, dict):
        raise TypeError("payload 必須是 dict")

    # 自動補上伺服器時間戳
    payload.setdefault("ts", timezone.now().isoformat())

    msg = _to_json(payload)
    client = _get_client()
    client.publish(channel, msg)
    logger.debug("Realtime: published to %s -> %s", channel, msg)
