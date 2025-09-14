# petapp/views_staff.py
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from typing import Optional
from .models import HandoffTicket, HandoffMessage

@staff_member_required(login_url='account_login')  # ← 明確指定登入頁
def handoff_console(request: HttpRequest, ticket_id: Optional[int] = None):
    tickets = HandoffTicket.objects.all().only("id", "session_key", "is_open", "created_at")
    current = None
    if ticket_id:
        current = (HandoffTicket.objects.prefetch_related("messages").get(id=ticket_id))
    return render(request, "AI_chat/staff_handoff.html", {"tickets": tickets, "current": current})

@staff_member_required(login_url='account_login')
@require_POST
def agent_reply(request: HttpRequest, ticket_id: int):
    ticket = get_object_or_404(HandoffTicket, id=ticket_id)
    if not ticket.is_open:
        return HttpResponseBadRequest("Ticket is closed")

    msg_text = None
    if request.content_type and "application/json" in request.content_type.lower():
        try:
            payload = json.loads(request.body.decode("utf-8"))
            msg_text = (payload.get("message") or "").strip()
        except Exception:
            msg_text = ""
    else:
        msg_text = (request.POST.get("message") or "").strip()

    if not msg_text:
        return HttpResponseBadRequest("message required")

    HandoffMessage.objects.create(
        ticket=ticket,
        sender=HandoffMessage.Sender.AGENT,
        text=msg_text,
    )
    return JsonResponse({"ok": True})

@staff_member_required(login_url='account_login')
@require_POST
def agent_close(request: HttpRequest, ticket_id: int):
    ticket = get_object_or_404(HandoffTicket, id=ticket_id)
    if not ticket.is_open:
        return redirect("handoff_console_ticket", ticket_id=ticket.id)

    ticket.is_open = False
    ticket.save(update_fields=["is_open", "updated_at"])
    HandoffMessage.objects.create(
        ticket=ticket,
        sender=HandoffMessage.Sender.SYSTEM,
        text="工單已結案",
    )
    return redirect("handoff_console_ticket", ticket_id=ticket.id)
