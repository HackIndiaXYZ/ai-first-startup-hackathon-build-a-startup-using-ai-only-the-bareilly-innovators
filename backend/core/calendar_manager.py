"""
SIVI AI — Google Calendar Manager Module
Voice-controlled Google Calendar integration.
Requires: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
Requires: credentials.json from Google Cloud Console
"""

import os
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("sivi.calendar")

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    _gcal_available = True
except ImportError:
    _gcal_available = False

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDS_FILE = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", "token.json")


class CalendarManager:
    def __init__(self):
        self.service = None
        if not _gcal_available:
            print(" Google Calendar dependencies missing.")
            return
        self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f" Token refresh failed: {e}")
                    creds = None
            if not creds and os.path.exists(CREDS_FILE):
                flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            elif not creds:
                print(" credentials.json not found. Calendar unavailable.")
                return
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        try:
            self.service = build("calendar", "v3", credentials=creds)
            print(" Google Calendar connected.")
        except Exception as e:
            print(f" Calendar connection failed: {e}")

    def get_today_events(self) -> str:
        if not self.service:
            return "Google Calendar not configured."

        # Use timezone-aware UTC datetime (fixes deprecation warning)
        now = datetime.now(tz=timezone.utc)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

        try:
            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=end_of_day.isoformat(),
                maxResults=5,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])
            if not events:
                return "You have no events scheduled for today."
            summaries = [e.get("summary", "Unnamed event") for e in events]
            return "Today's events: " + ", ".join(summaries) + "."
        except Exception as e:
            return f"Calendar error: {e}"

    def create_event(self, title: str, hours_from_now: int = 1) -> str:
        if not self.service:
            return "Google Calendar not configured."
        if not title.strip():
            return "Please provide an event title."

        # Use timezone-aware UTC for API calls
        start = datetime.now(tz=timezone.utc) + timedelta(hours=hours_from_now)
        end = start + timedelta(hours=1)

        event = {
            "summary": title,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
        }
        try:
            self.service.events().insert(calendarId="primary", body=event).execute()
            return f"Event '{title}' created for {hours_from_now} hour(s) from now."
        except Exception as e:
            return f"Failed to create event: {e}"

    def quick_add_event(self, text: str) -> str:
        """Use Google Calendar NLP to quickly add an event from natural language."""
        if not self.service:
            return "Google Calendar not configured."
        if not text.strip():
            return "Please provide event details."
            
        try:
            event = self.service.events().quickAdd(calendarId='primary', text=text).execute()
            
            # Format output nicely
            summary = event.get('summary', 'Event')
            start_dt = event.get('start', {}).get('dateTime')
            if start_dt:
                try:
                    dt = datetime.fromisoformat(start_dt)
                    time_str = dt.strftime("%d %b %I:%M %p")
                except:
                    time_str = start_dt
            else:
                time_str = event.get('start', {}).get('date', 'today')
                
            loc = event.get('location', '')
            loc_str = f" at {loc}" if loc else ""
                
            return f"Scheduled: {summary} on {time_str}{loc_str}."
        except Exception as e:
            return f"Failed to schedule via natural language: {e}"

    def get_today_events_list(self) -> list:
        """Returns a structured list of today's events for UI rendering."""
        if not self.service:
            return []

        from zoneinfo import ZoneInfo
        ist = ZoneInfo("Asia/Kolkata")
        now_ist = datetime.now(tz=ist)
        # Compute start and end of today in IST, then convert to UTC for the API
        start_of_day_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_ist = now_ist.replace(hour=23, minute=59, second=59, microsecond=0)

        try:
            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=start_of_day_ist.isoformat(),
                timeMax=end_of_day_ist.isoformat(),
                maxResults=10,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])
            
            out = []
            for e in events:
                summary = e.get("summary", "Busy")
                location = e.get("location", "")
                start = e.get("start", {}).get("dateTime")
                if not start:
                    start_str = "All Day"
                else:
                    dt = datetime.fromisoformat(start)
                    start_str = dt.strftime("%I:%M %p")
                
                out.append({
                    "title": summary,
                    "time": start_str,
                    "location": location
                })
            return out
        except Exception as e:
            logger.error(f"Calendar list error: {e}")
            return []


calendar_manager = CalendarManager()
