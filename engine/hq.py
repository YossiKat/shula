"""המטה של שולה — אפליקציית ווב (גרסה 1).

יוסי (16.11.2026): "את כל המטה של שולה תהפכי למערכת וובית מלאה שאני אשלוט ויעבוד דרך כתובת וובית" —
בעיצוב הכי מודרני (המראה מ-Canva שיוסי אהב: לבן-אפור רגוע, כרטיסים רכים, כחול-אפור אחד), ובשיטת סטיב ג'ובס:
כמה שפחות על המסך, כמה שיותר מידע.

כתובת: {PUBLIC_URL}/hq. כניסה בלי סיסמה: יוסי כותב לשולה בוואטסאפ "כניסה למטה" ומקבל קישור אישי לרבע שעה;
הקישור שם עוגייה חתומה בדפדפן ל-30 יום. בלי עוגייה — אין שום מידע.

מה יש בגרסה 1:
- היום שלי: כל מה שביומן היום ומחר, עם כפתור ✓ בוצע למשימות.
- 4 מספרים: משימות פתוחות היום, באיחור, בוצעו השבוע, הוצאות היום.
- הכסף של החודש: הוצאות והכנסות מהיומן.
- הוספה מהירה: הוצאה או משימה — נכנסות ליומן "יוסי קט" בצבעים של יוסי.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import hq_auth
import tools_calendar

router = APIRouter()
COOKIE = "hq_session"
LINK_TTL = 15 * 60
SESSION_TTL = 30 * 24 * 3600
OPEN_SKIP = ("✅", "בוצע", "❌", "בוטל", "לא התקיים")
MONEY = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*₪")


def _secret() -> bytes:
    raw = os.environ.get("HQ_SECRET") or (os.environ.get("ANTHROPIC_API_KEY", "") + os.environ.get("TWILIO_AUTH_TOKEN", ""))
    if not raw:
        raise RuntimeError("no secret for the HQ web app")
    return hashlib.sha256(("hq-v1:" + raw).encode()).digest()


def make_token(kind: str, ttl: int) -> str:
    body = base64.urlsafe_b64encode(json.dumps({"k": kind, "e": int(time.time()) + ttl}).encode()).decode().rstrip("=")
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()[:40]
    return f"{body}.{sig}"


def check_token(token: str, kind: str) -> bool:
    try:
        body, sig = (token or "").split(".", 1)
        good = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()[:40]
        if not hmac.compare_digest(sig, good):
            return False
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        return data.get("k") == kind and data.get("e", 0) > time.time()
    except Exception:
        return False


def hq_login_link() -> str:
    """קישור כניסה אישי למטה של שולה באתר (אפליקציית הווב של יוסי). תקף לרבע שעה, ואחרי הכניסה הדפדפן זוכר 30 יום.
    השתמשי כשיוסי כותב 'כניסה למטה', 'תשלחי לי קישור למטה', 'איך נכנסים לדשבורד'. שלחי לו את הקישור כמו שהוא."""
    base = os.environ.get("PUBLIC_URL", "https://shula-x5mr.onrender.com")
    return f"🏛️ הקישור שלך למטה (תקף לרבע שעה):\n{base}/hq/login?t={make_token('link', LINK_TTL)}"


HQ_TOOLS = [hq_login_link]


# מצב בדיקה: יוסי ביקש (16.11) לפתוח את המטה בלי הגנה לשעתיים כדי לבדוק הכול, ורק אחר כך להפעיל הגנות.
# אחרי השעה הזאת ההגנה חוזרת לבד. הגדרת Face ID / קוד גיבוי אפשרית רק עם כניסה אמיתית.
OPEN_UNTIL = 1794857400  # 16.11.2026 21:30 שעון ישראל


def _test_open() -> bool:
    return time.time() < OPEN_UNTIL


def _really_authed(request: Request) -> bool:
    return check_token(request.cookies.get(COOKIE, ""), "session")


def _authed(request: Request) -> bool:
    return _really_authed(request) or _test_open()


# ---------- נתונים ----------

def _events(start: datetime, end: datetime) -> list:
    svc, out, token = tools_calendar._svc(), [], None
    while True:
        res = svc.events().list(calendarId=tools_calendar.CALENDAR_ID, timeMin=start.isoformat(), timeMax=end.isoformat(),
                                singleEvents=True, orderBy="startTime", maxResults=250, pageToken=token).execute()
        out += res.get("items", [])
        token = res.get("nextPageToken")
        if not token or len(out) > 2000:
            return out


def _start(e: dict):
    s = e.get("start") or {}
    if s.get("dateTime"):
        return datetime.fromisoformat(s["dateTime"]).astimezone(tools_calendar.TZ), False
    return datetime.fromisoformat(s.get("date", "1970-01-01")).replace(tzinfo=tools_calendar.TZ), True


def _is_open_task(e: dict) -> bool:
    title = e.get("summary") or ""
    return e.get("colorId") == "11" and not any(w in title for w in OPEN_SKIP)


def _amount(title: str) -> float:
    m = MONEY.search(title or "")
    return float(m.group(1).replace(",", "")) if m else 0.0


def _is_expense(e: dict) -> bool:
    """הוצאה אמיתית: כתום (6) וכתוב בה 'הוצאה' או 💸. 'לשלם…' או 'לחייב…' הן משימות, לא הוצאה."""
    t = e.get("summary") or ""
    return e.get("colorId") == "6" and ("הוצאה" in t or "💸" in t)


def _is_income(e: dict) -> bool:
    return "הכנסה" in (e.get("summary") or "")


def _visible(e: dict) -> bool:
    import tools_sync
    return e.get("status") != "cancelled" and not tools_sync.is_monday_mirror(e)


def _item(e: dict) -> dict:
    when, all_day = _start(e)
    title = e.get("summary") or "(בלי כותרת)"
    kind = {"6": "expense", "7": "done", "10": "bike", "11": "task", "5": "trip", "2": "monday", "9": "gym"}.get(e.get("colorId") or "", "event")
    if kind == "task" and not _is_open_task(e):
        kind = "done"
    return {"id": e["id"], "title": title, "time": "" if all_day else when.strftime("%H:%M"),
            "day": when.date().isoformat(), "kind": kind, "where": e.get("location") or "",
            "can_done": _is_open_task(e), "dept": dept_of(title)}


DEPTS = [  # (מפתח, שם, אימוג'י, מילים בכותרת)
    ("cfo", "יונתן", "💰", ("💰", "יונתן", "רייצ׳ל", "מוני", "הכנסה", "קבלה", "תשלום", "חשבונית")),
    ("finance", "רות", "📊", ("📊", "רות", "חסיה", "ביטוח", "תקציב")),
    ("home", "ננסי", "🏠", ("🏠", "ננסי", "בתיה", "💸")),
    ("cmo", "ג׳סיקה", "📣", ("📣", "ג׳סיקה", "שירי", "פוסט", "שיווק", "aCare", "AlphaCare")),
    ("cto", "אמילי", "🧠", ("🧠", "אמילי", "רעיה", "שולה", "אפליקצי")),
    ("admin", "סוזן", "🗂️", ("🗂️", "סוזן", "סדרית")),
    ("personal", "ג׳ניפר", "❤️", ("❤️", "ג׳ניפר", "לבנה", "חדר כושר", "אימון")),
    ("legal", "אוליביה", "⚖️", ("⚖️", "אוליביה", "חוזה", "הסכם", "עו\"ד", "עורך דין", "רגולציה", "משפטי")),
]


def dept_of(title: str) -> str:
    for key, _, _, words in DEPTS:
        if any(w in (title or "") for w in words):
            return key
    return "admin"


# ---------- לימוד המחלקות ----------
# הגיליון "המטה של שולה – לימוד המחלקות" בדרייב של יוסי. הסריקה השבועית של יום ראשון מעדכנת אותו.
LEARN_FILE_ID = os.environ.get("HQ_LEARN_FILE_ID", "1pGwYLCnOTEiRgD327VEdu1HgCkG8MUTR27rPwvj9POQ")
_LEARN: dict = {"t": 0.0, "data": {}}


def learning() -> dict:
    """{dept: {topic, from, link, month, progress, lessons[], apply, status, check, why, updated, changes[]}}. 10 דקות בזיכרון."""
    if time.time() - _LEARN["t"] < 600:
        return _LEARN["data"]
    out: dict = {}
    try:
        import csv
        import io
        import google_auth
        drive = google_auth.service("drive", "v3", google_auth.MAIN)
        raw = drive.files().export(fileId=LEARN_FILE_ID, mimeType="text/csv").execute()
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        for r in csv.DictReader(io.StringIO(text)):
            dept, kind = (r.get("dept") or "").strip(), (r.get("kind") or "").strip()
            if not dept:
                continue
            d = out.setdefault(dept, {"changes": [], "learned": []})
            if kind == "learn":
                d.update({"topic": r.get("topic", ""), "from": r.get("from", ""), "link": r.get("link", ""),
                          "month": r.get("month", ""), "progress": r.get("progress", ""),
                          "lessons": [x.strip() for x in (r.get("lessons") or "").split("|") if x.strip()],
                          "apply": r.get("apply", ""), "status": r.get("applyStatus", ""),
                          "check": r.get("applyCheck", ""), "why": r.get("why", ""), "updated": r.get("updated", "")})
            elif kind == "change":
                d["changes"].append({"name": r.get("topic", ""), "what": r.get("apply", "")})
            elif kind == "learned":
                d["learned"].append({"topic": r.get("topic", ""), "month": r.get("month", "")})
        _LEARN["data"], _LEARN["t"] = out, time.time()
    except Exception:
        import logging
        logging.getLogger("shula.hq").exception("learning sheet read failed")
        _LEARN["t"] = time.time() - 480  # ננסה שוב בעוד 2 דקות
    return _LEARN["data"]


# ---------- המוח השני ----------
# כל ערב מגיעה במייל "ביקורת המוח השני – DD.MM.YYYY" (ציון למטה, מה טוב, מה תקוע, הצעד הבא). כאן מציגים את האחרונה.
_BRAIN: dict = {"t": 0.0, "data": {}}


def second_brain() -> dict:
    if time.time() - _BRAIN["t"] < 900:
        return _BRAIN["data"]
    out: dict = {}
    try:
        import tools_gmail
        g = tools_gmail._gmail()
        res = g.users().messages().list(userId="me", q='subject:"ביקורת המוח השני" newer_than:21d', maxResults=1).execute()
        msgs = res.get("messages") or []
        if msgs:
            m = g.users().messages().get(userId="me", id=msgs[0]["id"], format="full").execute()
            body = tools_gmail._body_text(m.get("payload", {}))
            score = re.search(r"ציון[^\n:]*:\s*(\d+)\s*/\s*10", body)
            lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
            out = {"subject": tools_gmail._header(m, "Subject"), "score": int(score.group(1)) if score else None,
                   "lines": [_clip(ln, 300) for ln in lines[:60]],
                   "link": f"https://mail.google.com/mail/u/0/#all/{msgs[0]['id']}"}
        _BRAIN["data"], _BRAIN["t"] = out, time.time()
    except Exception:
        import logging
        logging.getLogger("shula.hq").exception("second brain read failed")
        _BRAIN["t"] = time.time() - 780
    return _BRAIN["data"]


# ---------- כסף לפי חודש ----------
HE_MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]


def money_month(ym: str = "", now: datetime | None = None) -> dict:
    """הוצאות והכנסות של חודש שלם (1 בחודש עד סוף החודש), עם פירוט. ym = 'YYYY-MM' (ברירת מחדל: החודש הזה)."""
    now = now or datetime.now(tools_calendar.TZ)
    try:
        y, m = (int(x) for x in ym.split("-"))
        start = now.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)
    except Exception:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (start + timedelta(days=32)).replace(day=1)
    spent = income = 0.0
    items, planned = [], []
    for e in _events(start, end):
        if not _visible(e):
            continue
        title = e.get("summary") or ""
        when, _ = _start(e)
        if not (start <= when < end):
            continue
        amt = _amount(title)
        if not amt:
            continue
        kind = "out" if _is_expense(e) else "in" if _is_income(e) else ""
        if not kind:
            continue
        if when > now:  # עוד לא קרה — מוצג בנפרד ולא נספר
            planned.append({"day": when.date().isoformat(), "title": _clip(title, 90), "amount": amt, "kind": kind})
            continue
        if kind == "out":
            spent += amt
        else:
            income += amt
        items.append({"day": when.date().isoformat(), "title": _clip(title, 90), "amount": amt, "kind": kind})
    items.sort(key=lambda i: i["day"], reverse=True)
    prev = (start - timedelta(days=1)).replace(day=1)
    return {"ym": start.strftime("%Y-%m"), "label": f"{HE_MONTHS[start.month - 1]} {start.year}",
            "prev": prev.strftime("%Y-%m"), "next": end.strftime("%Y-%m"), "is_current": start.month == now.month and start.year == now.year,
            "spent": round(spent), "income": round(income), "balance": round(income - spent),
            "n_out": sum(1 for i in items if i["kind"] == "out"), "n_in": sum(1 for i in items if i["kind"] == "in"),
            "items": items[:300], "planned": sorted(planned, key=lambda i: i["day"])[:50]}


_SNAP: dict = {"t": 0.0, "data": None}
SNAP_TTL = 30


def cached_snapshot() -> dict:
    """אותה תמונת מצב למשך 30 שניות — שפתיחות ורענונים צמודים לא יחכו כל פעם ליומן. כל פעולה מנקה."""
    if _SNAP["data"] is None or time.time() - _SNAP["t"] > SNAP_TTL:
        _SNAP["data"], _SNAP["t"] = snapshot(), time.time()
    return _SNAP["data"]


def clear_snapshot() -> None:
    _SNAP["data"] = None


def snapshot(now: datetime | None = None) -> dict:
    now = now or datetime.now(tools_calendar.TZ)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = today.replace(day=1)
    since = min(month, today - timedelta(days=14))
    evs = [e for e in _events(since, today + timedelta(days=8)) if _visible(e)]
    day_items, tomorrow, late, week, done_week = [], [], [], [], []
    done7 = spent_today = spent_month = income_month = 0
    for e in evs:
        when, _ = _start(e)
        title = e.get("summary") or ""
        if when >= month and when < today + timedelta(days=1):
            if _is_expense(e) and when <= now:
                spent_month += _amount(title)
            if _is_income(e) and when <= now:
                income_month += _amount(title)
        if today <= when < today + timedelta(days=1):
            day_items.append(_item(e))
            if _is_expense(e) and when <= now:
                spent_today += _amount(title)
        elif today + timedelta(days=1) <= when < today + timedelta(days=8):
            week.append(_item(e))
            if when < today + timedelta(days=2):
                tomorrow.append(_item(e))
        elif when < today and _is_open_task(e) and when >= today - timedelta(days=14):
            late.append(_item(e))
        if e.get("colorId") == "7" and today - timedelta(days=6) <= when < today + timedelta(days=1):
            done7 += 1
            done_week.append(_item(e))
    open_today = sum(1 for i in day_items if i["can_done"])
    stats = {k: {"key": k, "name": n, "emoji": em, "open": 0, "late": 0, "done": 0} for k, n, em, _ in DEPTS}
    for i in day_items:
        d = stats[dept_of(i["title"])]
        if i["can_done"]:
            d["open"] += 1
        elif i["kind"] == "done":
            d["done"] += 1
    for i in late:
        stats[dept_of(i["title"])]["late"] += 1
    nxt = next((i for i in day_items if i["time"] and i["time"] >= now.strftime("%H:%M")), None)
    alerts = ([{"level": "next", "text": f"הבא: {nxt['time']} {nxt['title']}"}] if nxt else []) + \
             [{"level": "late", "text": f"באיחור מ-{i['day'][8:]}.{i['day'][5:7]}: {i['title']}"} for i in late[-4:][::-1]]
    return {"depts": list(stats.values()), "alerts": alerts,"now": now.strftime("%H:%M"), "date": today.date().isoformat(),
            "tiles": {"open": open_today, "late": len(late), "done7": done7, "spent": round(spent_today)},
            "money": {"spent": round(spent_month), "income": round(income_month), "month": month.strftime("%m.%Y")},
            "learning": learning(),
            "brain": second_brain(),
            "today": day_items, "tomorrow": tomorrow, "late": late[-20:], "week": week[:120], "done_week": done_week[-80:]}


def mark_done(event_id: str) -> dict:
    svc = tools_calendar._svc()
    e = svc.events().get(calendarId=tools_calendar.CALENDAR_ID, eventId=event_id).execute()
    if not _is_open_task(e):
        return {"ok": False, "msg": "זו לא משימה פתוחה"}
    title = "✅ בוצע: " + (e.get("summary") or "")
    svc.events().patch(calendarId=tools_calendar.CALENDAR_ID, eventId=event_id, sendUpdates="none",
                       body={"summary": title, "colorId": "7"}).execute()
    return {"ok": True, "title": title}


def book_room(topic: str, day: str, at: str, depts: list, minutes: int = 60) -> dict:
    """הזמנת חדר הישיבות: ישיבת צוות שבועית או עבודה משותפת של כמה מחלקות — אירוע אחד ביומן."""
    names = [n for k, n, _, _ in DEPTS if k in (depts or [])]
    if not _clip(topic):
        return {"ok": False, "msg": "חסר נושא לישיבה"}
    try:
        start = datetime.strptime(f"{day} {at or '10:00'}", "%Y-%m-%d %H:%M").replace(tzinfo=tools_calendar.TZ)
    except ValueError:
        return {"ok": False, "msg": "תאריך או שעה לא תקינים"}
    minutes = max(15, min(int(minutes or 60), 240))
    title = f"🏛️ חדר ישיבות – {_clip(topic, 80)}" + (f" ({', '.join(names)})" if names else "")
    tools_calendar._svc().events().insert(calendarId=tools_calendar.CALENDAR_ID, body={
        "summary": title, "colorId": "11",
        "description": "חדר הישיבות של המטה.\nמשתתפות: " + (", ".join(names) or "כל המחלקות") + "\nנקבע מהמטה באתר",
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
        "end": {"dateTime": (start + timedelta(minutes=minutes)).isoformat(), "timeZone": "Asia/Jerusalem"},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]}}).execute()
    return {"ok": True, "title": title}


def _clip(text: str, n: int = 120) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())[:n]


def add_expense(amount: float, what: str, how: str = "") -> dict:
    if not (0 < amount < 1_000_000) or not _clip(what):
        return {"ok": False, "msg": "חסר סכום או על מה"}
    now = datetime.now(tools_calendar.TZ)
    start = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    amt = f"{amount:,.0f}" if amount == int(amount) else f"{amount:,.2f}"
    title = f"💸 הוצאה {amt}₪ – {_clip(what)}" + (f" ({_clip(how, 30)})" if _clip(how) else "")
    tools_calendar._svc().events().insert(calendarId=tools_calendar.CALENDAR_ID, body={
        "summary": title, "colorId": "6", "description": f"סכום: {amt} ₪\nמה: {_clip(what)}\nאמצעי תשלום: {_clip(how, 30) or 'לא צוין'}\nנרשם מהמטה באתר",
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
        "end": {"dateTime": (start + timedelta(minutes=15)).isoformat(), "timeZone": "Asia/Jerusalem"},
        "reminders": {"useDefault": False, "overrides": []}}).execute()
    return {"ok": True, "title": title}


def add_task(title: str, day: str, at: str) -> dict:
    if not _clip(title):
        return {"ok": False, "msg": "חסר שם למשימה"}
    try:
        start = datetime.strptime(f"{day} {at or '10:00'}", "%Y-%m-%d %H:%M").replace(tzinfo=tools_calendar.TZ)
    except ValueError:
        return {"ok": False, "msg": "תאריך או שעה לא תקינים"}
    tools_calendar._svc().events().insert(calendarId=tools_calendar.CALENDAR_ID, body={
        "summary": _clip(title), "colorId": "11", "description": "נוסף מהמטה באתר",
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
        "end": {"dateTime": (start + timedelta(minutes=15)).isoformat(), "timeZone": "Asia/Jerusalem"},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]}}).execute()
    return {"ok": True, "title": _clip(title)}


# ---------- נתיבים ----------

@router.get("/hq/login")
def login(t: str = ""):
    if not check_token(t, "link"):
        return HTMLResponse(_page(LOGIN_BODY.replace("{msg}", "הקישור פג או לא תקין. כתוב לשולה שוב: <b>כניסה למטה</b>")), status_code=401)
    resp = RedirectResponse("/hq", status_code=303)
    resp.set_cookie(COOKIE, make_token("session", SESSION_TTL), max_age=SESSION_TTL, httponly=True, secure=True, samesite="lax")
    return resp


@router.get("/hq")
def home(request: Request):
    if not _authed(request):
        return HTMLResponse(_page(LOGIN_BODY.replace("{msg}", "פעם ראשונה, או שאין Face ID? כתוב לשולה בוואטסאפ: <b>כניסה למטה</b>")))
    body = APP_BODY.replace("/*AVATARS*/[]", json.dumps(avatars()))
    if _test_open() and not _really_authed(request):
        body = ('<div class="card testbar">🧪 מצב בדיקה: המטה פתוח בלי הגנה עד 21:30. אחר כך ההגנה חוזרת לבד.</div>'
                + body)
    return HTMLResponse(_page(body), headers={"Cache-Control": "no-store"})


@router.get("/hq/api/today")
def api_today(request: Request):
    if not _authed(request):
        return JSONResponse({"ok": False}, status_code=401)
    return JSONResponse(cached_snapshot(), headers={"Cache-Control": "no-store"})


IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hq_img")


def avatars() -> list:
    """אילו תמונות פורטרט קיימות (shula + מפתחות המחלקות)."""
    try:
        return sorted(f[:-4] for f in os.listdir(IMG_DIR) if f.endswith(".jpg"))
    except OSError:
        return []


@router.get("/hq/img/{name}.jpg")
def hq_img(name: str):
    from fastapi.responses import FileResponse, Response
    if name not in avatars():
        return Response(status_code=404)
    return FileResponse(os.path.join(IMG_DIR, name + ".jpg"), media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=86400"})


@router.get("/hq/api/money")
def api_money(request: Request, m: str = ""):
    if not _authed(request):
        return JSONResponse({"ok": False}, status_code=401)
    return JSONResponse(money_month(m), headers={"Cache-Control": "no-store"})


@router.post("/hq/api/{action}")
async def api_action(action: str, request: Request):
    if not _authed(request):
        return JSONResponse({"ok": False}, status_code=401)
    if request.headers.get("x-hq") != "1":  # הגנה מטפסים זרים
        return JSONResponse({"ok": False}, status_code=403)
    data = await request.json()
    clear_snapshot()
    if action == "done":
        return JSONResponse(mark_done(str(data.get("id", ""))))
    if action == "expense":
        try:
            amount = float(str(data.get("amount", "0")).replace(",", ""))
        except ValueError:
            amount = 0
        return JSONResponse(add_expense(amount, str(data.get("what", "")), str(data.get("how", ""))))
    if action == "room":
        depts = data.get("depts") if isinstance(data.get("depts"), list) else []
        return JSONResponse(book_room(str(data.get("topic", "")), str(data.get("day", "")), str(data.get("at", "")),
                                      [str(d) for d in depts][:7], data.get("minutes") or 60))
    if action == "task":
        return JSONResponse(add_task(str(data.get("title", "")), str(data.get("day", "")), str(data.get("at", ""))))
    return JSONResponse({"ok": False}, status_code=404)


def _session_response(payload: dict) -> JSONResponse:
    resp = JSONResponse(payload)
    resp.set_cookie(COOKIE, make_token("session", SESSION_TTL), max_age=SESSION_TTL, httponly=True, secure=True, samesite="lax")
    return resp


@router.post("/hq/auth/{action}")
async def auth_action(action: str, request: Request):
    """כניסה בלי שולה: Face ID (passkey) או קוד גיבוי. ההגדרות עצמן רק מתוך המטה (אחרי כניסה)."""
    if request.headers.get("x-hq") != "1":
        return JSONResponse({"ok": False}, status_code=403)
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    # פתוח לכולם — רק כדי להיכנס
    if action == "login-options":
        return JSONResponse(hq_auth.login_options())
    if action == "login":
        if hq_auth.login_verify(str(data.get("cid", "")), data.get("credential") or {}):
            return _session_response({"ok": True})
        return JSONResponse({"ok": False, "msg": "הזיהוי לא הצליח. נסה שוב."}, status_code=401)
    if action == "code":
        res = hq_auth.check_backup_code(str(data.get("code", "")))
        if res == "ok":
            return _session_response({"ok": True})
        msg = {"locked": "יותר מדי ניסיונות. נסה שוב בעוד רבע שעה.", "none": "עוד לא נוצר קוד גיבוי."}.get(res, "הקוד לא נכון.")
        return JSONResponse({"ok": False, "msg": msg}, status_code=401)
    # מכאן — רק מי שבאמת נכנס (לא במצב בדיקה פתוח)
    if not _really_authed(request):
        return JSONResponse({"ok": False}, status_code=401)
    if action == "status":
        return JSONResponse(hq_auth.status())
    if action == "register-options":
        return JSONResponse(hq_auth.register_options())
    if action == "register":
        return JSONResponse(hq_auth.register_verify(str(data.get("cid", "")), data.get("credential") or {}, str(data.get("name", ""))))
    if action == "backup":
        return JSONResponse(hq_auth.new_backup_code())
    if action == "remove-passkeys":
        return JSONResponse(hq_auth.remove_passkeys())
    return JSONResponse({"ok": False}, status_code=404)


def _page(body: str) -> str:
    return HEAD + body + "</body></html>"


HEAD = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#101c27"><meta name="robots" content="noindex,nofollow">
<title>המטה של שולה</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700;800&display=swap">
<style>
/* חדר המבצעים — כהה ונעים: כחול-לילה רך, טורקיז, ענבר ואלמוג במקום ניאון */
:root{--bg:#101c27;--bg2:#13222f;--card:#172a38;--line:#23394b;--fg:#e4edf3;--mut:#8ea5b7;--acc:#5ec4b6;--amb:#f2b866;--hot:#ef8b7e;--sh:0 1px 0 rgba(255,255,255,.03) inset,0 12px 30px rgba(0,0,0,.28);color-scheme:dark}
*{box-sizing:border-box}[hidden]{display:none!important}
html,body{margin:0;min-height:100%;color:var(--fg);font-family:Heebo,system-ui,sans-serif;background:radial-gradient(1200px 600px at 70% -10%,#1b3446 0%,transparent 60%),var(--bg)}
body{padding:max(14px,env(safe-area-inset-top)) 16px 40px;background-image:linear-gradient(rgba(94,196,182,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(94,196,182,.035) 1px,transparent 1px);background-size:32px 32px}
.w{max-width:1180px;margin:0 auto;display:grid;gap:16px}
.card{background:linear-gradient(180deg,rgba(255,255,255,.02),transparent),var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:var(--sh);padding:18px}
.bar{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:12px 18px}
.bar .live{display:flex;align-items:center;gap:8px;color:var(--acc);font-weight:700;letter-spacing:.08em;font-size:13px}
.bar .live i{width:9px;height:9px;border-radius:50%;background:var(--acc);box-shadow:0 0 0 0 rgba(94,196,182,.6);animation:pulse 2s infinite}
.bar .t{font-variant-numeric:tabular-nums;color:var(--mut);font-size:14px}.bar h1{margin:0;font-size:20px;font-weight:500;flex:1}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(94,196,182,.55)}70%{box-shadow:0 0 0 10px rgba(94,196,182,0)}100%{box-shadow:0 0 0 0 rgba(94,196,182,0)}}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
@media (max-width:700px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
.tile{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 12px;position:relative;overflow:hidden}
.tile:before{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:var(--acc);opacity:.7}
.tile.hot:before{background:var(--hot)}.tile.amb:before{background:var(--amb)}
.tile span{display:block;font-size:12px;color:var(--mut);letter-spacing:.04em}
.tile b{display:block;font-size:38px;font-weight:300;font-variant-numeric:tabular-nums;line-height:1.15;color:var(--fg)}
.tile.hot b{color:var(--hot)}.tile.amb b{color:var(--amb)}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr) minmax(0,.95fr);gap:16px}
@media (max-width:1000px){.grid{grid-template-columns:1fr}}
h2{font-size:14px;margin:0 0 12px;font-weight:700;letter-spacing:.06em;color:var(--mut)}
.radar{position:relative;aspect-ratio:1;max-width:100%;margin:0 auto}
.radar svg{width:100%;height:100%;display:block}
.sweep{transform-origin:200px 200px;animation:spin 6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.sweep,.bar .live i,.blip{animation:none!important}}
.blip{animation:blip 2.4s ease-in-out infinite}@keyframes blip{50%{opacity:.45}}
.legend{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 12px;margin-top:10px;font-size:13px}
.legend div{display:flex;gap:6px;align-items:center;min-width:0}.legend i{width:8px;height:8px;border-radius:50%;flex:none}
.legend small{color:var(--mut);margin-inline-start:auto}
.line{list-style:none;margin:0;padding:0;display:grid;gap:7px}
.it{display:grid;grid-template-columns:48px 8px minmax(0,1fr) auto;gap:10px;align-items:center;padding:9px 11px;border-radius:12px;background:var(--bg2);border:1px solid transparent}
.it .t{font-variant-numeric:tabular-nums;font-weight:500;font-size:13px;color:var(--mut)}
.it .d{width:8px;height:8px;border-radius:50%;background:var(--acc)}
.it .n{min-width:0;overflow-wrap:anywhere;font-size:14px}
.it.expense .d{background:var(--amb)}.it.task .d{background:var(--hot)}.it.task{border-color:rgba(239,139,126,.18)}
.it.done .d{background:#4c6a80}.it.done .n{color:var(--mut)}.it.trip .d{background:#d7c06a}
.now{display:flex;align-items:center;gap:8px;color:var(--hot);font-size:11px;font-weight:700;letter-spacing:.06em}.now:after{content:"";flex:1;height:1px;background:var(--hot);box-shadow:0 0 8px var(--hot)}
button{font:inherit;border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer;background:transparent;color:var(--acc);font-weight:600;font-size:13px}
button:hover{border-color:var(--acc)}button.go{background:var(--acc);border-color:transparent;color:#0d1a22}button:disabled{opacity:.5}
.alerts{display:grid;gap:8px}
.al{padding:10px 12px;border-radius:12px;background:var(--bg2);border-inline-start:3px solid var(--hot);font-size:14px;overflow-wrap:anywhere}
.al.next{border-color:var(--acc)}.al.late{animation:soft 3s ease-in-out infinite}@keyframes soft{50%{background:#1c2a36}}
.empty{color:var(--mut);text-align:center;padding:12px;border:1px dashed var(--line);border-radius:12px;font-size:14px}
.money{display:grid;grid-template-columns:1fr 1fr;gap:10px}.money div{background:var(--bg2);border-radius:12px;padding:10px;text-align:center}
.money span{font-size:12px;color:var(--mut)}.money b{display:block;font-size:24px;font-weight:300;font-variant-numeric:tabular-nums}.money .in b{color:var(--acc)}.money .out b{color:var(--amb)}
form{display:grid;gap:8px}input{font:inherit;padding:9px 11px;border-radius:10px;border:1px solid var(--line);background:var(--bg2);color:var(--fg);width:100%;min-width:0}
.row{display:flex;gap:8px}.row>*{flex:1;min-width:0}
.tabs{display:flex;gap:8px}.tabs button[aria-selected=true]{background:var(--acc);color:#0d1a22;border-color:transparent}
details summary{cursor:pointer;font-weight:600;color:var(--mut);font-size:14px}
.msg{font-size:12px;color:var(--mut);min-height:1em;margin:6px 0 0}
.login{max-width:420px;margin:14vh auto;text-align:center;display:grid;gap:12px}.login .big{font-size:18px;padding:14px}.login .hint{font-size:13px}.login .alt summary{cursor:pointer;color:var(--mut)}.login .alt form{display:grid;gap:8px;margin-top:8px}.login .alt input{text-align:center;letter-spacing:.15em;font-size:20px}.codebox{font-size:26px;letter-spacing:.12em;text-align:center;padding:12px;border:1px dashed var(--acc);border-radius:12px;font-variant-numeric:tabular-nums;user-select:all}.upd{font-size:12px;color:var(--mut)}
.brain .bh{display:flex;align-items:center;gap:10px}.brain h2{flex:1;margin:0}.brain .score{font-size:26px;font-weight:300;color:var(--amb);font-variant-numeric:tabular-nums}
.bl{list-style:none;margin:0;padding:0;display:grid;gap:4px}.bl li{line-height:1.5}.brain .src{display:inline-block;margin-top:8px;font-size:13px;color:var(--acc)}
.avimg{width:100%;height:100%;object-fit:cover;border-radius:50%;display:block}.dhead .av{overflow:hidden;padding:0}
.me{display:inline-flex}.meimg{width:40px;height:40px;border-radius:50%;object-fit:cover;border:2px solid var(--acc)}.avsm{width:30px;height:30px;border-radius:50%;object-fit:cover;display:block}
.mhead{display:flex;align-items:center;gap:8px}.mhead h2{flex:1;text-align:center;margin:0 0 10px}.arr.sm{width:30px;height:30px;font-size:16px;padding:0}
.learn{list-style:none;margin:0;padding:0;display:grid;gap:8px}.learn li{display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 10px;align-items:start;padding:8px 10px;background:var(--bg2);border-radius:12px;cursor:pointer}
.learn .e{font-size:20px;grid-row:span 2}.learn .t{font-weight:500}.learn small{color:var(--mut);font-size:12px}
.lbox{display:grid;gap:10px}.lbox h3{margin:0;font-size:17px;font-weight:500}.lbox .src{font-size:13px;color:var(--mut)}.lbox .src a{color:var(--acc)}
.lbox ul{margin:0;padding-inline-start:18px;display:grid;gap:4px}.lbox .ap{background:var(--bg2);border-radius:12px;padding:10px}.pill{display:inline-block;font-size:12px;padding:2px 8px;border-radius:999px;border:1px solid var(--line);margin-inline-start:6px}
.pill.ok{color:var(--acc);border-color:var(--acc)}.pill.wait{color:var(--amb);border-color:var(--amb)}.testbar{max-width:1180px;margin:0 auto 16px;border-color:var(--amb);color:var(--amb);text-align:center;padding:10px}.login h1{font-weight:300;font-size:34px;margin:6px 0}.login p{color:var(--mut)}
.brand{color:var(--acc);font-weight:700;letter-spacing:.1em;font-size:12px;margin:0}
/* ===== מראה 2: אפל נקי (body.apple) — לבן, שקט, הרבה מקום, מעט על המסך ===== */
body.apple{--bg:#f5f6f8;--bg2:#f3f5f7;--card:#fff;--line:#e8ecf0;--fg:#1d2733;--mut:#7a8794;--acc:#6f8ba4;--amb:#c98a2e;--hot:#e26d5a;--sh:0 1px 2px rgba(20,30,45,.04),0 12px 32px rgba(20,30,45,.07);color-scheme:light;background:var(--bg);background-image:none}
body.apple .card,body.apple .tile{border:0;box-shadow:var(--sh);border-radius:24px;background:var(--card)}
body.apple .tile:before{display:none}
body.apple .bar{padding:28px 28px 22px;flex-direction:column;align-items:flex-start;gap:4px}
body.apple .bar h1{font-family:Georgia,'Frank Ruhl Libre',serif;font-weight:300;font-size:clamp(34px,6vw,52px);order:-1}
body.apple .bar .live{display:none}
body.apple .tiles{grid-template-columns:repeat(3,minmax(0,1fr))}body.apple .tile.amb{display:none}
body.apple .tile{text-align:center;padding:22px 12px}body.apple .tile span{font-size:14px;font-weight:600;color:var(--fg)}
body.apple .tile b{font-size:52px;font-weight:300;color:var(--acc)}body.apple .tile.hot b{color:var(--hot)}
body.apple .grid{grid-template-columns:minmax(0,1.6fr) minmax(0,1fr)}
@media (max-width:1000px){body.apple .grid{grid-template-columns:1fr}}
body.apple #c-radar{grid-column:1/-1;order:9}body.apple #c-radar .radar,body.apple #c-alerts{display:none}
body.apple .legend{grid-template-columns:repeat(7,minmax(0,1fr));gap:10px;margin:0}
@media (max-width:700px){body.apple .legend{grid-template-columns:repeat(4,minmax(0,1fr))}}
body.apple .legend div{flex-direction:column;gap:6px;text-align:center;font-size:13px;position:relative}
body.apple .legend .e{order:-1;display:grid;place-items:center;width:52px;height:52px;margin:0 auto;border-radius:50%;background:var(--bg2);font-size:24px}
body.apple .legend i{position:absolute;top:2px;inset-inline-end:calc(50% - 26px);width:12px;height:12px;border:2px solid #fff}
body.apple .legend small{margin:0}
body.apple .it{background:var(--bg2);border:0;border-radius:14px}body.apple .it.task{border:0}
body.apple button{border-color:var(--line);background:#eef2f6;color:var(--acc)}body.apple button.go{background:var(--acc);color:#fff}
body.apple input{background:var(--bg2)}body.apple .al.late{animation:none}
.look{font-size:12px;padding:5px 10px}
.nav{display:flex;align-items:center;gap:8px;min-width:0}.chips{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;flex:1;padding:2px}.chips::-webkit-scrollbar{display:none}
.chips button{flex:none;white-space:nowrap}.chips button[aria-current=page]{background:var(--acc);color:#0d1a22;border-color:transparent}
body.apple .chips button[aria-current=page]{color:#fff}
.arr{font-size:20px;line-height:1;padding:4px 12px}
.view{display:grid;gap:16px}.sub2{color:var(--mut);margin:-4px 0 12px;font-size:14px}
.grid2{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:16px}@media (max-width:900px){.grid2{grid-template-columns:1fr}}
.dhead{display:flex;align-items:center;gap:14px}.dhead .av{width:64px;height:64px;border-radius:50%;display:grid;place-items:center;font-size:32px;background:var(--bg2);border:1px solid var(--line)}
.dhead h2{margin:0;font-size:24px;color:var(--fg);letter-spacing:0}.dhead p{margin:2px 0 0;color:var(--mut)}
.stat3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:14px}.stat3 div{background:var(--bg2);border-radius:12px;padding:10px;text-align:center}
.stat3 b{display:block;font-size:28px;font-weight:300}.stat3 span{font-size:12px;color:var(--mut)}
.table{position:relative;max-width:640px;margin:0 auto;aspect-ratio:1.35}
.table svg{width:100%;height:100%;display:block}
.who{display:flex;flex-wrap:wrap;gap:6px}.who label{display:flex;align-items:center;gap:4px;font-size:13px;padding:4px 10px;border:1px solid var(--line);border-radius:999px;cursor:pointer}
.who input{width:auto}
</style></head><body>"""

LOGIN_BODY = r"""<div class="card login"><p class="brand">● המטה של שולה</p><h1>שלום, יוסי</h1>
<button type="button" class="go big" id="fid">🔐 כניסה עם Face ID</button>
<details class="alt"><summary>יש לי קוד גיבוי</summary><form id="codef"><input name="code" inputmode="numeric" autocomplete="one-time-code" placeholder="____-____-____" required><button class="go">כניסה</button></form></details>
<p class="msg" id="lmsg"></p><p class="hint">{msg}</p></div>
<script>
const b2a=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'==='.slice((s.length+3)%4)),c=>c.charCodeAt(0)).buffer;
const a2b=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const ap=(u,b)=>fetch(u,{method:'POST',credentials:'same-origin',headers:{'content-type':'application/json','x-hq':'1'},body:JSON.stringify(b||{})}).then(r=>r.json());
const say=t=>{document.getElementById('lmsg').textContent=t;};
document.getElementById('fid').onclick=async()=>{
 if(!window.PublicKeyCredential){say('הדפדפן הזה לא תומך ב-Face ID. אפשר להיכנס עם קוד גיבוי.');return;}
 try{const o=await ap('/hq/auth/login-options');if(!o.ok){say(o.msg);return;}
  const pk=o.options;pk.challenge=b2a(pk.challenge);(pk.allowCredentials||[]).forEach(c=>c.id=b2a(c.id));
  const c=await navigator.credentials.get({publicKey:pk});
  const cred={id:c.id,rawId:a2b(c.rawId),type:c.type,response:{clientDataJSON:a2b(c.response.clientDataJSON),authenticatorData:a2b(c.response.authenticatorData),signature:a2b(c.response.signature),userHandle:c.response.userHandle?a2b(c.response.userHandle):null}};
  const r=await ap('/hq/auth/login',{cid:o.cid,credential:cred});if(r.ok)location.replace('/hq');else say(r.msg||'לא הצליח');
 }catch(e){say('הזיהוי בוטל או לא הצליח. נסה שוב.');}};
document.getElementById('codef').onsubmit=async ev=>{ev.preventDefault();const r=await ap('/hq/auth/code',{code:ev.target.code.value});if(r.ok)location.replace('/hq');else say(r.msg||'לא הצליח');};
</script>"""

APP_BODY = r"""<div class="w">
<header class="card bar"><span class="live"><i></i>פעיל</span><span class="me" id="me"></span><h1 id="hi">המטה של שולה</h1><span class="t" id="clock"></span><span class="upd" id="upd"></span><button type="button" class="look" id="refresh" aria-label="רענון">🔄</button><button type="button" class="look" id="sec">🔐 כניסה</button><button type="button" class="look" id="look">🎨 מראה</button></header>
<section class="card" id="secp" hidden><h2>🔐 כניסה בלי שולה</h2><p class="sub2" id="sec-st">בודק…</p><div class="row"><button type="button" class="go" id="sec-add">להגדיר Face ID במכשיר הזה</button><button type="button" class="go" id="sec-code">ליצור קוד גיבוי</button></div><div class="codebox" id="sec-show" hidden></div><p class="msg" id="sec-msg"></p><button type="button" class="look" id="sec-rm" hidden>למחוק את כל ה-Face ID</button></section>
<nav class="nav" aria-label="ניווט"><button type="button" class="arr" id="prev" aria-label="הקודם">›</button><div class="chips" id="chips"></div><button type="button" class="arr" id="next" aria-label="הבא">‹</button></nav>
<div id="v-main" class="view">
<section class="card brain" id="brain" hidden><div class="bh"><h2>🧠 המוח השני – הביקורת האחרונה</h2><span class="score" id="b-score"></span></div><p class="sub2" id="b-sub"></p><ul class="bl" id="b-top"></ul>
<details><summary>כל הביקורת</summary><ul class="bl" id="b-all" style="margin-top:8px"></ul></details><a class="src" id="b-link" target="_blank" rel="noopener">לפתוח את המייל ↗</a></section>
<section class="tiles" aria-label="מספרים">
 <div class="tile"><span>משימות היום</span><b id="t-open">–</b></div>
 <div class="tile hot"><span>באיחור</span><b id="t-late">–</b></div>
 <div class="tile"><span>בוצעו השבוע</span><b id="t-done">–</b></div>
 <div class="tile amb"><span>הוצאות היום</span><b id="t-spent">–</b></div>
</section>
<div class="grid">
 <section class="card" id="c-radar"><h2>🛰️ המחלקות – עכשיו</h2><div class="radar" id="radar"></div><div class="legend" id="legend"></div></section>
 <section class="card"><h2>☀️ היום שלי</h2><ul class="line" id="today"></ul>
  <details style="margin-top:12px"><summary id="late-h">⏳ מחכה מימים קודמים</summary><ul class="line" id="late" style="margin-top:8px"></ul></details>
  <details style="margin-top:8px"><summary>🌙 מחר</summary><ul class="line" id="tomorrow" style="margin-top:8px"></ul></details>
 </section>
 <div style="display:grid;gap:16px;align-content:start">
  <section class="card" id="c-alerts"><h2>🚨 התראות</h2><div class="alerts" id="alerts"></div></section>
  <section class="card"><h2>➕ הוספה מהירה</h2>
   <div class="tabs" role="tablist"><button type="button" role="tab" aria-selected="true" data-f="exp">💸 הוצאה</button><button type="button" role="tab" aria-selected="false" data-f="task">📌 משימה</button></div>
   <form id="exp" style="margin-top:10px"><div class="row"><input name="amount" inputmode="decimal" placeholder="סכום ₪" required><input name="how" placeholder="איך שילמת"></div><input name="what" placeholder="על מה ואיפה" required><button class="go">לרשום ביומן</button></form>
   <form id="task" hidden style="margin-top:10px"><input name="title" placeholder="מה צריך לעשות" required><div class="row"><input name="day" type="date" required><input name="at" type="time" value="10:00"></div><button class="go">להוסיף ליומן</button></form>
   <p class="msg" id="msg"></p>
  </section>
  <section class="card"><div class="mhead"><button type="button" class="arr sm" id="m-prev" aria-label="חודש קודם">›</button><h2 id="m-label">💰 החודש</h2><button type="button" class="arr sm" id="m-next" aria-label="חודש הבא">‹</button></div>
   <div class="money"><div class="out"><span>הוצאות</span><b id="m-out">–</b></div><div class="in"><span>הכנסות</span><b id="m-in">–</b></div></div>
   <p class="sub2" id="m-bal" style="margin:10px 0 0;text-align:center"></p>
   <details style="margin-top:8px"><summary id="m-sum">פירוט החודש</summary><ul class="line" id="m-items" style="margin-top:8px"></ul></details></section>
  <section class="card"><h2>📚 מה המחלקות לומדות החודש</h2><ul class="learn" id="learn"></ul></section>
 </div>
</div>
</div>
<div id="v-dept" class="view" hidden></div>
<div id="v-room" class="view" hidden>
 <section class="card"><h2>🪑 חדר הישיבות</h2><p class="sub2">כל מחלקה מדווחת: מה פתוח, מה באיחור ומה נעשה השבוע.</p><div class="table" id="table"></div></section>
 <div class="grid2">
  <section class="card"><h2>📋 סדר יום – מה צריך החלטה</h2><ul class="line" id="agenda"></ul></section>
  <section class="card"><h2>📅 להזמין את החדר</h2>
   <form id="room"><input name="topic" placeholder="נושא – למשל: ישיבת צוות שבועית" required><div class="row"><input name="day" type="date" required><input name="at" type="time" value="10:00"><input name="minutes" type="number" min="15" max="240" step="15" value="60" aria-label="דקות"></div>
   <div class="who" id="who"></div><button class="go">להזמין את החדר</button></form><p class="msg" id="rmsg"></p>
   <h2 style="margin-top:16px">🗓️ ישיבות קרובות</h2><ul class="line" id="meetings"></ul></section>
 </div>
</div>
</div>
<script>
const $=s=>document.querySelector(s);
const AV=/*AVATARS*/[];const avImg=(k,cls)=>{if(!AV.includes(k))return null;const i=document.createElement('img');i.src='/hq/img/'+k+'.jpg';i.alt='';i.className=cls||'avimg';return i;};
const nis=n=>n.toLocaleString('he-IL')+'₪';
const C={ok:'#5ec4b6',open:'#f2b866',late:'#ef8b7e'};
function tick(){const d=new Date(),h=d.getHours();$('#hi').textContent=(h<5?'לילה טוב':h<12?'בוקר טוב':h<17?'צהריים טובים':h<21?'ערב טוב':'לילה טוב')+', יוסי';
 $('#clock').textContent=d.toLocaleDateString('he-IL',{weekday:'long',day:'numeric',month:'numeric'})+' · '+d.toTimeString().slice(0,5);}
function radar(depts){const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 400 400');svg.setAttribute('role','img');svg.setAttribute('aria-label','רדאר המחלקות');
 let h='<defs><radialGradient id="g" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#5ec4b6" stop-opacity=".10"/><stop offset="1" stop-color="#5ec4b6" stop-opacity="0"/></radialGradient><linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5ec4b6" stop-opacity="0"/><stop offset="1" stop-color="#5ec4b6" stop-opacity=".35"/></linearGradient></defs>';
 h+='<circle cx="200" cy="200" r="190" fill="url(#g)"/>';
 for(const r of [60,120,180])h+=`<circle cx="200" cy="200" r="${r}" fill="none" stroke="#23394b"/>`;
 h+='<line x1="20" y1="200" x2="380" y2="200" stroke="#1d3141"/><line x1="200" y1="20" x2="200" y2="380" stroke="#1d3141"/>';
 h+='<g class="sweep"><path d="M200 200 L380 200 A180 180 0 0 0 327 73 Z" fill="url(#sw)"/></g>';
 depts.forEach((d,i)=>{const a=-Math.PI/2+i*2*Math.PI/depts.length;const busy=d.late?180:d.open?120:70;const r=Math.min(170,busy);
  const x=200+r*Math.cos(a),y=200+r*Math.sin(a);const c=d.late?C.late:d.open?C.open:C.ok;
  h+=`<circle class="blip" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${8+Math.min(10,d.open+d.late*2)}" fill="${c}" fill-opacity=".25"/><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5" fill="${c}"/>`;
  h+=`<text x="${(200+(r+(r>150?-22:22))*Math.cos(a)).toFixed(1)}" y="${(200+(r+(r>150?-22:22))*Math.sin(a)+5).toFixed(1)}" text-anchor="middle" font-size="15" fill="#e4edf3">${d.emoji}</text>`;});
 svg.innerHTML=h;$('#radar').replaceChildren(svg);
 const lg=$('#legend');lg.replaceChildren();for(const d of depts){const el=document.createElement('div');const i=document.createElement('i');i.style.background=d.late?C.late:d.open?C.open:C.ok;
  const e=document.createElement('span');e.className='e';e.textContent=d.emoji;const n=document.createElement('span');n.className='nm';n.textContent=d.name;const s=document.createElement('small');s.textContent=d.late?d.late+' באיחור':d.open?d.open+' פתוחות':'שקט';el.append(i,e,n,s);lg.append(el);}}
function li(i,showDay){const el=document.createElement('li');el.className='it '+i.kind;
 const t=document.createElement('span');t.className='t';t.textContent=showDay?i.day.slice(8)+'.'+i.day.slice(5,7):(i.time||'כל היום');
 const d=document.createElement('span');d.className='d';const n=document.createElement('span');n.className='n';n.textContent=i.title;el.append(t,d,n);
 if(i.can_done){const b=document.createElement('button');b.textContent='✓ בוצע';b.onclick=async()=>{b.disabled=true;const r=await post('done',{id:i.id});if(r.ok){n.textContent=r.title;el.className='it done';b.remove();load();}else{b.disabled=false;msg(r.msg||'לא הצליח');}};el.append(b);}
 else el.append(document.createElement('span'));return el;}
function fill(id,items,showDay,empty){const ul=$(id);ul.replaceChildren();if(!items.length){const e=document.createElement('li');e.className='empty';e.textContent=empty;ul.append(e);return;}
 const nowS=new Date().toTimeString().slice(0,5);let placed=id!=='#today';
 for(const i of items){if(!placed&&i.time&&i.time>nowS){const n=document.createElement('li');n.className='now';n.textContent='עכשיו '+nowS;ul.append(n);placed=true;}ul.append(li(i,showDay));}}
async function getToday(){for(let i=0;i<3;i++){try{const r=await fetch('/hq/api/today',{credentials:'same-origin'});if(r.status==401)return 401;if(r.ok)return await r.json();}catch(e){}await new Promise(z=>setTimeout(z,2500*(i+1)));}throw new Error('load');}
async function load(){try{$('#upd').textContent='מתעדכן…';const s=await getToday();if(s===401){location.reload();return;}S=s;if($('#msg').textContent.startsWith('לא הצלחתי לטעון'))msg('');
 $('#t-open').textContent=s.tiles.open;$('#t-late').textContent=s.tiles.late;$('#t-done').textContent=s.tiles.done7;$('#t-spent').textContent=nis(s.tiles.spent);
 if(!MM.ym||MM.cur){$('#m-out').textContent=nis(s.money.spent);$('#m-in').textContent=nis(s.money.income);}learnList(s.learning||{});brain(s.brain||{});radar(s.depts||[]);
 const al=$('#alerts');al.replaceChildren();if(!(s.alerts||[]).length){const e=document.createElement('div');e.className='empty';e.textContent='הכול שקט 🌿';al.append(e);}
 for(const a of s.alerts||[]){const e=document.createElement('div');e.className='al '+a.level;e.textContent=a.text;al.append(e);}
 fill('#today',s.today,false,'אין כלום ביומן היום 🌿');fill('#tomorrow',s.tomorrow,false,'מחר פנוי');fill('#late',s.late,true,'אין משימות באיחור 👏');
 $('#late-h').textContent='⏳ מחכה מימים קודמים ('+s.late.length+')';render();}catch(e){msg('לא הצלחתי לטעון. נסה לרענן.');upd();}}
async function post(a,b){const r=await fetch('/hq/api/'+a,{method:'POST',credentials:'same-origin',headers:{'content-type':'application/json','x-hq':'1'},body:JSON.stringify(b)});return r.json();}
function msg(t){$('#msg').textContent=t;}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button').forEach(x=>x.setAttribute('aria-selected',x===b));$('#exp').hidden=b.dataset.f!=='exp';$('#task').hidden=b.dataset.f!=='task';});
$('#task [name=day]').value=new Date().toISOString().slice(0,10);
for(const f of ['exp','task'])$('#'+f).onsubmit=async ev=>{ev.preventDefault();const fd=Object.fromEntries(new FormData(ev.target));const btn=ev.target.querySelector('button');btn.disabled=true;
 const r=await post(f==='exp'?'expense':'task',fd);btn.disabled=false;if(r.ok){msg('✅ נרשם: '+r.title);ev.target.reset();$('#task [name=day]').value=new Date().toISOString().slice(0,10);load();}else msg(r.msg||'לא הצליח');};
const LOOKS=['war','apple'];function setLook(l){document.body.classList.toggle('apple',l==='apple');try{localStorage.setItem('hq-look',l)}catch(e){}
 const m=document.querySelector('meta[name=theme-color]');if(m)m.content=l==='apple'?'#f5f6f8':'#101c27';$('#look').textContent=l==='apple'?'🛰️ חדר מבצעים':'🍏 אפל נקי';}
let look=new URLSearchParams(location.search).get('look');if(!LOOKS.includes(look)){try{look=localStorage.getItem('hq-look')}catch(e){}}setLook(LOOKS.includes(look)?look:'war');
$('#look').onclick=()=>setLook(document.body.classList.contains('apple')?'war':'apple');
const ROLES={cfo:'כספים ותזרים',finance:'CFO – תקציב וביטוחים',home:'הוצאות הבית',cmo:'שיווק ופוסטים',cto:'טכנולוגיה ואוטומציות',admin:'משימות והזמנות',personal:'כושר ואישי',legal:'משפטית ורגולציה'};
const PAGES=[{k:'main',l:'🏛️ המטה'},{k:'cfo',l:'💰 יונתן'},{k:'finance',l:'📊 רות'},{k:'home',l:'🏠 ננסי'},{k:'cmo',l:'📣 ג׳סיקה'},{k:'cto',l:'🧠 אמילי'},{k:'admin',l:'🗂️ סוזן'},{k:'personal',l:'❤️ ג׳ניפר'},{k:'legal',l:'⚖️ אוליביה'},{k:'room',l:'🪑 חדר ישיבות'}];
let page='main',S=null;
function chips(){const c=$('#chips');c.replaceChildren();for(const p of PAGES){const b=document.createElement('button');b.type='button';b.textContent=p.l;if(p.k===page)b.setAttribute('aria-current','page');b.onclick=()=>go(p.k);c.append(b);}
 const cur=c.querySelector('[aria-current]');if(cur)cur.scrollIntoView({block:'nearest',inline:'center'});}
function go(k){page=k;try{history.replaceState(null,'','#'+k)}catch(e){}$('#v-main').hidden=k!=='main';$('#v-room').hidden=k!=='room';$('#v-dept').hidden=(k==='main'||k==='room');chips();render();window.scrollTo({top:0,behavior:'smooth'});}
function step(d){const i=PAGES.findIndex(p=>p.k===page);go(PAGES[(i+d+PAGES.length)%PAGES.length].k);}
$('#prev').onclick=()=>step(-1);$('#next').onclick=()=>step(1);
let tx=null;document.addEventListener('touchstart',e=>{tx=e.touches[0].clientX},{passive:true});
document.addEventListener('touchend',e=>{if(tx===null)return;const dx=e.changedTouches[0].clientX-tx;tx=null;if(Math.abs(dx)>70&&!e.target.closest('input,form,.chips'))step(dx>0?1:-1);},{passive:true});
document.addEventListener('keydown',e=>{if(e.target.closest('input'))return;if(e.key==='ArrowLeft')step(1);if(e.key==='ArrowRight')step(-1);});
function card(title,items,empty,showDay){const c=document.createElement('section');c.className='card';const h=document.createElement('h2');h.textContent=title;const ul=document.createElement('ul');ul.className='line';
 if(!items.length){const e=document.createElement('li');e.className='empty';e.textContent=empty;ul.append(e);}else for(const i of items)ul.append(li(i,showDay));c.append(h,ul);return c;}
function deptView(k){const v=$('#v-dept');v.replaceChildren();if(!S)return;const d=(S.depts||[]).find(x=>x.key===k);if(!d)return;
 const head=document.createElement('section');head.className='card';const dh=document.createElement('div');dh.className='dhead';
 const av=document.createElement('span');av.className='av';const pi=avImg(k);if(pi)av.append(pi);else av.textContent=d.emoji;const tt=document.createElement('div');const h=document.createElement('h2');h.textContent=d.name;const p=document.createElement('p');p.textContent=ROLES[k]||'';tt.append(h,p);dh.append(av,tt);
 const by=a=>(a||[]).filter(i=>i.dept===k);const st=document.createElement('div');st.className='stat3';
 for(const [n,l,col] of [[by(S.today).filter(i=>i.can_done).length,'פתוחות היום',''],[by(S.late).length,'באיחור','var(--hot)'],[by(S.done_week).length,'בוצעו השבוע','var(--acc)']]){const x=document.createElement('div');const b=document.createElement('b');b.textContent=n;if(col)b.style.color=col;const sp=document.createElement('span');sp.textContent=l;x.append(b,sp);st.append(x);}
 head.append(dh,st);const g=document.createElement('div');g.className='grid2';
 const left=document.createElement('div');left.style.cssText='display:grid;gap:16px;align-content:start';left.append(card('☀️ היום',by(S.today),'אין משימות היום'),card('⏳ באיחור',by(S.late),'אין משימות באיחור 👏',true));
 const right=document.createElement('div');right.style.cssText='display:grid;gap:16px;align-content:start';right.append(learnCard(k),card('📅 השבוע הקרוב',by(S.week),'אין כלום ב-7 הימים הקרובים',true),card('✅ מה נעשה השבוע',by(S.done_week).slice(-15).reverse(),'עוד לא נרשם שום דבר השבוע',true));
 g.append(left,right);v.append(head,g);}
function roomView(){if(!S)return;const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 540 430');svg.setAttribute('role','img');svg.setAttribute('aria-label','שולחן הישיבות');
 const ds=S.depts||[];let h='<ellipse cx="270" cy="200" rx="145" ry="66" fill="var(--bg2)" stroke="var(--line)" stroke-width="2"/><text x="270" y="196" text-anchor="middle" font-size="16" fill="var(--mut)">ישיבת צוות</text><text x="270" y="218" text-anchor="middle" font-size="13" fill="var(--mut)">שולה מנחה</text>';
 ds.forEach((d,i)=>{const a=-Math.PI/2+i*2*Math.PI/ds.length;const x=270+215*Math.cos(a),y=200+145*Math.sin(a);const c=d.late?C.late:d.open?C.open:C.ok;
  const rep=d.late?d.late+' באיחור':d.open?d.open+' פתוחות':'הכול בסדר';
  h+=`<circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="27" fill="var(--card)" stroke="${c}" stroke-width="3"/><text x="${x.toFixed(0)}" y="${(y+8).toFixed(0)}" text-anchor="middle" font-size="24">${d.emoji}</text>`;
  h+=`<text x="${x.toFixed(0)}" y="${(y+46).toFixed(0)}" text-anchor="middle" font-size="13" fill="var(--fg)">${d.name}</text><text x="${x.toFixed(0)}" y="${(y+62).toFixed(0)}" text-anchor="middle" font-size="11" fill="${c}">${rep}</text>`;});
 svg.innerHTML=h;$('#table').replaceChildren(svg);
 const ag=$('#agenda');ag.replaceChildren();const items=(S.late||[]).slice(-8).reverse();if(!items.length){const e=document.createElement('li');e.className='empty';e.textContent='אין נושאים פתוחים 👏';ag.append(e);}else items.forEach(i=>ag.append(li(i,true)));
 const mt=$('#meetings');mt.replaceChildren();const ms=[...(S.today||[]),...(S.week||[])].filter(i=>i.title.startsWith('🏛️'));if(!ms.length){const e=document.createElement('li');e.className='empty';e.textContent='אין ישיבות קבועות עדיין';mt.append(e);}else ms.forEach(i=>mt.append(li(i,true)));
 const who=$('#who');if(!who.children.length)for(const d of ds){const l=document.createElement('label');const c=document.createElement('input');c.type='checkbox';c.name='depts';c.value=d.key;c.checked=true;l.append(c,document.createTextNode(d.emoji+' '+d.name));who.append(l);}}
function render(){if(page==='room')roomView();else if(page!=='main')deptView(page);}
$('#room [name=day]').value=(()=>{const d=new Date();d.setDate(d.getDate()+((7-d.getDay())%7||7));return d.toISOString().slice(0,10)})();
$('#room').onsubmit=async ev=>{ev.preventDefault();const f=ev.target;const body={topic:f.topic.value,day:f.day.value,at:f.at.value,minutes:f.minutes.value,depts:[...f.querySelectorAll('[name=depts]:checked')].map(x=>x.value)};
 const b=f.querySelector('button.go');b.disabled=true;const r=await post('room',body);b.disabled=false;$('#rmsg').textContent=r.ok?'✅ נקבע ביומן: '+r.title:(r.msg||'לא הצליח');if(r.ok){f.topic.value='';load();}};
const startPage=(location.hash||'').slice(1);page=PAGES.some(p=>p.k===startPage)?startPage:'main';
let lastLoad=0;const _load=load;load=async function(){await _load();lastLoad=Date.now();upd();if(MM.ym)money(MM.cur?'':MM.ym);};
function upd(){if(!lastLoad)return;const m=Math.round((Date.now()-lastLoad)/60000);$('#upd').textContent=m<1?'עודכן עכשיו':'עודכן לפני '+m+' דק׳';}
$('#refresh').onclick=()=>load();
const MM={ym:'',cur:true};
async function money(ym){try{const r=await fetch('/hq/api/money'+(ym?'?m='+ym:''),{credentials:'same-origin'});if(!r.ok)return;const m=await r.json();MM.ym=m.ym;MM.cur=m.is_current;MM.prev=m.prev;MM.next=m.next;
 $('#m-label').textContent='💰 '+m.label;$('#m-out').textContent=nis(m.spent);$('#m-in').textContent=nis(m.income);
 $('#m-bal').textContent=(m.balance>=0?'נשאר ':'חסר ')+nis(Math.abs(m.balance))+' · '+m.n_out+' הוצאות · '+m.n_in+' הכנסות';
 $('#m-next').disabled=m.is_current;$('#m-sum').textContent='פירוט '+m.label;
 const ul=$('#m-items');ul.replaceChildren();if(!m.items.length){const e=document.createElement('li');e.className='empty';e.textContent='אין הוצאות או הכנסות בחודש הזה';ul.append(e);}
 for(const i of [...(m.planned||[]).map(x=>({...x,pl:1})),...m.items]){const li=document.createElement('li');li.className='it '+(i.kind==='in'?'monday':'expense');const t=document.createElement('span');t.className='t';t.textContent=i.day.slice(8)+'.'+i.day.slice(5,7);
  const d=document.createElement('span');d.className='d';const n=document.createElement('span');n.className='n';n.textContent=(i.pl?'⏳ צפוי: ':'')+i.title;if(i.pl)li.style.opacity='.6';const a=document.createElement('b');a.textContent=(i.kind==='in'?'+':'−')+nis(i.amount);a.style.color=i.kind==='in'?'var(--acc)':'var(--amb)';li.append(t,d,n,a);ul.append(li);}
}catch(e){}}
$('#m-prev').onclick=()=>money(MM.prev);$('#m-next').onclick=()=>{if(!MM.cur)money(MM.next);};
function brain(b){const c=$('#brain');if(!b||!b.lines||!b.lines.length){c.hidden=true;return;}c.hidden=false;
 $('#b-score').textContent=b.score!=null?b.score+'/10':'';$('#b-sub').textContent=b.subject||'';
 const fillB=(id,arr)=>{const ul=$(id);ul.replaceChildren();for(const t of arr){const li=document.createElement('li');li.textContent=t;ul.append(li);}};
 const body=b.lines.filter(t=>!/^ביקורת המוח השני/.test(t));fillB('#b-top',body.slice(0,5));fillB('#b-all',body.slice(5));
 const a=$('#b-link');if(/^https:\/\/mail\.google\.com\//.test(b.link||''))a.href=b.link;else a.hidden=true;}
function learnList(L){const ul=$('#learn');ul.replaceChildren();const ds=(S&&S.depts)||[];let any=false;
 for(const d of ds){const l=L[d.key];if(!l||!l.topic)continue;any=true;const li=document.createElement('li');const e=document.createElement('span');e.className='e';const pi=avImg(d.key,'avsm');if(pi)e.append(pi);else e.textContent=d.emoji;
  const t=document.createElement('span');t.className='t';t.textContent=d.name+': '+l.topic;const sm=document.createElement('small');sm.textContent=(l.progress||'')+(l.status?' · '+l.status:'');li.append(e,t,sm);li.onclick=()=>go(d.key);ul.append(li);}
 if(!any){const e=document.createElement('li');e.className='empty';e.textContent='עוד אין נושאי לימוד';ul.append(e);}}
function learnCard(k){const l=((S&&S.learning)||{})[k];const c=document.createElement('section');c.className='card';const h=document.createElement('h2');h.textContent='📚 לומדת החודש';c.append(h);
 const b=document.createElement('div');b.className='lbox';c.append(b);
 if(!l||!l.topic){const p=document.createElement('p');p.className='sub2';p.textContent='עוד אין נושא לימוד החודש.';b.append(p);return c;}
 const h3=document.createElement('h3');h3.textContent=l.topic;const src=document.createElement('div');src.className='src';src.append(document.createTextNode('ממי לומדים: '+(l.from||'')+' '));
 if(/^https:\/\//.test(l.link||'')){const a=document.createElement('a');a.href=l.link;a.target='_blank';a.rel='noopener';a.textContent='למקור ↗';src.append(a);}
 const pr=document.createElement('div');pr.className='src';pr.textContent=(l.month||'')+' · '+(l.progress||'')+(l.updated?' · עודכן '+l.updated:'');b.append(h3,src,pr);
 if(l.why){const w=document.createElement('div');w.textContent='למה: '+l.why;b.append(w);}
 if((l.lessons||[]).length){const t=document.createElement('div');t.textContent='מה למדה:';const ul=document.createElement('ul');for(const x of l.lessons){const li=document.createElement('li');li.textContent=x;ul.append(li);}b.append(t,ul);}
 if(l.apply){const ap=document.createElement('div');ap.className='ap';ap.textContent='🔧 מה משתנה בעבודה: '+l.apply;if(l.status){const p=document.createElement('span');p.className='pill '+(l.status==='פעיל'?'ok':'wait');p.textContent=l.status;ap.append(p);}
  if(l.check){const ck=document.createElement('div');ck.className='src';ck.textContent='בדיקה: '+l.check;ap.append(ck);}b.append(ap);}
 if((l.changes||[]).length){const t=document.createElement('div');t.textContent='✅ שינויים שכבר עובדים:';const ul=document.createElement('ul');for(const x of l.changes){const li=document.createElement('li');li.textContent=x.name+(x.what?' – '+x.what:'');ul.append(li);}b.append(t,ul);}
 return c;}
window.addEventListener('hashchange',()=>{const k=(location.hash||'').slice(1);if(k!==page&&PAGES.some(p=>p.k===k))go(k);});
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-lastLoad>20000)load();});
window.addEventListener('focus',()=>{if(Date.now()-lastLoad>20000)load();});
window.addEventListener('pageshow',e=>{if(e.persisted)load();});
const b2a=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'==='.slice((s.length+3)%4)),c=>c.charCodeAt(0)).buffer;
const a2b=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const ap=(a,b)=>fetch('/hq/auth/'+a,{method:'POST',credentials:'same-origin',headers:{'content-type':'application/json','x-hq':'1'},body:JSON.stringify(b||{})}).then(r=>r.json());
async function secStatus(){const s=await ap('status');$('#sec-st').textContent=(s.passkeys?'✅ Face ID מוגדר ב-'+s.passkeys+' מכשירים ('+s.names.join(', ')+')':'Face ID עוד לא מוגדר.')+' · '+(s.backup?'✅ יש קוד גיבוי':'אין קוד גיבוי');$('#sec-rm').hidden=!s.passkeys;}
$('#sec').onclick=()=>{const p=$('#secp');p.hidden=!p.hidden;if(!p.hidden)secStatus();};
$('#sec-add').onclick=async()=>{const m=$('#sec-msg');if(!window.PublicKeyCredential){m.textContent='הדפדפן הזה לא תומך ב-Face ID.';return;}
 try{const o=await ap('register-options');const pk=o.options;pk.challenge=b2a(pk.challenge);pk.user.id=b2a(pk.user.id);(pk.excludeCredentials||[]).forEach(c=>c.id=b2a(c.id));
  const c=await navigator.credentials.create({publicKey:pk});
  const name=/iPhone/.test(navigator.userAgent)?'אייפון':/iPad/.test(navigator.userAgent)?'אייפד':/Mac/.test(navigator.userAgent)?'מק':/Android/.test(navigator.userAgent)?'אנדרואיד':'מחשב';
  const cred={id:c.id,rawId:a2b(c.rawId),type:c.type,response:{clientDataJSON:a2b(c.response.clientDataJSON),attestationObject:a2b(c.response.attestationObject),transports:c.response.getTransports?c.response.getTransports():[]}};
  const r=await ap('register',{cid:o.cid,credential:cred,name});m.textContent=r.msg;secStatus();
 }catch(e){m.textContent='ההגדרה בוטלה או לא הצליחה. נסה שוב.';}};
$('#sec-code').onclick=async()=>{const r=await ap('backup');const b=$('#sec-show');b.textContent=r.code;b.hidden=false;$('#sec-msg').textContent=r.msg;secStatus();};
$('#sec-rm').onclick=async()=>{const b=$('#sec-rm');if(b.dataset.sure!=='1'){b.dataset.sure='1';b.textContent='בטוח? ללחוץ שוב כדי למחוק';return;}const r=await ap('remove-passkeys');$('#sec-msg').textContent=r.msg;b.dataset.sure='';b.textContent='למחוק את כל ה-Face ID';secStatus();};
{const si=avImg('shula','meimg');if(si){si.title='שולה – ראש המטה';$('#me').append(si);}}
tick();setInterval(()=>{tick();upd();},30000);go(page);load();money('');setInterval(()=>{if(!document.hidden)load();},60000);
</script>"""
