# petapp/views_handoff_new.py
"""
人工客服系統 - 重新設計版本
所有 API 都有完整的錯誤處理和日誌記錄
"""
import json
import logging
import uuid
from typing import Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Max
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from .models import HandoffTicket, HandoffMessage, Notification

logger = logging.getLogger(__name__)


# ======================
# 輔助函數
# ======================

def get_session_key(request: HttpRequest) -> str:
    """獲取或創建 session key"""
    try:
        # 嘗試訪問 session，這會自動創建 session
        if not hasattr(request, 'session'):
            temp_key = f"temp_{uuid.uuid4().hex[:20]}"
            logger.error(f"No session middleware, using temporary key: {temp_key}")
            return temp_key

        # 確保 session 被創建（通過修改來觸發保存）
        if not request.session.session_key:
            request.session['_handoff_init'] = True
            request.session.modified = True

        # 再次獲取 session_key
        session_key = request.session.session_key

        # 如果還是沒有，使用臨時 key
        if not session_key:
            session_key = f"temp_{uuid.uuid4().hex[:20]}"
            logger.warning(f"Session key not created, using temporary: {session_key}")

        return session_key
    except Exception as e:
        # 如果 session 完全失敗，使用臨時 key
        temp_key = f"temp_{uuid.uuid4().hex[:20]}"
        logger.exception(f"Session error: {e}, using temporary key: {temp_key}")
        return temp_key


def json_response(success: bool = True, data: dict = None, error: str = None, status: int = 200) -> JsonResponse:
    """統一的 JSON 響應格式"""
    response_data = {"ok": success}
    if data:
        response_data.update(data)
    if error:
        response_data["error"] = error
    return JsonResponse(response_data, status=status)


def safe_create_notification(user: User, title: str, message: str, notification_type: str) -> bool:
    """安全創建通知，失敗不影響主流程"""
    try:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to create notification for user {user.id}: {e}")
        return False


# ======================
# 用戶端 API
# ======================

@csrf_exempt
@require_POST
def api_handoff_request(request: HttpRequest):
    """
    用戶發起人工客服請求
    POST /api/handoff/request/
    Body: {"name": "用戶名", "contact": "聯絡方式", "last_question": "問題", "channel": "web"}
    """
    try:
        # 獲取 session key
        session_key = get_session_key(request)
        logger.info(f"Handoff request from session: {session_key}")

        # 解析請求數據
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in request: {e}")
            data = {}

        name = (data.get("name") or "").strip() or "匿名"
        contact = (data.get("contact") or "").strip()
        last_question = (data.get("last_question") or "").strip()
        channel = (data.get("channel") or "web").strip()

        # 檢查是否已有未結案工單
        existing_ticket = HandoffTicket.objects.filter(
            session_key=session_key,
            is_open=True
        ).order_by('-created_at').first()

        if existing_ticket:
            # 重用現有工單
            logger.info(f"Reusing ticket #{existing_ticket.id}")

            # 更新資訊
            updated = False
            if existing_ticket.name != name:
                existing_ticket.name = name
                updated = True
            if contact and existing_ticket.contact != contact:
                existing_ticket.contact = contact
                updated = True
            if updated:
                existing_ticket.save()

            # 添加新問題
            if last_question:
                HandoffMessage.objects.create(
                    ticket=existing_ticket,
                    sender="user",
                    text=last_question
                )

            return json_response(success=True, data={
                "ticket_id": existing_ticket.id,
                "reused": True
            })

        # 創建新工單
        ticket = HandoffTicket.objects.create(
            session_key=session_key,
            name=name,
            contact=contact,
            channel=channel,
            is_open=True
        )
        logger.info(f"Created new ticket #{ticket.id}")

        # 添加初始訊息
        if last_question:
            HandoffMessage.objects.create(
                ticket=ticket,
                sender="user",
                text=last_question
            )

        HandoffMessage.objects.create(
            ticket=ticket,
            sender="system",
            text="已建立人工客服工單，請稍候"
        )

        # 通知員工（失敗不影響工單創建）
        staff_users = User.objects.filter(is_staff=True)
        for staff_user in staff_users:
            safe_create_notification(
                user=staff_user,
                title="新的人工客服請求",
                message=f"用戶 {name} 發起了新的客服工單 (#{ticket.id})",
                notification_type="handoff_request"
            )

        return json_response(success=True, data={
            "ticket_id": ticket.id,
            "reused": False
        })

    except Exception as e:
        logger.exception(f"Error in api_handoff_request: {e}")
        return json_response(
            success=False,
            error=f"系統錯誤: {str(e)}",
            status=500
        )


@csrf_exempt
@require_POST
def api_handoff_user_send(request: HttpRequest):
    """
    用戶發送訊息
    POST /api/handoff/user/send/
    Body: {"ticket_id": 123, "message": "訊息內容"}
    """
    try:
        session_key = get_session_key(request)

        # 解析請求
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return json_response(success=False, error="無效的 JSON 格式", status=400)

        ticket_id = data.get("ticket_id")
        message = (data.get("message") or "").strip()

        if not ticket_id or not message:
            return json_response(success=False, error="缺少必要參數", status=400)

        # 獲取工單
        try:
            ticket = HandoffTicket.objects.get(id=ticket_id)
        except HandoffTicket.DoesNotExist:
            return json_response(success=False, error="工單不存在", status=404)

        # 驗證 session
        if ticket.session_key != session_key:
            return json_response(success=False, error="無權操作此工單", status=403)

        # 檢查工單狀態
        if not ticket.is_open:
            return json_response(success=False, error="工單已關閉", status=409)

        # 創建訊息
        HandoffMessage.objects.create(
            ticket=ticket,
            sender="user",
            text=message
        )
        logger.info(f"User message added to ticket #{ticket_id}")

        # 通知員工（失敗不影響訊息發送）
        staff_users = User.objects.filter(is_staff=True)
        for staff_user in staff_users:
            safe_create_notification(
                user=staff_user,
                title="客服工單有新訊息",
                message=f"工單 #{ticket.id} 收到用戶新訊息",
                notification_type="handoff_message"
            )

        return json_response(success=True)

    except Exception as e:
        logger.exception(f"Error in api_handoff_user_send: {e}")
        return json_response(
            success=False,
            error=f"系統錯誤: {str(e)}",
            status=500
        )


@csrf_exempt
@require_POST
def api_handoff_user_end(request: HttpRequest):
    """
    用戶結束對話
    POST /api/handoff/user/end/
    Body: {"ticket_id": 123}
    """
    try:
        session_key = get_session_key(request)

        # 解析請求
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return json_response(success=False, error="無效的 JSON 格式", status=400)

        ticket_id = data.get("ticket_id")

        if not ticket_id:
            return json_response(success=False, error="缺少 ticket_id", status=400)

        # 獲取工單
        try:
            ticket = HandoffTicket.objects.get(id=ticket_id)
        except HandoffTicket.DoesNotExist:
            return json_response(success=False, error="工單不存在", status=404)

        # 驗證 session
        if ticket.session_key != session_key:
            return json_response(success=False, error="無權操作此工單", status=403)

        # 如果已關閉，直接返回成功
        if not ticket.is_open:
            return json_response(success=True)

        # 關閉工單
        ticket.is_open = False
        ticket.save(update_fields=['is_open'])
        logger.info(f"User ended ticket #{ticket_id}")

        # 添加系統訊息
        HandoffMessage.objects.create(
            ticket=ticket,
            sender="system",
            text="🔚 用戶主動結束對話"
        )

        # 通知員工（失敗不影響結束操作）
        staff_users = User.objects.filter(is_staff=True)
        for staff_user in staff_users:
            safe_create_notification(
                user=staff_user,
                title="客服工單已結束",
                message=f"用戶主動結束了工單 #{ticket.id}",
                notification_type="handoff_closed"
            )

        return json_response(success=True)

    except Exception as e:
        logger.exception(f"Error in api_handoff_user_end: {e}")
        return json_response(
            success=False,
            error=f"系統錯誤: {str(e)}",
            status=500
        )


@csrf_exempt
def api_handoff_poll(request: HttpRequest):
    """
    用戶輪詢新訊息
    GET /api/handoff/poll/?ticket_id=123&since=0
    """
    try:
        session_key = get_session_key(request)

        # 獲取參數
        try:
            ticket_id = int(request.GET.get("ticket_id", 0))
            since = int(request.GET.get("since", 0))
        except (TypeError, ValueError):
            return json_response(success=False, error="無效的參數", status=400)

        if not ticket_id:
            return json_response(success=False, error="缺少 ticket_id", status=400)

        # 獲取工單
        try:
            ticket = HandoffTicket.objects.get(id=ticket_id)
        except HandoffTicket.DoesNotExist:
            return json_response(success=False, error="工單不存在", status=404)

        # 驗證 session
        if ticket.session_key != session_key:
            return json_response(success=False, error="無權操作此工單", status=403)

        # 獲取新訊息
        messages = ticket.messages.filter(id__gt=since).order_by('id')
        messages_data = [
            {
                "id": msg.id,
                "sender": msg.sender,
                "text": msg.text,
                "ts": msg.created_at.isoformat()
            }
            for msg in messages
        ]

        last_id = messages_data[-1]["id"] if messages_data else since

        return json_response(success=True, data={
            "messages": messages_data,
            "last_id": last_id,
            "is_open": ticket.is_open
        })

    except Exception as e:
        logger.exception(f"Error in api_handoff_poll: {e}")
        return json_response(
            success=False,
            error=f"系統錯誤: {str(e)}",
            status=500
        )


# ======================
# 員工端視圖
# ======================

@staff_member_required(login_url="account_login")
def handoff_console(request: HttpRequest, ticket_id: Optional[int] = None):
    """客服控台"""
    tickets = HandoffTicket.objects.all().order_by('-is_open', '-created_at')

    current = None
    current_assigned = False
    if ticket_id:
        try:
            current = HandoffTicket.objects.prefetch_related('messages').get(id=ticket_id)
            # 檢查是否已被接手
            current_assigned = HandoffMessage.objects.filter(
                ticket=current,
                sender__in=["agent", "system"],
                text__icontains="接手您的工單"
            ).exists() or HandoffMessage.objects.filter(
                ticket=current,
                sender="agent"
            ).exists()
        except HandoffTicket.DoesNotExist:
            pass

    return render(request, 'ai_chat/staff_handoff.html', {
        'tickets': tickets,
        'current': current,
        'current_assigned': current_assigned
    })


@staff_member_required(login_url="account_login")
@require_POST
def handoff_agent_reply(request: HttpRequest, ticket_id: int):
    """客服回覆"""
    try:
        ticket = get_object_or_404(HandoffTicket, id=ticket_id)

        if not ticket.is_open:
            return json_response(success=False, error="工單已關閉", status=409)

        # 獲取訊息
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body.decode('utf-8'))
                message = (data.get("message") or "").strip()
            except json.JSONDecodeError:
                message = ""
        else:
            message = (request.POST.get("message") or "").strip()

        if not message:
            return json_response(success=False, error="訊息不能為空", status=400)

        # 第一次回覆時添加接單訊息
        if not HandoffMessage.objects.filter(
            ticket=ticket,
            sender="system",
            text__icontains="接手您的工單"
        ).exists():
            agent_name = request.user.get_full_name() or request.user.username or "客服"
            HandoffMessage.objects.create(
                ticket=ticket,
                sender="system",
                text=f"🎧 已有客服（{agent_name}）接手您的工單，稍候將與您聯繫。"
            )

        # 創建回覆
        HandoffMessage.objects.create(
            ticket=ticket,
            sender="agent",
            text=message
        )

        return json_response(success=True)

    except Exception as e:
        logger.exception(f"Error in handoff_agent_reply: {e}")
        return json_response(success=False, error=f"系統錯誤: {str(e)}", status=500)


@staff_member_required(login_url="account_login")
@require_POST
def handoff_agent_close(request: HttpRequest, ticket_id: int):
    """客服關閉工單"""
    try:
        ticket = get_object_or_404(HandoffTicket, id=ticket_id)

        if not ticket.is_open:
            return redirect('handoff_console_ticket', ticket_id=ticket.id)

        ticket.is_open = False
        ticket.save(update_fields=['is_open'])

        HandoffMessage.objects.create(
            ticket=ticket,
            sender="system",
            text="🔒 工單已結案，感謝您的諮詢！如有其他問題，請重新發起人工客服。"
        )

        return redirect('handoff_console_ticket', ticket_id=ticket.id)

    except Exception as e:
        logger.exception(f"Error in handoff_agent_close: {e}")
        return redirect('handoff_console')


@staff_member_required(login_url="account_login")
@require_POST
def handoff_agent_accept(request: HttpRequest, ticket_id: int):
    """客服接單"""
    try:
        ticket = get_object_or_404(HandoffTicket, id=ticket_id)

        if not ticket.is_open:
            return redirect('handoff_console_ticket', ticket_id=ticket.id)

        # 避免重複接單訊息
        if not HandoffMessage.objects.filter(
            ticket=ticket,
            sender="system",
            text__icontains="接手您的工單"
        ).exists():
            agent_name = request.user.get_full_name() or request.user.username or "客服"
            HandoffMessage.objects.create(
                ticket=ticket,
                sender="system",
                text=f"🎧 已有客服（{agent_name}）接手您的工單，稍候將與您聯繫。"
            )

        return redirect('handoff_console_ticket', ticket_id=ticket.id)

    except Exception as e:
        logger.exception(f"Error in handoff_agent_accept: {e}")
        return redirect('handoff_console')


@staff_member_required(login_url="account_login")
def handoff_staff_tickets_poll(request: HttpRequest):
    """員工端工單列表輪詢"""
    try:
        tickets = list(HandoffTicket.objects.all().order_by('-is_open', '-created_at'))

        if not tickets:
            return json_response(success=True, data={
                "unclaimed": [],
                "open": [],
                "closed": []
            })

        # 檢查是否有客服回覆
        ticket_ids = [t.id for t in tickets]
        agent_ticket_ids = set(
            HandoffMessage.objects.filter(
                ticket_id__in=ticket_ids,
                sender="agent"
            ).values_list("ticket_id", flat=True).distinct()
        )

        accept_ticket_ids = set(
            HandoffMessage.objects.filter(
                ticket_id__in=ticket_ids,
                sender="system",
                text__icontains="接手您的工單"
            ).values_list("ticket_id", flat=True).distinct()
        )

        # 最後訊息 ID
        last_msg_ids = {
            row["ticket_id"]: row["last_id"]
            for row in HandoffMessage.objects.filter(
                ticket_id__in=ticket_ids
            ).values("ticket_id").annotate(last_id=Max("id"))
        }

        # 分組
        unclaimed, opened, closed = [], [], []

        for ticket in tickets:
            assigned = (ticket.id in agent_ticket_ids) or (ticket.id in accept_ticket_ids)

            item = {
                "id": ticket.id,
                "session_key": ticket.session_key,
                "is_open": ticket.is_open,
                "assigned": assigned,
                "created_at": ticket.created_at.isoformat(),
                "last_msg_id": last_msg_ids.get(ticket.id, 0)
            }

            if not ticket.is_open:
                closed.append(item)
            elif not assigned:
                unclaimed.append(item)
            else:
                opened.append(item)

        return json_response(success=True, data={
            "unclaimed": unclaimed,
            "open": opened,
            "closed": closed
        })

    except Exception as e:
        logger.exception(f"Error in handoff_staff_tickets_poll: {e}")
        return json_response(success=False, error=f"系統錯誤: {str(e)}", status=500)


@staff_member_required(login_url="account_login")
def handoff_staff_poll(request: HttpRequest, ticket_id: int):
    """員工端訊息輪詢"""
    try:
        since = int(request.GET.get("since", 0))

        ticket = get_object_or_404(HandoffTicket, id=ticket_id)

        messages = ticket.messages.filter(id__gt=since).order_by('id')
        messages_data = [
            {
                "id": msg.id,
                "sender": msg.sender,
                "text": msg.text,
                "ts": msg.created_at.isoformat()
            }
            for msg in messages
        ]

        last_id = messages_data[-1]["id"] if messages_data else since

        return json_response(success=True, data={
            "messages": messages_data,
            "last_id": last_id
        })

    except Exception as e:
        logger.exception(f"Error in handoff_staff_poll: {e}")
        return json_response(success=False, error=f"系統錯誤: {str(e)}", status=500)
