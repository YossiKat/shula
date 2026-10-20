"""
כלי יומן גוגל לשולה.
עובד עם Service Account: היומן "יוסי קט" משותף עם כתובת ה-Service Account.
משתני סביבה: GOOGLE_SERVICE_ACCOUNT_JSON (תוכן קובץ ה-JSON), GOOGLE_CALENDAR_ID
"""
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Jerusalem")
CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

# קודי הצבע של יוסי (Google colorId)
COLOR_IDS = {
    "expense": "6",   # כתום  — הוצאות
    "done": "7",      # תכלת  — משימות שבוצעו
    "bike": "10",     # ירוק  — שיעורי אופניים
    "meeting": "11",  # אדום  — פגישות ושיחות זום
}
COLOR_NAMES = {"6": "🟠 הוצאה", "7": "🔵 בוצע", "10": "🟢 שיעור אופניים", "11": "🔴 פגישה"}

_service = None


def _svc():
    global _service
    if _service is None:
        import google_auth
        if google_auth.is_connected():
            _service = google_auth.service("calendar", "v3")
        else:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
            if not raw:
                raise RuntimeError("היומן עדיין לא מחובר (חשבון גוגל לא חובר לשולה)")
            creds = service_account.Credentials.from_service_account_info(
                json.loads(raw), scopes=["https://www.googleapis.com/auth/calendar"]
            )
            _service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return _service


def _fmt(ev: dict) -> str:
    start = ev.get("start", {})
    when = start.get("dateTime") or start.get("date", "")
    if "T" in when:
        dt = datetime.fromisoformat(when).astimezone(TZ)
        when = dt.strftime("%a %d/%m %H:%M")
    color = COLOR_NAMES.get(ev.get("colorId", ""), "")
    loc = f" @ {ev['location']}" if ev.get("location") else ""
    return f"{when} — {ev.get('summary', '(ללא כותרת)')}{loc} {color}".strip()


def get_calendar_events(days_ahead: int = 1, days_back: int = 0) -> str:
    """מחזיר את האירועים ביומן של יוסי. days_ahead = כמה ימים קדימה (1 = היום בלבד, 2 = היום ומחר). days_back = כמה ימים אחורה להציג גם."""
    now = datetime.now(TZ)
    t_min = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0)
    t_max = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0)
    res = _svc().events().list(
        calendarId=CALENDAR_ID, timeMin=t_min.isoformat(), timeMax=t_max.isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=50,
    ).execute()
    items = res.get("items", [])
    if not items:
        return "אין אירועים בטווח הזה."
    return "\n".join(_fmt(e) for e in items)


def get_events_for_date(date_iso: str) -> str:
    """מחזיר את כל האירועים ביומן של יוסי בתאריך מסוים. date_iso בפורמט YYYY-MM-DD. זה הכלי הנכון לשאלות כמו 'מה יש לי מחר' או 'מה יש ביום חמישי'."""
    day = datetime.fromisoformat(date_iso).replace(tzinfo=TZ, hour=0, minute=0, second=0)
    res = _svc().events().list(
        calendarId=CALENDAR_ID, timeMin=day.isoformat(), timeMax=(day + timedelta(days=1)).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=50,
    ).execute()
    items = res.get("items", [])
    return "\n".join(_fmt(e) for e in items) if items else f"אין אירועים ב-{day.strftime('%d/%m')}."


def search_calendar_events(query: str, days_ahead: int = 30) -> str:
    """מחפש אירועים ביומן לפי מילה (למשל 'אופניים', 'זום', שם של אדם) בטווח של days_ahead ימים קדימה."""
    now = datetime.now(TZ)
    res = _svc().events().list(
        calendarId=CALENDAR_ID, q=query, timeMin=now.isoformat(),
        timeMax=(now + timedelta(days=days_ahead)).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=30,
    ).execute()
    items = res.get("items", [])
    return "\n".join(_fmt(e) for e in items) if items else f"לא מצאתי אירועים עם '{query}'."


def create_calendar_event(
    title: str,
    start_iso: str,
    duration_minutes: int = 60,
    category: str = "meeting",
    location: str = "",
    notes: str = "",
) -> str:
    """יוצר אירוע חדש ביומן של יוסי.
    start_iso: תאריך ושעה בפורמט YYYY-MM-DDTHH:MM (שעון ישראל).
    category: אחד מ-'meeting' (פגישה/זום, אדום), 'bike' (שיעור אופניים, ירוק), 'expense' (הוצאה, כתום), 'done' (משימה שבוצעה, תכלת).
    """
    start = datetime.fromisoformat(start_iso).replace(tzinfo=TZ)
    end = start + timedelta(minutes=duration_minutes)
    body = {
        "summary": title,
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Jerusalem"},
        "colorId": COLOR_IDS.get(category, COLOR_IDS["meeting"]),
    }
    if location:
        body["location"] = location
    if notes:
        body["description"] = notes
    ev = _svc().events().insert(calendarId=CALENDAR_ID, body=body).execute()
    return f"נוצר: {_fmt(ev)}"


def delete_calendar_event(title_query: str, date_iso: str) -> str:
    """מוחק אירוע ביומן. title_query = מילה מהכותרת, date_iso = התאריך YYYY-MM-DD. מוחק רק אם נמצא אירוע אחד בדיוק."""
    day = datetime.fromisoformat(date_iso).replace(tzinfo=TZ)
    res = _svc().events().list(
        calendarId=CALENDAR_ID, q=title_query, timeMin=day.isoformat(),
        timeMax=(day + timedelta(days=1)).isoformat(), singleEvents=True,
    ).execute()
    items = res.get("items", [])
    if len(items) != 1:
        return f"נמצאו {len(items)} אירועים — צריך להיות בדיוק אחד. " + "\n".join(_fmt(e) for e in items)
    _svc().events().delete(calendarId=CALENDAR_ID, eventId=items[0]["id"]).execute()
    return f"נמחק: {_fmt(items[0])}"


CALENDAR_TOOLS = [get_events_for_date, get_calendar_events, search_calendar_events, create_calendar_event, delete_calendar_event]
