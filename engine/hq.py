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


def _authed(request: Request) -> bool:
    return check_token(request.cookies.get(COOKIE, ""), "session")


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
            "can_done": _is_open_task(e)}


DEPTS = [  # (מפתח, שם, אימוג'י, מילים בכותרת)
    ("cfo", "רייצ׳ל", "💰", ("💰", "רייצ׳ל", "מוני", "הכנסה", "קבלה", "תשלום", "חשבונית")),
    ("finance", "רות", "📊", ("📊", "רות", "חסיה", "ביטוח", "תקציב")),
    ("home", "ננסי", "🏠", ("🏠", "ננסי", "בתיה", "💸")),
    ("cmo", "ג׳סיקה", "📣", ("📣", "ג׳סיקה", "שירי", "פוסט", "שיווק", "aCare", "AlphaCare")),
    ("cto", "אמילי", "🧠", ("🧠", "אמילי", "רעיה", "שולה", "אפליקצי")),
    ("admin", "סוזן", "🗂️", ("🗂️", "סוזן", "סדרית")),
    ("personal", "ג׳ניפר", "❤️", ("❤️", "ג׳ניפר", "לבנה", "חדר כושר", "אימון")),
]


def dept_of(title: str) -> str:
    for key, _, _, words in DEPTS:
        if any(w in (title or "") for w in words):
            return key
    return "admin"


def snapshot(now: datetime | None = None) -> dict:
    now = now or datetime.now(tools_calendar.TZ)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = today.replace(day=1)
    since = min(month, today - timedelta(days=14))
    evs = [e for e in _events(since, today + timedelta(days=2)) if _visible(e)]
    day_items, tomorrow, late = [], [], []
    done7 = spent_today = spent_month = income_month = 0
    for e in evs:
        when, _ = _start(e)
        title = e.get("summary") or ""
        if when >= month and when < today + timedelta(days=1):
            if e.get("colorId") == "6":
                spent_month += _amount(title)
            if "הכנסה" in title:
                income_month += _amount(title)
        if today <= when < today + timedelta(days=1):
            day_items.append(_item(e))
            if e.get("colorId") == "6":
                spent_today += _amount(title)
        elif today + timedelta(days=1) <= when < today + timedelta(days=2):
            tomorrow.append(_item(e))
        elif when < today and _is_open_task(e) and when >= today - timedelta(days=14):
            late.append(_item(e))
        if e.get("colorId") == "7" and today - timedelta(days=6) <= when < today + timedelta(days=1):
            done7 += 1
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
            "today": day_items, "tomorrow": tomorrow, "late": late[-20:]}


def mark_done(event_id: str) -> dict:
    svc = tools_calendar._svc()
    e = svc.events().get(calendarId=tools_calendar.CALENDAR_ID, eventId=event_id).execute()
    if not _is_open_task(e):
        return {"ok": False, "msg": "זו לא משימה פתוחה"}
    title = "✅ בוצע: " + (e.get("summary") or "")
    svc.events().patch(calendarId=tools_calendar.CALENDAR_ID, eventId=event_id, sendUpdates="none",
                       body={"summary": title, "colorId": "7"}).execute()
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
        return HTMLResponse(_page(LOGIN_BODY.replace("{msg}", "כדי להיכנס, כתוב לשולה בוואטסאפ: <b>כניסה למטה</b>")))
    return HTMLResponse(_page(APP_BODY), headers={"Cache-Control": "no-store"})


@router.get("/hq/api/today")
def api_today(request: Request):
    if not _authed(request):
        return JSONResponse({"ok": False}, status_code=401)
    return JSONResponse(snapshot(), headers={"Cache-Control": "no-store"})


@router.post("/hq/api/{action}")
async def api_action(action: str, request: Request):
    if not _authed(request):
        return JSONResponse({"ok": False}, status_code=401)
    if request.headers.get("x-hq") != "1":  # הגנה מטפסים זרים
        return JSONResponse({"ok": False}, status_code=403)
    data = await request.json()
    if action == "done":
        return JSONResponse(mark_done(str(data.get("id", ""))))
    if action == "expense":
        try:
            amount = float(str(data.get("amount", "0")).replace(",", ""))
        except ValueError:
            amount = 0
        return JSONResponse(add_expense(amount, str(data.get("what", "")), str(data.get("how", ""))))
    if action == "task":
        return JSONResponse(add_task(str(data.get("title", "")), str(data.get("day", "")), str(data.get("at", ""))))
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
.login{max-width:420px;margin:14vh auto;text-align:center}.login h1{font-weight:300;font-size:34px;margin:6px 0}.login p{color:var(--mut)}
.brand{color:var(--acc);font-weight:700;letter-spacing:.1em;font-size:12px;margin:0}
</style></head><body>"""

LOGIN_BODY = """<div class="card login"><p class="brand">● המטה של שולה</p><h1>שלום, יוסי</h1><p>{msg}</p></div>"""

APP_BODY = r"""<div class="w">
<header class="card bar"><span class="live"><i></i>פעיל</span><h1 id="hi">המטה של שולה</h1><span class="t" id="clock"></span></header>
<section class="tiles" aria-label="מספרים">
 <div class="tile"><span>משימות היום</span><b id="t-open">–</b></div>
 <div class="tile hot"><span>באיחור</span><b id="t-late">–</b></div>
 <div class="tile"><span>בוצעו השבוע</span><b id="t-done">–</b></div>
 <div class="tile amb"><span>הוצאות היום</span><b id="t-spent">–</b></div>
</section>
<div class="grid">
 <section class="card"><h2>🛰️ המחלקות – עכשיו</h2><div class="radar" id="radar"></div><div class="legend" id="legend"></div></section>
 <section class="card"><h2>☀️ היום שלי</h2><ul class="line" id="today"></ul>
  <details style="margin-top:12px"><summary id="late-h">⏳ מחכה מימים קודמים</summary><ul class="line" id="late" style="margin-top:8px"></ul></details>
  <details style="margin-top:8px"><summary>🌙 מחר</summary><ul class="line" id="tomorrow" style="margin-top:8px"></ul></details>
 </section>
 <div style="display:grid;gap:16px;align-content:start">
  <section class="card"><h2>🚨 התראות</h2><div class="alerts" id="alerts"></div></section>
  <section class="card"><h2>➕ הוספה מהירה</h2>
   <div class="tabs" role="tablist"><button type="button" role="tab" aria-selected="true" data-f="exp">💸 הוצאה</button><button type="button" role="tab" aria-selected="false" data-f="task">📌 משימה</button></div>
   <form id="exp" style="margin-top:10px"><div class="row"><input name="amount" inputmode="decimal" placeholder="סכום ₪" required><input name="how" placeholder="איך שילמת"></div><input name="what" placeholder="על מה ואיפה" required><button class="go">לרשום ביומן</button></form>
   <form id="task" hidden style="margin-top:10px"><input name="title" placeholder="מה צריך לעשות" required><div class="row"><input name="day" type="date" required><input name="at" type="time" value="10:00"></div><button class="go">להוסיף ליומן</button></form>
   <p class="msg" id="msg"></p>
  </section>
  <section class="card"><h2>💰 החודש</h2><div class="money"><div class="out"><span>הוצאות</span><b id="m-out">–</b></div><div class="in"><span>הכנסות</span><b id="m-in">–</b></div></div></section>
 </div>
</div>
</div>
<script>
const $=s=>document.querySelector(s);
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
  const n=document.createElement('span');n.textContent=d.emoji+' '+d.name;const s=document.createElement('small');s.textContent=d.late?d.late+' באיחור':d.open?d.open+' פתוחות':'שקט';el.append(i,n,s);lg.append(el);}}
function li(i,showDay){const el=document.createElement('li');el.className='it '+i.kind;
 const t=document.createElement('span');t.className='t';t.textContent=showDay?i.day.slice(8)+'.'+i.day.slice(5,7):(i.time||'כל היום');
 const d=document.createElement('span');d.className='d';const n=document.createElement('span');n.className='n';n.textContent=i.title;el.append(t,d,n);
 if(i.can_done){const b=document.createElement('button');b.textContent='✓ בוצע';b.onclick=async()=>{b.disabled=true;const r=await post('done',{id:i.id});if(r.ok){n.textContent=r.title;el.className='it done';b.remove();load();}else{b.disabled=false;msg(r.msg||'לא הצליח');}};el.append(b);}
 else el.append(document.createElement('span'));return el;}
function fill(id,items,showDay,empty){const ul=$(id);ul.replaceChildren();if(!items.length){const e=document.createElement('li');e.className='empty';e.textContent=empty;ul.append(e);return;}
 const nowS=new Date().toTimeString().slice(0,5);let placed=id!=='#today';
 for(const i of items){if(!placed&&i.time&&i.time>nowS){const n=document.createElement('li');n.className='now';n.textContent='עכשיו '+nowS;ul.append(n);placed=true;}ul.append(li(i,showDay));}}
async function load(){try{const r=await fetch('/hq/api/today',{credentials:'same-origin'});if(r.status==401){location.reload();return;}const s=await r.json();
 $('#t-open').textContent=s.tiles.open;$('#t-late').textContent=s.tiles.late;$('#t-done').textContent=s.tiles.done7;$('#t-spent').textContent=nis(s.tiles.spent);
 $('#m-out').textContent=nis(s.money.spent);$('#m-in').textContent=nis(s.money.income);radar(s.depts||[]);
 const al=$('#alerts');al.replaceChildren();if(!(s.alerts||[]).length){const e=document.createElement('div');e.className='empty';e.textContent='הכול שקט 🌿';al.append(e);}
 for(const a of s.alerts||[]){const e=document.createElement('div');e.className='al '+a.level;e.textContent=a.text;al.append(e);}
 fill('#today',s.today,false,'אין כלום ביומן היום 🌿');fill('#tomorrow',s.tomorrow,false,'מחר פנוי');fill('#late',s.late,true,'אין משימות באיחור 👏');
 $('#late-h').textContent='⏳ מחכה מימים קודמים ('+s.late.length+')';}catch(e){msg('לא הצלחתי לטעון. נסה לרענן.');}}
async function post(a,b){const r=await fetch('/hq/api/'+a,{method:'POST',credentials:'same-origin',headers:{'content-type':'application/json','x-hq':'1'},body:JSON.stringify(b)});return r.json();}
function msg(t){$('#msg').textContent=t;}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button').forEach(x=>x.setAttribute('aria-selected',x===b));$('#exp').hidden=b.dataset.f!=='exp';$('#task').hidden=b.dataset.f!=='task';});
$('#task [name=day]').value=new Date().toISOString().slice(0,10);
for(const f of ['exp','task'])$('#'+f).onsubmit=async ev=>{ev.preventDefault();const fd=Object.fromEntries(new FormData(ev.target));const btn=ev.target.querySelector('button');btn.disabled=true;
 const r=await post(f==='exp'?'expense':'task',fd);btn.disabled=false;if(r.ok){msg('✅ נרשם: '+r.title);ev.target.reset();$('#task [name=day]').value=new Date().toISOString().slice(0,10);load();}else msg(r.msg||'לא הצליח');};
tick();setInterval(tick,30000);load();setInterval(load,120000);
</script>"""
