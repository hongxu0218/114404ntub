# petapp/views_handoff.py
import json
from typing import Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Max

from .models import HandoffTicket, HandoffMessage, Notification
from django.contrib.auth.models import User


# ----------------------------
# 共用小工具
# ----------------------------
def _ensure_session_key(request: HttpRequest) -> str:
    """確保匿名使用者也有 session_key 可追蹤"""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": message}, status=status)


# ----------------------------
# Staff Console（職員端）
# ----------------------------
@staff_member_required(login_url="account_login")
def handoff_console(request: HttpRequest, ticket_id: Optional[int] = None):
    """
    客服控台頁：左邊工單清單，右邊顯示選取工單的聊天室。
    對應樣板：templates/ai_chat/staff_handoff.html
    """
    tickets = HandoffTicket.objects.all().only("id", "session_key", "is_open", "created_at")

    current = None
    if ticket_id:
        current = HandoffTicket.objects.prefetch_related("messages").get(id=ticket_id)

    return render(
        request,
        "ai_chat/staff_handoff.html",
        {"tickets": tickets, "current": current},
    )


@staff_member_required(login_url="account_login")
@require_POST
def handoff_agent_reply(request: HttpRequest, ticket_id: int):
    """
    職員在控台回覆訊息。
    - 接受 JSON: {"message": "..."} 或 form POST: message=...
    - 回傳: {"ok": true}
    - 第一次回覆前會自動新增一則 system 訊息通知「已接單」
    """
    t = get_object_or_404(HandoffTicket, id=ticket_id)
    if not t.is_open:
        return _json_error("工單已結案，無法回覆。", status=409)

    # 取文字
    if request.content_type and "application/json" in request.content_type.lower():
        try:
            payload = json.loads(request.body.decode("utf-8"))
            msg_text = (payload.get("message") or "").strip()
        except Exception:
            msg_text = ""
    else:
        msg_text = (request.POST.get("message") or "").strip()

    if not msg_text:
        return _json_error("message 欄位必填。", status=400)

    # --- 第一次回覆前，自動補「已接單」system 訊息（只發一次） ---
    if not HandoffMessage.objects.filter(
        ticket=t, sender="system", text__icontains="接手您的工單"
    ).exists():
        # 若 model 有 assigned_to / accepted_at 欄位則順手標記
        changed = False
        if hasattr(t, "assigned_to") and getattr(t, "assigned_to_id", None) != request.user.id:
            t.assigned_to = request.user
            changed = True
        if hasattr(t, "accepted_at") and getattr(t, "accepted_at", None) is None:
            t.accepted_at = timezone.now()
            changed = True
        if changed:
            try:
                t.save()
            except Exception:
                pass

        agent_name = (
            getattr(request.user, "get_full_name", lambda: "")()
            or getattr(request.user, "username", None)
            or "客服"
        )
        HandoffMessage.objects.create(
            ticket=t,
            sender="system",
            text=f"🎧 已有客服（{agent_name}）接手您的工單，稍候將與您聯繫。",
        )

        # 通知用戶有客服接手了工單（如果工單有關聯的用戶）
        try:
            if hasattr(t, 'user') and t.user:
                Notification.objects.create(
                    user=t.user,
                    title="客服已接手您的工單",
                    message=f"客服 {agent_name} 已接手您的工單 #{t.id}，稍候將與您聯繫",
                    notification_type="handoff_message"
                )
        except Exception:
            pass  # 通知失敗不影響回覆
    # ------------------------------------------------------------

    HandoffMessage.objects.create(
        ticket=t,
        sender="agent",  # 你的 model 定義使用小寫字串
        text=msg_text,
    )

    # 通知用戶有新的客服回覆（如果工單有關聯的用戶）
    try:
        if hasattr(t, 'user') and t.user:
            Notification.objects.create(
                user=t.user,
                title="客服已回覆",
                message=f"您的客服工單 #{t.id} 有新回覆",
                notification_type="handoff_message"
            )
    except Exception:
        pass  # 通知失敗不影響回覆

    return JsonResponse({"ok": True})


@staff_member_required(login_url="account_login")
@require_POST
def handoff_agent_close(request: HttpRequest, ticket_id: int):
    """
    結案：將工單設為 is_open=False，並留下系統訊息。
    成功後導回該工單頁面。
    """
    t = get_object_or_404(HandoffTicket, id=ticket_id)
    if not t.is_open:
        return redirect("handoff_console_ticket", ticket_id=t.id)

    t.is_open = False
    t.save(update_fields=["is_open"])  # 你的 model 沒有 updated_at，就只存 is_open

    HandoffMessage.objects.create(
        ticket=t,
        sender="system",
        text="🔒 工單已結案，感謝您的諮詢！如有其他問題，請重新發起人工客服。",
    )

    # 通知用戶工單已結案（如果工單有關聯的用戶）
    try:
        if hasattr(t, 'user') and t.user:
            Notification.objects.create(
                user=t.user,
                title="客服工單已結束",
                message=f"您的客服工單 #{t.id} 已由客服結案",
                notification_type="handoff_closed"
            )
    except Exception:
        pass  # 通知失敗不影響結案

    return redirect("handoff_console_ticket", ticket_id=t.id)


@staff_member_required(login_url="account_login")
@require_POST
def handoff_agent_accept(request: HttpRequest, ticket_id: int):
    """
    （可選）手動「接單」：座席點擊接單按鈕即發出 system 訊息告知使用者。
    成功後導回該工單頁面。
    """
    t = get_object_or_404(HandoffTicket, id=ticket_id)
    if not t.is_open:
        return redirect("handoff_console_ticket", ticket_id=t.id)

    # 若 model 有欄位就同步標記
    changed = False
    if hasattr(t, "assigned_to") and getattr(t, "assigned_to_id", None) != request.user.id:
        t.assigned_to = request.user
        changed = True
    if hasattr(t, "accepted_at") and getattr(t, "accepted_at", None) is None:
        t.accepted_at = timezone.now()
        changed = True
    if changed:
        try:
            t.save()
        except Exception:
            pass

    # 避免重覆發同一則通知
    if not HandoffMessage.objects.filter(
        ticket=t, sender="system", text__icontains="接手您的工單"
    ).exists():
        agent_name = (
            getattr(request.user, "get_full_name", lambda: "")()
            or getattr(request.user, "username", None)
            or "客服"
        )
        HandoffMessage.objects.create(
            ticket=t,
            sender="system",
            text=f"🎧 已有客服（{agent_name}）接手您的工單，稍候將與您聯繫。",
        )

        # 通知用戶有客服接手了工單（如果工單有關聯的用戶）
        try:
            if hasattr(t, 'user') and t.user:
                Notification.objects.create(
                    user=t.user,
                    title="客服已接手您的工單",
                    message=f"客服 {agent_name} 已接手您的工單 #{t.id}，稍候將與您聯繫",
                    notification_type="handoff_message"
                )
        except Exception:
            pass  # 通知失敗不影響回覆

    return redirect("handoff_console_ticket", ticket_id=t.id)


# ----------------------------
# Staff：工單清單輪詢（左側欄即時更新）
# ----------------------------
@staff_member_required(login_url="account_login")
def handoff_staff_tickets_poll(request: HttpRequest):
    """
    供控台左側工單清單即時更新：
    回傳三組分區：unclaimed / open / closed，各含精簡欄位。
    未接手 = 未結案 且 尚無 agent 訊息（或未發出「接手您的工單」系統訊息，或沒有 assigned_to）
    """
    tickets = list(HandoffTicket.objects.all().only("id", "session_key", "is_open", "created_at"))

    if not tickets:
        return JsonResponse({"ok": True, "unclaimed": [], "open": [], "closed": []})

    t_ids = [t.id for t in tickets]

    # 有沒有座席回覆過
    agent_tids = set(
        HandoffMessage.objects.filter(ticket_id__in=t_ids, sender="agent")
        .values_list("ticket_id", flat=True)
        .distinct()
    )
    # 有沒有系統「已接手」通知
    accept_tids = set(
        HandoffMessage.objects.filter(ticket_id__in=t_ids, sender="system", text__icontains="接手您的工單")
        .values_list("ticket_id", flat=True)
        .distinct()
    )
    # 每個 ticket 最後訊息 id（給前端做變更偵測用）
    last_ids = {
        row["ticket_id"]: row["last_id"]
        for row in HandoffMessage.objects.filter(ticket_id__in=t_ids)
        .values("ticket_id")
        .annotate(last_id=Max("id"))
    }

    # 分組
    unclaimed, opened, closed = [], [], []
    for t in sorted(tickets, key=lambda x: x.created_at, reverse=True):
        # 若 model 有 assigned_to，可直接視為已接手
        has_assigned_field = hasattr(t, "assigned_to_id")
        assigned_flag = bool(getattr(t, "assigned_to_id", None)) if has_assigned_field else False

        assigned = assigned_flag or (t.id in agent_tids) or (t.id in accept_tids)
        item = {
            "id": t.id,
            "session_key": t.session_key,
            "is_open": t.is_open,
            "assigned": bool(assigned),
            "created_at": t.created_at.isoformat(),
            "last_msg_id": last_ids.get(t.id, 0),
        }
        if not t.is_open:
            closed.append(item)
        elif not assigned:
            unclaimed.append(item)
        else:
            opened.append(item)

    return JsonResponse({"ok": True, "unclaimed": unclaimed, "open": opened, "closed": closed})


# ----------------------------
# User-facing APIs（使用者端）
# ----------------------------
@csrf_exempt
@require_POST
def api_handoff_request(request: HttpRequest):
    """
    使用者按「轉人工客服」時呼叫。
    規則：若同一 session 有「未結案」工單，沿用；否則新建。
    body(JSON): { "name": "可選，預設匿名", "contact": "可選", "last_question": "可選", "channel": "web" }
    回傳: { "ok": true, "ticket_id": 123, "reused": true/false }
    """
    try:
        session_key = _ensure_session_key(request)

        try:
            data = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            data = {}
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error in api_handoff_request initialization: {e}")
        return _json_error(f"Internal server error: {str(e)}", status=500)

    name = (data.get("name") or "").strip() or "匿名"
    contact = (data.get("contact") or "").strip()
    last_question = (data.get("last_question") or "").strip()
    channel = (data.get("channel") or "web").strip() or "web"

    # 先找「同一 session 的未結案工單」
    t = (
        HandoffTicket.objects.filter(session_key=session_key, is_open=True)
        .order_by("-created_at")
        .first()
    )

    if t:
        fields = []
        # 你的 model 有 name/contact/channel，就直接更新；沒「last_question」欄位，改用訊息紀錄
        if t.name != name:
            t.name = name
            fields.append("name")
        if contact and t.contact != contact:
            t.contact = contact
            fields.append("contact")
        if t.channel != channel:
            t.channel = channel
            fields.append("channel")
        if fields:
            t.save(update_fields=fields)

        # 若有新的最後問題，用訊息附加（避免覆蓋舊資料）
        if last_question:
            HandoffMessage.objects.create(ticket=t, sender="user", text=last_question)

        return JsonResponse({"ok": True, "ticket_id": t.id, "reused": True})

    # 找不到才新建
    t = HandoffTicket.objects.create(
        session_key=session_key,
        name=name,
        contact=contact,
        channel=channel,
        is_open=True,
        created_at=timezone.now(),  # auto_now_add 仍會生效；顯式給也不影響
    )

    # 若有最後問題，把它當作首則使用者訊息；再補一則系統提示
    if last_question:
        HandoffMessage.objects.create(ticket=t, sender="user", text=last_question)
    HandoffMessage.objects.create(ticket=t, sender="system", text="已建立人工客服工單，請稍候")

    # 創建新工單通知給所有員工（即使失敗也不影響工單創建）
    try:
        staff_users = User.objects.filter(is_staff=True)
        for staff_user in staff_users:
            Notification.objects.create(
                user=staff_user,
                title="新的人工客服請求",
                message=f"用戶 {name} 發起了新的客服工單 (#{t.id})",
                notification_type="handoff_request"
            )
    except Exception as e:
        # 記錄錯誤但不影響工單創建的成功返回
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to create notifications for handoff ticket {t.id}: {e}")

    return JsonResponse({"ok": True, "ticket_id": t.id, "reused": False})


@csrf_exempt
@require_POST
def api_handoff_user_end(request: HttpRequest):
    """
    使用者主動結束人工客服會話。
    body(JSON): {"ticket_id": <int>}
    回傳: {"ok": true}
    """
    try:
        session_key = _ensure_session_key(request)

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return _json_error("invalid json", status=400)

        ticket_id = payload.get("ticket_id")
        if not ticket_id:
            return _json_error("ticket_id required", status=400)

        try:
            t = HandoffTicket.objects.get(id=ticket_id)
        except HandoffTicket.DoesNotExist:
            return _json_error("ticket not found", status=404)

        if t.session_key != session_key:
            return _json_error("session mismatch", status=403)

        if not t.is_open:
            return JsonResponse({"ok": True})  # 已經結案了

        # 結案並留下用戶主動結束的訊息
        t.is_open = False
        t.save(update_fields=["is_open"])
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error in api_handoff_user_end: {e}")
        return _json_error(f"Internal server error: {str(e)}", status=500)

    HandoffMessage.objects.create(
        ticket=t,
        sender="system",
        text="🔚 用戶主動結束對話",
    )

    # 通知所有員工用戶主動結束了工單（即使失敗也不影響結束操作）
    try:
        staff_users = User.objects.filter(is_staff=True)
        for staff_user in staff_users:
            Notification.objects.create(
                user=staff_user,
                title="客服工單已結束",
                message=f"用戶主動結束了工單 #{t.id}",
                notification_type="handoff_closed"
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to create notifications for ticket end {t.id}: {e}")

    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def api_handoff_user_send(request: HttpRequest):
    """
    使用者在人工客服聊天室發訊息。
    body(JSON): {"ticket_id": <int>, "message": "text"}
    回傳: {"ok": true}
    """
    try:
        session_key = _ensure_session_key(request)

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return _json_error("invalid json", status=400)

        ticket_id = payload.get("ticket_id")
        text = (payload.get("message") or "").strip()
        if not ticket_id or not text:
            return _json_error("ticket_id and message required", status=400)

        try:
            t = HandoffTicket.objects.get(id=ticket_id)
        except HandoffTicket.DoesNotExist:
            return _json_error("ticket not found", status=404)

        if t.session_key != session_key:
            return _json_error("session mismatch", status=403)

        if not t.is_open:
            return _json_error("ticket closed", status=409)

        HandoffMessage.objects.create(ticket=t, sender="user", text=text)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error in api_handoff_user_send: {e}")
        return _json_error(f"Internal server error: {str(e)}", status=500)

    # 通知所有員工有新的用戶訊息（即使失敗也不影響訊息發送）
    try:
        staff_users = User.objects.filter(is_staff=True)
        for staff_user in staff_users:
            Notification.objects.create(
                user=staff_user,
                title="客服工單有新訊息",
                message=f"工單 #{t.id} 收到用戶新訊息",
                notification_type="handoff_message"
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to create notifications for user message in ticket {t.id}: {e}")

    return JsonResponse({"ok": True})


@csrf_exempt
def api_handoff_poll(request: HttpRequest):
    """
    使用者輪詢取得座席/系統訊息。
    GET: ticket_id, since(最後已讀訊息 id)
    回傳: {"ok": true, "messages":[{"id":..,"sender":"agent","text":"..."},...], "last_id": <int>}
    """
    try:
        session_key = _ensure_session_key(request)

        try:
            ticket_id = int(request.GET.get("ticket_id") or 0)
        except (TypeError, ValueError):
            return _json_error("ticket_id required", status=400)
        since = int(request.GET.get("since") or 0)

        try:
            t = HandoffTicket.objects.get(id=ticket_id)
        except HandoffTicket.DoesNotExist:
            return _json_error("ticket not found", status=404)

        if t.session_key != session_key:
            return _json_error("session mismatch", status=403)

        qs = t.messages.filter(id__gt=since).order_by("id").only("id", "sender", "text", "created_at")
        msgs = [{"id": m.id, "sender": m.sender, "text": m.text, "ts": m.created_at.isoformat()} for m in qs]
        last_id = msgs[-1]["id"] if msgs else since
        return JsonResponse({"ok": True, "messages": msgs, "last_id": last_id, "is_open": t.is_open})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error in api_handoff_poll: {e}")
        return _json_error(f"Internal server error: {str(e)}", status=500)


# 員工輪詢：取 ticket 的新訊息（since 之後）
@staff_member_required(login_url="account_login")
def handoff_staff_poll(request: HttpRequest, ticket_id: int):
    try:
        since = int(request.GET.get("since") or 0)
    except (TypeError, ValueError):
        since = 0

    t = get_object_or_404(HandoffTicket, id=ticket_id)
    qs = t.messages.filter(id__gt=since).order_by("id").only("id", "sender", "text", "created_at")
    msgs = [{"id": m.id, "sender": m.sender, "text": m.text, "ts": m.created_at.isoformat()} for m in qs]
    last_id = msgs[-1]["id"] if msgs else since
    return JsonResponse({"ok": True, "messages": msgs, "last_id": last_id})