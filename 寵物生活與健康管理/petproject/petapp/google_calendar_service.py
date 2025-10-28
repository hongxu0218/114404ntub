# petapp/google_calendar_service.py
"""
Google Calendar 整合服務
自動將預約、疫苗、驅蟲等重要事項新增至使用者的 Google Calendar
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from django.conf import settings
from django.contrib.auth.models import User
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Google Calendar API 服務類別"""

    # Google Calendar API 權限範圍
    SCOPES = ['https://www.googleapis.com/auth/calendar.events']

    def __init__(self, user: User):
        """
        初始化 Google Calendar 服務

        Args:
            user: Django User 物件
        """
        self.user = user
        self.service = None

    def get_credentials(self) -> Optional[Credentials]:
        """
        取得使用者的 Google Calendar 憑證

        Returns:
            Credentials 物件或 None
        """
        try:
            # 從使用者的 Profile 取得儲存的 token
            if not hasattr(self.user, 'profile'):
                return None

            profile = self.user.profile

            # 檢查是否有儲存 Google Calendar token
            if not hasattr(profile, 'google_calendar_token') or not profile.google_calendar_token:
                return None

            # 從 JSON 字串重建憑證
            import json
            token_data = json.loads(profile.google_calendar_token)

            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=settings.GOOGLE_CALENDAR_CLIENT_ID,
                client_secret=settings.GOOGLE_CALENDAR_CLIENT_SECRET,
                scopes=self.SCOPES
            )

            # 檢查憑證是否過期，如果過期則更新
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # 儲存更新後的憑證
                self.save_credentials(creds)

            return creds

        except Exception as e:
            logger.error(f"取得 Google Calendar 憑證失敗: {e}")
            return None

    def save_credentials(self, creds: Credentials):
        """
        儲存使用者的 Google Calendar 憑證

        Args:
            creds: Credentials 物件
        """
        try:
            import json

            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'scopes': creds.scopes
            }

            profile = self.user.profile
            profile.google_calendar_token = json.dumps(token_data)
            profile.save()

            logger.info(f"已儲存使用者 {self.user.username} 的 Google Calendar 憑證")

        except Exception as e:
            logger.error(f"儲存 Google Calendar 憑證失敗: {e}")

    def get_service(self):
        """
        取得 Google Calendar API 服務物件

        Returns:
            Google Calendar API service 或 None
        """
        if self.service:
            return self.service

        try:
            creds = self.get_credentials()
            if not creds:
                logger.warning(f"使用者 {self.user.username} 尚未授權 Google Calendar")
                return None

            self.service = build('calendar', 'v3', credentials=creds)
            return self.service

        except Exception as e:
            logger.error(f"建立 Google Calendar 服務失敗: {e}")
            return None

    def create_event(
        self,
        summary: str,
        start_datetime: datetime,
        end_datetime: datetime,
        description: str = '',
        location: str = '',
        reminders: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        在使用者的 Google Calendar 中建立事件

        Args:
            summary: 事件標題
            start_datetime: 開始時間
            end_datetime: 結束時間
            description: 事件描述
            location: 地點
            reminders: 提醒設定

        Returns:
            事件 ID 或 None
        """
        try:
            service = self.get_service()
            if not service:
                return None

            # 預設提醒設定：前一天和前 1 小時
            if reminders is None:
                reminders = {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 前一天
                        {'method': 'popup', 'minutes': 60},       # 前 1 小時
                    ],
                }

            # 建立事件資料
            event = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Asia/Taipei',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Asia/Taipei',
                },
                'reminders': reminders,
            }

            # 插入事件
            created_event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            event_id = created_event.get('id')
            logger.info(f"已在 Google Calendar 建立事件: {summary} (ID: {event_id})")

            return event_id

        except HttpError as e:
            logger.error(f"Google Calendar API 錯誤: {e}")
            return None
        except Exception as e:
            logger.error(f"建立 Google Calendar 事件失敗: {e}")
            return None

    def update_event(
        self,
        event_id: str,
        summary: str = None,
        start_datetime: datetime = None,
        end_datetime: datetime = None,
        description: str = None,
        location: str = None
    ) -> bool:
        """
        更新 Google Calendar 事件

        Args:
            event_id: 事件 ID
            summary: 事件標題
            start_datetime: 開始時間
            end_datetime: 結束時間
            description: 事件描述
            location: 地點

        Returns:
            是否成功
        """
        try:
            service = self.get_service()
            if not service:
                return False

            # 先取得現有事件
            event = service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()

            # 更新欄位
            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if start_datetime:
                event['start'] = {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Asia/Taipei',
                }
            if end_datetime:
                event['end'] = {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Asia/Taipei',
                }

            # 更新事件
            service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"已更新 Google Calendar 事件: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Google Calendar API 錯誤: {e}")
            return False
        except Exception as e:
            logger.error(f"更新 Google Calendar 事件失敗: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """
        刪除 Google Calendar 事件

        Args:
            event_id: 事件 ID

        Returns:
            是否成功
        """
        try:
            service = self.get_service()
            if not service:
                return False

            service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()

            logger.info(f"已刪除 Google Calendar 事件: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Google Calendar API 錯誤: {e}")
            return False
        except Exception as e:
            logger.error(f"刪除 Google Calendar 事件失敗: {e}")
            return False

    @staticmethod
    def create_appointment_event(user: User, appointment) -> Optional[str]:
        """
        為預約建立 Google Calendar 事件

        Args:
            user: 使用者
            appointment: VetAppointment 物件

        Returns:
            事件 ID 或 None
        """
        service = GoogleCalendarService(user)

        # 組合事件資訊
        summary = f"🏥 {appointment.pet.name} 看診預約"

        # 計算開始和結束時間
        start_datetime = datetime.combine(
            appointment.slot.date,
            appointment.slot.start_time
        )
        end_datetime = datetime.combine(
            appointment.slot.date,
            appointment.slot.end_time
        )

        # 組合描述
        description = f"""
寵物：{appointment.pet.name}
診所：{appointment.slot.clinic.name if appointment.slot.clinic else '未指定'}
獸醫：{appointment.slot.doctor.user.get_full_name() if appointment.slot.doctor else '未指定'}
原因：{appointment.reason if appointment.reason else '未填寫'}
備註：{appointment.notes if appointment.notes else '無'}
聯絡電話：{appointment.contact_phone}

毛日好寵物健康管理平台
        """.strip()

        location = ''
        if appointment.slot.clinic and appointment.slot.clinic.address:
            location = appointment.slot.clinic.address

        return service.create_event(
            summary=summary,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            description=description,
            location=location
        )

    @staticmethod
    def create_vaccine_event(user: User, vaccine_record) -> Optional[str]:
        """
        為疫苗記錄建立 Google Calendar 事件

        Args:
            user: 使用者
            vaccine_record: VaccineRecord 物件

        Returns:
            事件 ID 或 None
        """
        service = GoogleCalendarService(user)

        # 組合事件資訊
        summary = f"💉 {vaccine_record.pet.name} 疫苗接種"

        # 使用疫苗接種日期，設定為全天事件的方式（使用具體時間）
        # 設定為早上 9:00 開始，持續 1 小時
        start_datetime = datetime.combine(
            vaccine_record.vaccine_date,
            datetime.min.time().replace(hour=9)
        )
        end_datetime = start_datetime + timedelta(hours=1)

        # 組合描述
        description = f"""
寵物：{vaccine_record.pet.name}
疫苗種類：{vaccine_record.get_vaccine_type_display()}
疫苗品牌：{vaccine_record.vaccine_brand if vaccine_record.vaccine_brand else '未填寫'}
接種地點：{vaccine_record.vaccine_location if vaccine_record.vaccine_location else '未填寫'}

下次接種日期：{vaccine_record.next_vaccine_date.strftime('%Y/%m/%d') if vaccine_record.next_vaccine_date else '無'}

毛日好寵物健康管理平台
        """.strip()

        location = vaccine_record.vaccine_location if vaccine_record.vaccine_location else ''

        event_id = service.create_event(
            summary=summary,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            description=description,
            location=location
        )

        # 如果有下次接種日期，也建立提醒事件
        if vaccine_record.next_vaccine_date and event_id:
            next_summary = f"💉 {vaccine_record.pet.name} 下次疫苗接種提醒"
            next_start = datetime.combine(
                vaccine_record.next_vaccine_date,
                datetime.min.time().replace(hour=9)
            )
            next_end = next_start + timedelta(hours=1)

            next_description = f"""
寵物：{vaccine_record.pet.name}
疫苗種類：{vaccine_record.get_vaccine_type_display()}
上次接種：{vaccine_record.vaccine_date.strftime('%Y/%m/%d')}

請記得帶 {vaccine_record.pet.name} 去接種疫苗！

毛日好寵物健康管理平台
            """.strip()

            service.create_event(
                summary=next_summary,
                start_datetime=next_start,
                end_datetime=next_end,
                description=next_description,
                location=location
            )

        return event_id

    @staticmethod
    def create_deworm_event(user: User, deworm_record) -> Optional[str]:
        """
        為驅蟲記錄建立 Google Calendar 事件

        Args:
            user: 使用者
            deworm_record: DewormRecord 物件

        Returns:
            事件 ID 或 None
        """
        service = GoogleCalendarService(user)

        # 組合事件資訊
        summary = f"🐛 {deworm_record.pet.name} 驅蟲"

        # 使用驅蟲日期，設定為早上 9:00 開始，持續 1 小時
        start_datetime = datetime.combine(
            deworm_record.deworm_date,
            datetime.min.time().replace(hour=9)
        )
        end_datetime = start_datetime + timedelta(hours=1)

        # 組合描述
        description = f"""
寵物：{deworm_record.pet.name}
驅蟲類型：{deworm_record.get_deworm_type_display()}
驅蟲藥品牌：{deworm_record.deworm_brand if deworm_record.deworm_brand else '未填寫'}
施藥地點：{deworm_record.deworm_location if deworm_record.deworm_location else '未填寫'}

下次驅蟲日期：{deworm_record.next_deworm_date.strftime('%Y/%m/%d') if deworm_record.next_deworm_date else '無'}

毛日好寵物健康管理平台
        """.strip()

        location = deworm_record.deworm_location if deworm_record.deworm_location else ''

        event_id = service.create_event(
            summary=summary,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            description=description,
            location=location
        )

        # 如果有下次驅蟲日期，也建立提醒事件
        if deworm_record.next_deworm_date and event_id:
            next_summary = f"🐛 {deworm_record.pet.name} 下次驅蟲提醒"
            next_start = datetime.combine(
                deworm_record.next_deworm_date,
                datetime.min.time().replace(hour=9)
            )
            next_end = next_start + timedelta(hours=1)

            next_description = f"""
寵物：{deworm_record.pet.name}
驅蟲類型：{deworm_record.get_deworm_type_display()}
上次驅蟲：{deworm_record.deworm_date.strftime('%Y/%m/%d')}

請記得幫 {deworm_record.pet.name} 進行驅蟲！

毛日好寵物健康管理平台
            """.strip()

            service.create_event(
                summary=next_summary,
                start_datetime=next_start,
                end_datetime=next_end,
                description=next_description,
                location=location
            )

        return event_id


def get_authorization_url(request) -> tuple:
    """
    取得 Google Calendar OAuth 授權網址

    Args:
        request: Django request 物件

    Returns:
        (authorization_url, state) tuple
    """
    try:
        # 建立 OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_CALENDAR_REDIRECT_URI]
                }
            },
            scopes=GoogleCalendarService.SCOPES
        )

        flow.redirect_uri = settings.GOOGLE_CALENDAR_REDIRECT_URI

        # 產生授權網址
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # 強制顯示同意畫面以取得 refresh token
        )

        return authorization_url, state

    except Exception as e:
        logger.error(f"產生 Google Calendar 授權網址失敗: {e}")
        return None, None
