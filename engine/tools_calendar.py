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
    "mentors": "5",   # צהוב  — מפגשי תוכנית המנטורים (קבוצת פיברו)
    "monday": "2",    # ירוק בהיר — כל מה שמגיע מה-monday
    "personal_meal": "8",  # אפור — ארוחות (אחרים)
}
COLOR_NAMES = {"6": "🟠 הוצאה", "7": "🔵 בוצע", "10": "🟢 שיעור אופניים", "11": "🔴 פגישה", "5": "🟡 מנטורים", "2": "🟢 הכנסה או monday"}

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


def _extra_calendars():
    """יומנים לקריאה בלבד מהחשבון הנוסף (Yossi@anycan.ai) — מוצגים יחד עם היומן הראשי. אירועים חדשים נכנסים רק ל"יוסי קט"."""
    import google_auth
    out = []
    for acct in google_auth.connected_accounts():
        if acct != google_auth.MAIN:
            out.append((google_auth.service("calendar", "v3", acct), "primary", google_auth.label(acct)))
    return out


def _list_all(**kwargs) -> list[dict]:
    """אירועים מהיומן הראשי ומהיומנים הנוספים, ממוינים לפי שעה. אירוע מיומן נוסף מסומן בשם החשבון."""
    items = _svc().events().list(calendarId=CALENDAR_ID, **kwargs).execute().get("items", [])
    try:
        extra = _extra_calendars()
    except Exception:
        extra = []
    for svc, cal_id, lbl in extra:
        try:
            for ev in svc.events().list(calendarId=cal_id, **kwargs).execute().get("items", []):
                ev["_account"] = lbl
                items.append(ev)
        except Exception:
            continue
    if extra:
        items.sort(key=lambda e: e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", ""))
    return items


def _fmt(ev: dict) -> str:
    start = ev.get("start", {})
    when = start.get("dateTime") or start.get("date", "")
    if "T" in when:
        dt = datetime.fromisoformat(when).astimezone(TZ)
        when = dt.strftime("%a %d/%m %H:%M")
    color = COLOR_NAMES.get(ev.get("colorId", ""), "")
    loc = f" @ {ev['location']}" if ev.get("location") else ""
    acct = f" ({ev['_account']})" if ev.get("_account") else ""
    return f"{when} — {ev.get('summary', '(ללא כותרת)')}{loc} {color}{acct}".strip()


def get_calendar_events(days_ahead: int = 1, days_back: int = 0) -> str:
    """מחזיר את האירועים ביומן של יוסי. days_ahead = כמה ימים קדימה (1 = היום בלבד, 2 = היום ומחר). days_back = כמה ימים אחורה להציג גם."""
    now = datetime.now(TZ)
    t_min = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0)
    t_max = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0)
    items = _list_all(timeMin=t_min.isoformat(), timeMax=t_max.isoformat(),
                      singleEvents=True, orderBy="startTime", maxResults=50)
    if not items:
        return "אין אירועים בטווח הזה."
    return "\n".join(_fmt(e) for e in items)


def get_events_for_date(date_iso: str) -> str:
    """מחזיר את כל האירועים ביומן של יוסי בתאריך מסוים. date_iso בפורמט YYYY-MM-DD. זה הכלי הנכון לשאלות כמו 'מה יש לי מחר' או 'מה יש ביום חמישי'."""
    day = datetime.fromisoformat(date_iso).replace(tzinfo=TZ, hour=0, minute=0, second=0)
    items = _list_all(timeMin=day.isoformat(), timeMax=(day + timedelta(days=1)).isoformat(),
                      singleEvents=True, orderBy="startTime", maxResults=50)
    return "\n".join(_fmt(e) for e in items) if items else f"אין אירועים ב-{day.strftime('%d/%m')}."


def search_calendar_events(query: str, days_ahead: int = 30) -> str:
    """מחפש אירועים ביומן לפי מילה (למשל 'אופניים', 'זום', שם של אדם) בטווח של days_ahead ימים קדימה."""
    now = datetime.now(TZ)
    items = _list_all(q=query, timeMin=now.isoformat(), timeMax=(now + timedelta(days=days_ahead)).isoformat(),
                      singleEvents=True, orderBy="startTime", maxResults=30)
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
    category: אחד מ-'meeting' (פגישה/זום, אדום), 'bike' (שיעור אופניים, ירוק), 'expense' (הוצאה, כתום), 'done' (משימה שבוצעה, תכלת), 'mentors' (מפגש תוכנית המנטורים / פיברו, צהוב).
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
    """מוחק אירוע ביומן. title_query = מילה מהכותרת, date_iso = התאריך YYYY-MM-DD. מוחק רק אם נמצא אירוע אחד בדיוק.
    חובה לקבל אישור מפורש מיוסי לפני המחיקה."""
    import shula_agent
    if not shula_agent.user_approved():
        return ("עוד לא נמחק. קודם כתבי ליוסי איזה אירוע בדיוק (שם, תאריך ושעה) "
                "ובקשי שיענה 'כן, מחקי'. רק אחרי התשובה שלו אפשר למחוק.")
    day = datetime.fromisoformat(date_iso).replace(tzinfo=TZ)
    res = _svc().events().list(
        calendarId=CALENDAR_ID, q=title_query, timeMin=day.isoformat(),
        timeMax=(day + timedelta(days=1)).isoformat(), singleEvents=True,
    ).execute()
    items = res.get("items", [])
    if len(items) != 1:
        return f"נמצאו {len(items)} אירועים — צריך להיות בדיוק אחד. " + "\n".join(_fmt(e) for e in items)
    _svc().events().delete(calendarId=CALENDAR_ID, eventId=items[0]["id"]).execute()
    shula_agent.consume_approval()
    return f"נמחק: {_fmt(items[0])}"


DONE_WORDS = ("בוצע", "בוצעה", "סיימתי", "עשיתי", "גמרתי", "done", "✅")
_CLOSED_MARKS = ("✅", "בוצע", "❌", "בוטל")


def mark_event_done(title_query: str, result: str = "", days_back: int = 14) -> str:
    """מסמנת משימה/שיחה/פגישה ביומן כ'בוצע' (כשיוסי כותב 'בוצע <שם המשימה>').
    title_query = מילה או שתיים מהכותרת. result = תוצאה קצרה אם יוסי אמר (למשל 'נקבע ביקור 25.1').
    מחפשת אירועים פתוחים מ-days_back ימים אחורה ועד סוף היום. אם יש כמה התאמות — מסמנת את האחרונה שזמנה עבר,
    ואם אין כזו — מחזירה רשימה כדי לשאול את יוסי איזו."""
    import shula_agent
    msg = (getattr(shula_agent._turn, "message", "") or "").lower()
    if not any(w in msg for w in DONE_WORDS):
        return "לא סומן. מסמנים 'בוצע' רק כשיוסי עצמו כותב 'בוצע' בהודעה שלו."
    now = datetime.now(TZ)
    t_min = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0)
    t_max = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
    items = _svc().events().list(calendarId=CALENDAR_ID, q=title_query, timeMin=t_min.isoformat(),
                                 timeMax=t_max.isoformat(), singleEvents=True, orderBy="startTime",
                                 maxResults=30).execute().get("items", [])
    open_items = [e for e in items if not any(m in e.get("summary", "") for m in _CLOSED_MARKS)]
    if not open_items:
        return f"לא מצאתי משימה פתוחה עם '{title_query}' ב-{days_back} הימים האחרונים."

    def _start(e):
        s = e.get("start", {})
        v = s.get("dateTime") or (s.get("date", "") + "T00:00:00+02:00")
        return datetime.fromisoformat(v)

    past = [e for e in open_items if _start(e) <= now]
    if past:
        ev = past[-1]
    elif len(open_items) == 1:
        ev = open_items[0]
    else:
        return "יש כמה משימות מתאימות — שאלי את יוסי איזו:\n" + "\n".join(_fmt(e) for e in open_items)
    title = "✅ בוצע: " + ev.get("summary", "")
    if result:
        title += f" ({result})"
    _svc().events().patch(calendarId=CALENDAR_ID, eventId=ev["id"], sendUpdates="none",
                          body={"summary": title, "colorId": COLOR_IDS["done"]}).execute()
    left = len(open_items) - 1
    more = f" עוד {left} פתוחות עם אותה מילה." if left else ""
    return f"סומן: {title} ({_fmt(ev).split(' — ')[0]}).{more}"


RATINGS = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


def log_meal(description: str, calories_estimate: int, rating: str = "yellow",
             price_ils: float = 0, place: str = "", when_iso: str = "",
             protein_g: int = 0, carbs_g: int = 0, fat_g: int = 0) -> str:
    """רושמת ארוחה ביומן (מתמונה של אוכל, קבלה של וולט או 'אכלתי ...').
    description = מה נאכל (קצר). calories_estimate = הערכת קלוריות שלך (מספר שלם, הערכה בלבד).
    rating = 'green' (טוב ליעד), 'yellow' (בסדר), 'red' (כבד/לא מתאים ליעד ~1,800 קק״ל ביום).
    price_ils = מחיר בשקלים אם יש קבלה (וולט וכו') — אז נרשמת גם הוצאה בכתום. place = מסעדה/מקום.
    when_iso = YYYY-MM-DDTHH:MM, ריק = עכשיו (מעוגל לרבע שעה).
    protein_g / carbs_g / fat_g = הערכת חלבון, פחמימות ושומן בגרמים (אם אפשר להעריך) — מוצגים בלוח התזונה במטה."""
    if when_iso:
        start = datetime.fromisoformat(when_iso).replace(tzinfo=TZ)
    else:
        n = datetime.now(TZ)
        start = n.replace(minute=n.minute - n.minute % 15, second=0, microsecond=0)
    mark = RATINGS.get(rating, "🟡")
    where = f", {place}" if place else ""
    meal_title = f"🍽️ ארוחה: {description}{where} – ~{int(calories_estimate)} קק״ל {mark}"
    if protein_g or carbs_g or fat_g:
        meal_title += f" · ח׳ {int(protein_g)} פ׳ {int(carbs_g)} ש׳ {int(fat_g)}"
    note = "הערכת קלוריות בלבד (לא מדידה). יעד זמני: ~1,800 קק״ל ביום."
    out = [create_calendar_event(meal_title, start.strftime("%Y-%m-%dT%H:%M"), 15, "personal_meal", notes=note)]
    if price_ils:
        exp_title = f"💸 הוצאה {price_ils:g}₪ – {description}{where}"
        out.append(create_calendar_event(exp_title, start.strftime("%Y-%m-%dT%H:%M"), 15, "expense",
                                         notes=f"ארוחה. {meal_title}"))
    return "\n".join(out)


CALENDAR_TOOLS = [get_events_for_date, get_calendar_events, search_calendar_events, create_calendar_event,
                  delete_calendar_event, mark_event_done, log_meal]
