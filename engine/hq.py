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
    return {"now": now.strftime("%H:%M"), "date": today.date().isoformat(),
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
<meta name="theme-color" content="#f4f6f8"><meta name="robots" content="noindex,nofollow">
<title>המטה של שולה</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700;800&display=swap">
<style>
:root{--bg:#f4f6f8;--card:#fff;--fg:#1d2733;--mut:#6b7785;--acc:#6f8ba4;--acc2:#e8eef4;--hot:#e26d5a;--ok:#5fb98a;--line:#e6eaef;--sh:0 1px 2px rgba(20,30,45,.04),0 10px 28px rgba(20,30,45,.07);color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#12161b;--card:#1b2128;--fg:#e9eef3;--mut:#93a0ad;--acc:#8fa9c2;--acc2:#24303b;--hot:#f08a78;--ok:#6fcb9a;--line:#2a333d;--sh:0 1px 2px rgba(0,0,0,.3),0 10px 28px rgba(0,0,0,.35);color-scheme:dark}}
*{box-sizing:border-box}[hidden]{display:none!important}html,body{margin:0;background:var(--bg);color:var(--fg);font-family:Heebo,system-ui,sans-serif}
body{padding:max(16px,env(safe-area-inset-top)) 16px 40px}
.w{max-width:980px;margin:0 auto;display:grid;gap:18px}
.card{background:var(--card);border-radius:22px;box-shadow:var(--sh);padding:20px}
.hi{font-weight:300;font-size:clamp(30px,6vw,46px);margin:0;letter-spacing:-.01em}
.sub{color:var(--mut);margin:2px 0 0;font-size:15px}
.brand{color:var(--acc);font-weight:700;letter-spacing:.06em;font-size:13px;margin:0 0 6px}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
@media (max-width:640px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
.tile{background:var(--card);border-radius:18px;box-shadow:var(--sh);padding:16px 10px;text-align:center}
.tile span{display:block;font-size:13px;font-weight:600}.tile b{display:block;font-size:40px;font-weight:500;color:var(--acc);font-variant-numeric:tabular-nums;line-height:1.1;margin-top:6px}
.tile.hot b{color:var(--hot)}
.grid{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:18px}
@media (max-width:820px){.grid{grid-template-columns:1fr}}
h2{font-size:18px;margin:0 0 12px;font-weight:700}
.line{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.it{display:grid;grid-template-columns:52px 10px minmax(0,1fr) auto;gap:10px;align-items:center;padding:10px 12px;border-radius:14px;background:var(--bg)}
.it .t{font-variant-numeric:tabular-nums;font-weight:600;font-size:14px;color:var(--mut)}
.it .d{width:10px;height:10px;border-radius:50%;background:var(--acc)}
.it .n{min-width:0;overflow-wrap:anywhere;font-size:15px}
.it.expense .d{background:#e7a64a}.it.task .d{background:var(--hot)}.it.done .d{background:var(--acc)}.it.bike .d,.it.monday .d{background:var(--ok)}.it.trip .d{background:#e7c24a}
.it.done .n{color:var(--mut)}
.now{display:flex;align-items:center;gap:8px;color:var(--hot);font-size:12px;font-weight:700}.now:after{content:"";flex:1;height:2px;background:var(--hot);border-radius:2px}
button,.btn{font:inherit;border:0;border-radius:999px;padding:8px 14px;cursor:pointer;background:var(--acc2);color:var(--acc);font-weight:600}
button.go{background:var(--acc);color:#fff}button:disabled{opacity:.5}
.empty{color:var(--mut);text-align:center;padding:14px;border:1px dashed var(--line);border-radius:14px}
.money{display:grid;grid-template-columns:1fr 1fr;gap:10px}.money div{background:var(--bg);border-radius:14px;padding:12px;text-align:center}
.money b{display:block;font-size:26px;font-weight:500;font-variant-numeric:tabular-nums}.money .in b{color:var(--ok)}.money .out b{color:#d98a2b}
form{display:grid;gap:8px}input,select{font:inherit;padding:10px 12px;border-radius:12px;border:1px solid var(--line);background:var(--bg);color:var(--fg);width:100%;min-width:0}
.row{display:flex;gap:8px}.row>*{flex:1;min-width:0}
.tabs{display:flex;gap:8px}.tabs button[aria-selected=true]{background:var(--acc);color:#fff}
details summary{cursor:pointer;font-weight:600;color:var(--mut)}
.msg{font-size:13px;color:var(--mut);min-height:1em}
.login{max-width:420px;margin:12vh auto;text-align:center}
</style></head><body>"""

LOGIN_BODY = """<div class="card login"><p class="brand">המטה של שולה</p><h1 class="hi">שלום, יוסי</h1><p class="sub">{msg}</p></div>"""

APP_BODY = r"""<div class="w">
<header class="card"><p class="brand">המטה של שולה</p><h1 class="hi" id="hi">שלום, יוסי</h1><p class="sub" id="date"></p></header>
<section class="tiles" aria-label="מספרים">
 <div class="tile"><span>משימות היום</span><b id="t-open">–</b></div>
 <div class="tile hot"><span>באיחור</span><b id="t-late">–</b></div>
 <div class="tile"><span>בוצעו השבוע</span><b id="t-done">–</b></div>
 <div class="tile"><span>הוצאות היום</span><b id="t-spent">–</b></div>
</section>
<div class="grid">
 <section class="card"><h2>☀️ היום שלי</h2><ul class="line" id="today"></ul>
  <details style="margin-top:14px"><summary id="late-h">⏳ מחכה מימים קודמים</summary><ul class="line" id="late" style="margin-top:10px"></ul></details>
  <details style="margin-top:10px"><summary>🌙 מחר</summary><ul class="line" id="tomorrow" style="margin-top:10px"></ul></details>
 </section>
 <div style="display:grid;gap:18px;align-content:start">
  <section class="card"><h2>➕ הוספה מהירה</h2>
   <div class="tabs" role="tablist"><button type="button" role="tab" aria-selected="true" data-f="exp">💸 הוצאה</button><button type="button" role="tab" aria-selected="false" data-f="task">📌 משימה</button></div>
   <form id="exp" style="margin-top:12px"><div class="row"><input name="amount" inputmode="decimal" placeholder="סכום ₪" required><input name="how" placeholder="איך שילמת"></div><input name="what" placeholder="על מה ואיפה" required><button class="go">לרשום ביומן</button></form>
   <form id="task" hidden style="margin-top:12px"><input name="title" placeholder="מה צריך לעשות" required><div class="row"><input name="day" type="date" required><input name="at" type="time" value="10:00"></div><button class="go">להוסיף ליומן</button></form>
   <p class="msg" id="msg"></p>
  </section>
  <section class="card"><h2>💰 הכסף של החודש</h2><div class="money"><div class="out"><span>הוצאות</span><b id="m-out">–</b></div><div class="in"><span>הכנסות</span><b id="m-in">–</b></div></div></section>
 </div>
</div>
</div>
<script>
const $=s=>document.querySelector(s);
const nis=n=>n.toLocaleString('he-IL')+'₪';
function greet(){const h=new Date().getHours();$('#hi').textContent=(h<5?'לילה טוב':h<12?'בוקר טוב':h<17?'צהריים טובים':h<21?'ערב טוב':'לילה טוב')+', יוסי';
 $('#date').textContent=new Date().toLocaleDateString('he-IL',{weekday:'long',day:'numeric',month:'long',year:'numeric'});}
function li(i,showDay){const el=document.createElement('li');el.className='it '+i.kind;
 const t=document.createElement('span');t.className='t';t.textContent=showDay?i.day.slice(8)+'.'+i.day.slice(5,7):(i.time||'כל היום');
 const d=document.createElement('span');d.className='d';const n=document.createElement('span');n.className='n';n.textContent=i.title;
 el.append(t,d,n);
 if(i.can_done){const b=document.createElement('button');b.textContent='✓ בוצע';b.onclick=async()=>{b.disabled=true;const r=await post('done',{id:i.id});if(r.ok){n.textContent=r.title;el.className='it done';b.remove();load();}else{b.disabled=false;msg(r.msg||'לא הצליח');}};el.append(b);}
 else el.append(document.createElement('span'));return el;}
function fill(id,items,showDay,empty){const ul=$(id);ul.replaceChildren();if(!items.length){const e=document.createElement('li');e.className='empty';e.textContent=empty;ul.append(e);return;}
 const nowS=new Date().toTimeString().slice(0,5);let placed=!id.includes('today');
 for(const i of items){if(!placed&&i.time&&i.time>nowS){const n=document.createElement('li');n.className='now';n.textContent='עכשיו '+nowS;ul.append(n);placed=true;}ul.append(li(i,showDay));}}
async function load(){try{const r=await fetch('/hq/api/today',{credentials:'same-origin'});if(r.status==401){location.reload();return;}const s=await r.json();
 $('#t-open').textContent=s.tiles.open;$('#t-late').textContent=s.tiles.late;$('#t-done').textContent=s.tiles.done7;$('#t-spent').textContent=nis(s.tiles.spent);
 $('#m-out').textContent=nis(s.money.spent);$('#m-in').textContent=nis(s.money.income);
 fill('#today',s.today,false,'אין כלום ביומן היום 🌿');fill('#tomorrow',s.tomorrow,false,'מחר פנוי');fill('#late',s.late,true,'אין משימות באיחור 👏');
 $('#late-h').textContent='⏳ מחכה מימים קודמים ('+s.late.length+')';}catch(e){msg('לא הצלחתי לטעון. נסה לרענן.');}}
async function post(a,b){const r=await fetch('/hq/api/'+a,{method:'POST',credentials:'same-origin',headers:{'content-type':'application/json','x-hq':'1'},body:JSON.stringify(b)});return r.json();}
function msg(t){$('#msg').textContent=t;}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button').forEach(x=>x.setAttribute('aria-selected',x===b));$('#exp').hidden=b.dataset.f!=='exp';$('#task').hidden=b.dataset.f!=='task';});
$('#task [name=day]').value=new Date().toISOString().slice(0,10);
for(const f of ['exp','task'])$('#'+f).onsubmit=async ev=>{ev.preventDefault();const fd=Object.fromEntries(new FormData(ev.target));const btn=ev.target.querySelector('button');btn.disabled=true;
 const r=await post(f==='exp'?'expense':'task',fd);btn.disabled=false;if(r.ok){msg('✅ נרשם: '+r.title);ev.target.reset();$('#task [name=day]').value=new Date().toISOString().slice(0,10);load();}else msg(r.msg||'לא הצליח');};
greet();load();setInterval(load,120000);
</script>"""
