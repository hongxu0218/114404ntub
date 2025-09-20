# petapp/views_handoff.py
import json
from typing import Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Max

from .models import HandoffTicket, HandoffMessage


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
    對應樣板：templates/AI_chat/staff_handoff.html
    """
    tickets = HandoffTicket.objects.all().only("id", "session_key", "is_open", "created_at")

    current = None
    if ticket_id:
        current = HandoffTicket.objects.prefetch_related("messages").get(id=ticket_id)

    return render(
        request,
        "AI_chat/staff_handoff.html",
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
    # ------------------------------------------------------------

    HandoffMessage.objects.create(
        ticket=t,
        sender="agent",  # 你的 model 定義使用小寫字串
        text=msg_text,
    )
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
        text="工單已結案",
    )
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
@require_POST
def api_handoff_request(request: HttpRequest):
    """
    使用者按「轉人工客服」時呼叫。
    規則：若同一 session 有「未結案」工單，沿用；否則新建。
    body(JSON): { "name": "可選，預設匿名", "contact": "可選", "last_question": "可選", "channel": "web" }
    回傳: { "ok": true, "ticket_id": 123, "reused": true/false }
    """
    session_key = _ensure_session_key(request)

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = {}

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

    return JsonResponse({"ok": True, "ticket_id": t.id, "reused": False})


@require_POST
def api_handoff_user_send(request: HttpRequest):
    """
    使用者在人工客服聊天室發訊息。
    body(JSON): {"ticket_id": <int>, "message": "text"}
    回傳: {"ok": true}
    """
    session_key = _ensure_session_key(request)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_error("invalid json", status=400)

    ticket_id = payload.get("ticket_id")
    text = (payload.get("message") or "").strip()
    if not ticket_id or not text:
        return _json_error("ticket_id and message required", status=400)

    t = get_object_or_404(HandoffTicket, id=ticket_id)

    if t.session_key != session_key:
        return _json_error("session mismatch", status=403)

    if not t.is_open:
        return _json_error("ticket closed", status=409)

    HandoffMessage.objects.create(ticket=t, sender="user", text=text)
    return JsonResponse({"ok": True})


def api_handoff_poll(request: HttpRequest):
    """
    使用者輪詢取得座席/系統訊息。
    GET: ticket_id, since(最後已讀訊息 id)
    回傳: {"ok": true, "messages":[{"id":..,"sender":"agent","text":"..."},...], "last_id": <int>}
    """
    session_key = _ensure_session_key(request)

    try:
        ticket_id = int(request.GET.get("ticket_id") or 0)
    except (TypeError, ValueError):
        return _json_error("ticket_id required", status=400)
    since = int(request.GET.get("since") or 0)

    t = get_object_or_404(HandoffTicket, id=ticket_id)
    if t.session_key != session_key:
        return _json_error("session mismatch", status=403)

    qs = t.messages.filter(id__gt=since).order_by("id").only("id", "sender", "text", "created_at")
    msgs = [{"id": m.id, "sender": m.sender, "text": m.text, "ts": m.created_at.isoformat()} for m in qs]
    last_id = msgs[-1]["id"] if msgs else since
    return JsonResponse({"ok": True, "messages": msgs, "last_id": last_id})


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
