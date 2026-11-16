"""סנכרון יומי בין ה-monday של AnyCan ליומן גוגל של יוסי.
1. רק פריטים חשובים מהלוח נכנסים ליומן "יוסי קט" כאירוע משלהם (סטטוס דחוף/חשוב/תקוע, או תאריך עם שעה), ומתעדכנים
   כשהתאריך או הסטטוס משתנים. כל השאר נכנס לאירוע סיכום אחד ביום: "📋 monday – סיכום היום".
   (יוסי, 15.11.2026: "כל עדכון ביומן סתם מעמיס — רק דברים חשובים, אחרי סיכום". MONDAY_CAL_ALL=1 מחזיר את הישן.)
2. פגישה חדשה ביומן שמזכירה אדם או ארגון מהלוח נרשמת כעדכון על הפריט שלו ב-monday.
רץ לבד פעם ביום בבוקר, ואפשר לבקש משולה 'סנכרני מנדיי ויומן'."""
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta

import tools_calendar
import tools_monday

log = logging.getLogger("shula.sync")
TZ = tools_calendar.TZ
SYNC_BOARD = os.environ.get("MONDAY_SYNC_BOARD", tools_monday.ANYCAN_DEFAULT_BOARD)
SYNC_HOUR = int(os.environ.get("MONDAY_SYNC_HOUR", "7"))
PAST_DAYS = 7          # תאריכים ישנים יותר לא נכנסים ליומן
MAX_UPDATES = 20       # הגנה: לא יותר מ-20 עדכונים ל-monday בריצה אחת
DONE_WORDS = {"done", "בוצע", "הושלם", "סגור", "closed", "completed"}
TAG = "shula_monday"   # סימון על אירוע שנוצר מה-monday
LOGGED = "monday_logged"  # סימון על פגישה שכבר נרשמה ב-monday
SUMMARY = "shula_monday_summary"  # סימון על אירוע הסיכום היומי
SUMMARY_DAYS = 7       # הסיכום מראה מה מתוכנן ב-7 הימים הקרובים
CAL_ALL = os.environ.get("MONDAY_CAL_ALL", "") == "1"
IMPORTANT_WORDS = ("דחוף", "חשוב", "תקוע", "באיחור", "קריטי", "urgent", "high", "critical", "stuck", "overdue", "asap")
_lock = threading.Lock()


def _board_items() -> tuple[dict, list]:
    """(הלוח, כל הפריטים שלו) מה-monday של AnyCan."""
    want = SYNC_BOARD.strip().lower()
    boards = tools_monday._anycan_boards()
    match = [b for b in boards if b["name"].strip().lower() == want] or [b for b in boards if want in b["name"].lower()]
    if not match:
        raise RuntimeError(f"לא מצאתי את הלוח '{SYNC_BOARD}' ב-monday של AnyCan")
    board = match[0]
    cols = "id name group { title } column_values { id type text value column { title } }"
    data = tools_monday._query(
        "query ($ids: [ID!]) { account { slug } boards(ids: $ids) { items_page(limit: 500) { cursor items { %s } } } }" % cols,
        {"ids": [board["id"]]}, "anycan")
    board["slug"] = (data.get("account") or {}).get("slug") or "anycan-team"
    page = data["boards"][0]["items_page"]
    items = list(page["items"])
    while page.get("cursor") and len(items) < 5000:
        page = tools_monday._query(
            "query ($c: String!) { next_items_page(cursor: $c, limit: 500) { cursor items { %s } } }" % cols,
            {"c": page["cursor"]}, "anycan")["next_items_page"]
        items += page["items"]
    return board, items


def _is_done(item: dict) -> bool:
    return any(c.get("type") == "status" and (c.get("text") or "").strip().lower() in DONE_WORDS
               for c in item["column_values"])


def _is_important(item: dict, has_time: bool = False) -> bool:
    """פריט חשוב = לא בוצע, ויש לו סטטוס/עדיפות דחוף-חשוב-תקוע, או שנקבעה לו שעה (פגישה / שיחה)."""
    if _is_done(item):
        return False
    text = " ".join((c.get("text") or "") for c in item["column_values"] if c.get("type") in ("status", "dropdown")).lower()
    return has_time or any(w in text for w in IMPORTANT_WORDS)


def _wanted_events(board: dict, items: list, today) -> dict:
    """{מפתח: אירוע יומן} לתאריכים חשובים בלוח, מ-PAST_DAYS ימים אחורה והלאה (MONDAY_CAL_ALL=1 — לכל תאריך)."""
    out = {}
    for it in items:
        status = "; ".join(f"{c['column']['title']}: {c['text']}" for c in it["column_values"]
                           if c.get("type") == "status" and c.get("text"))
        for c in it["column_values"]:
            if c.get("type") != "date" or not c.get("value"):
                continue
            try:
                val = json.loads(c["value"])
                day = datetime.strptime(val["date"], "%Y-%m-%d").date()
            except (ValueError, KeyError, TypeError):
                continue
            if day < today - timedelta(days=PAST_DAYS):
                continue
            if not CAL_ALL and not _is_important(it, bool(val.get("time"))):
                continue
            key = f"{it['id']}:{c['id']}"
            ev = {
                "summary": f"📋 {it['name']} · {c['column']['title']}",
                "description": (f"מה-monday של AnyCan, לוח {board['name']}, קבוצה {it['group']['title']}.\n"
                                + (status + "\n" if status else "")
                                + f"https://{board['slug']}.monday.com/boards/{board['id']}/pulses/{it['id']}"),
                "extendedProperties": {"private": {TAG: key}},
            }
            if val.get("time"):  # ב-monday השעה נשמרת ב-UTC
                start = datetime.strptime(f"{val['date']} {val['time']}", "%Y-%m-%d %H:%M:%S")
                ev["start"] = {"dateTime": start.isoformat() + "Z"}
                ev["end"] = {"dateTime": (start + timedelta(minutes=30)).isoformat() + "Z"}
            else:
                ev["start"] = {"date": day.isoformat()}
                ev["end"] = {"date": (day + timedelta(days=1)).isoformat()}
            # ירוק בהיר לכל מה שמגיע מה-monday; פריט שבוצע — תכלת, כמו כל משימה שבוצעה ביומן של יוסי
            ev["colorId"] = tools_calendar.COLOR_IDS["done" if _is_done(it) else "monday"]
            out[key] = ev
    return out


def _list(**kw) -> list:
    svc, out, token = tools_calendar._svc(), [], None
    while True:
        res = svc.events().list(calendarId=tools_calendar.CALENDAR_ID, pageToken=token, maxResults=250, **kw).execute()
        out += res.get("items", [])
        token = res.get("nextPageToken")
        if not token:
            return out


def _same(old: dict, new: dict) -> bool:
    def start(e):
        s = e.get("start", {})
        return s.get("date") or (s.get("dateTime") or "")[:16]
    return (old.get("summary") == new["summary"] and start(old) == start(new)
            and old.get("description") == new["description"] and old.get("colorId") == new.get("colorId"))


def _summary_event(board: dict, items: list, now: datetime) -> dict:
    """אירוע אחד ביום שמסכם את ה-monday: מה מתוכנן ל-7 ימים, מה באיחור, ומה מהם חשוב (החשובים — גם כאירוע משלהם)."""
    today, soon, late, n_imp = now.date(), [], [], 0
    for it in items:
        if _is_done(it):
            continue
        for c in it["column_values"]:
            if c.get("type") != "date" or not c.get("value"):
                continue
            try:
                val = json.loads(c["value"])
                day = datetime.strptime(val["date"], "%Y-%m-%d").date()
            except (ValueError, KeyError, TypeError):
                continue
            imp = _is_important(it, bool(val.get("time")))
            line = f"{'❗ ' if imp else '• '}{day.strftime('%d.%m')} {it['name']} ({it['group']['title']})"
            if today - timedelta(days=PAST_DAYS) <= day < today:
                late.append((day, line))
            elif today <= day <= today + timedelta(days=SUMMARY_DAYS):
                soon.append((day, line))
            else:
                continue
            n_imp += imp
    soon.sort(key=lambda x: x[0]); late.sort(key=lambda x: x[0])
    title = f"📋 monday – סיכום היום: {len(soon)} מתוכננים, {len(late)} באיחור"
    desc = (f"מה-monday של AnyCan, לוח {board['name']}. ❗ = חשוב (מופיע גם כאירוע משלו ביומן).\n\n"
            + (f"⏳ באיחור ({len(late)}):\n" + "\n".join(l for _, l in late[:25]) + "\n\n" if late else "")
            + (f"📅 ב-{SUMMARY_DAYS} הימים הקרובים ({len(soon)}):\n" + "\n".join(l for _, l in soon[:40]) if soon else "אין משהו מתוכנן ב-7 הימים הקרובים.")
            + f"\n\nhttps://{board['slug']}.monday.com/boards/{board['id']}")
    start = now.replace(hour=7, minute=0, second=0, microsecond=0)
    return {"summary": title, "description": desc[:8000], "colorId": tools_calendar.COLOR_IDS["monday"],
            "transparency": "transparent", "reminders": {"useDefault": False, "overrides": []},
            "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
            "end": {"dateTime": (start + timedelta(minutes=15)).isoformat(), "timeZone": "Asia/Jerusalem"},
            "extendedProperties": {"private": {SUMMARY: today.isoformat()}}}


def _write_summary(board: dict, items: list, now: datetime) -> str:
    svc, cal = tools_calendar._svc(), tools_calendar.CALENDAR_ID
    ev = _summary_event(board, items, now)
    found = _list(privateExtendedProperty=f"{SUMMARY}={now.date().isoformat()}", showDeleted=False)
    if found:
        svc.events().patch(calendarId=cal, eventId=found[0]["id"], body=ev).execute()
    else:
        svc.events().insert(calendarId=cal, body=ev).execute()
    return ev["summary"]


def _monday_to_calendar(board: dict, items: list, now: datetime, preview: bool = False) -> list:
    wanted = _wanted_events(board, items, now.date())
    svc, cal = tools_calendar._svc(), tools_calendar.CALENDAR_ID
    existing = {}
    for e in _list(privateExtendedProperty=f"{TAG}_on=1", showDeleted=False,
                   timeMin=(now - timedelta(days=PAST_DAYS + 1)).isoformat()):
        existing[e["extendedProperties"]["private"][TAG]] = e
    if preview:
        new = sorted((ev["start"].get("date") or ev["start"]["dateTime"][:10], ev["summary"])
                     for key, ev in wanted.items() if key not in existing)
        return ([f"בדיקה בלבד, לא נכתב כלום. ייכנסו ליומן {len(new)} אירועים חדשים (מתוך {len(wanted)} תאריכים חשובים בלוח), ועוד אירוע סיכום אחד:"]
                + [f"- {d[8:]}.{d[5:7]}.{d[:4]} {name}" for d, name in new[:40]]
                + (["ועוד..."] if len(new) > 40 else []))
    added = changed = removed = 0
    for key, ev in wanted.items():
        ev["extendedProperties"]["private"][f"{TAG}_on"] = "1"
        old = existing.pop(key, None)
        if old is None:
            svc.events().insert(calendarId=cal, body=ev).execute()
            added += 1
        elif not _same(old, ev):
            svc.events().patch(calendarId=cal, eventId=old["id"], body=ev).execute()
            changed += 1
    for old in existing.values():  # התאריך נמחק מה-monday או שהפריט הוסר
        svc.events().delete(calendarId=cal, eventId=old["id"]).execute()
        removed += 1
    out = [f"מה-monday ליומן (רק חשובים): {added} חדשים, {changed} עודכנו, {removed} הוסרו ({len(wanted)} תאריכים חשובים בלוח)."]
    if not CAL_ALL:
        out.append("סיכום ביומן: " + _write_summary(board, items, now))
    return out


def _when(e: dict) -> str:
    s = e.get("start", {})
    if s.get("date"):
        return datetime.strptime(s["date"], "%Y-%m-%d").strftime("%d.%m.%Y")
    return datetime.fromisoformat(s["dateTime"]).astimezone(TZ).strftime("%d.%m.%Y %H:%M")


def _matches(e: dict, items: list) -> list:
    """פריטים מהלוח שהפגישה קשורה אליהם: השם שלהם מופיע בפגישה, או שהמייל שלהם מוזמן."""
    text = " ".join([e.get("summary") or "", e.get("description") or "", e.get("location") or ""]
                    + [a.get("displayName") or "" for a in e.get("attendees", [])]).lower()
    mails = {(a.get("email") or "").lower() for a in e.get("attendees", [])} - {""}
    hit = []
    for it in items:
        name = it["name"].strip().lower()
        by_name = len(name) >= 5 and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text)
        by_mail = any(c.get("type") == "email" and (c.get("text") or "").strip().lower() in mails
                      for c in it["column_values"])
        if by_name or by_mail:
            hit.append(it)
    return hit[:3]


def _calendar_to_monday(items: list, now: datetime, preview: bool = False) -> list:
    svc, cal = tools_calendar._svc(), tools_calendar.CALENDAR_ID
    events = _list(updatedMin=(now - timedelta(hours=36)).isoformat(), singleEvents=True,
                   timeMin=(now - timedelta(days=1)).isoformat(), showDeleted=False)
    lines, sent = [], 0
    for e in events:
        private = (e.get("extendedProperties") or {}).get("private") or {}
        if TAG in private or "shula_snapshot" in private or SUMMARY in private or "shula_outreach_plan" in private or e.get("status") == "cancelled" or not e.get("start"):
            continue
        hit = _matches(e, items)
        stamp = ",".join(it["id"] for it in hit) + "@" + _when(e)
        if not hit or private.get(LOGGED) == stamp:
            continue
        if sent >= MAX_UPDATES:
            lines.append("עצרתי אחרי 20 עדכונים — השאר ייכנסו בסנכרון הבא.")
            break
        if preview:
            lines.append(f"- יירשם ב-monday על {', '.join(it['name'] for it in hit)}: {e.get('summary') or 'פגישה'} ({_when(e)})")
            continue
        word = "עודכנה" if private.get(LOGGED) else "נקבעה"
        body = f"📅 {word} ביומן של יוסי: <b>{e.get('summary') or 'פגישה'}</b>, {_when(e)}"
        if e.get("location"):
            body += f", {e['location']}"
        for it in hit:
            tools_monday._query("mutation ($item: ID!, $body: String!) { create_update(item_id: $item, body: $body) { id } }",
                                {"item": it["id"], "body": body}, "anycan")
            sent += 1
        svc.events().patch(calendarId=cal, eventId=e["id"],
                           body={"extendedProperties": {"private": {LOGGED: stamp}}}).execute()
        lines.append(f"נרשם ב-monday על {', '.join(it['name'] for it in hit)}: {e.get('summary') or 'פגישה'} ({_when(e)})")
    if preview:
        return [f"פגישות מהיומן שיירשמו ב-monday: {len(lines)}"] + lines
    return [f"מהיומן ל-monday: {sent} עדכונים נרשמו."] + lines


def sync_monday_and_calendar(preview: bool = False) -> str:
    """מסנכרנת עכשיו בין ה-monday של AnyCan ליומן גוגל של יוסי, בשני הכיוונים:
    תאריכים חשובים מהלוח AnyCan Ai נכנסים ליומן (וכל השאר — באירוע סיכום אחד ביום), ופגישות חדשות ביומן שקשורות לאדם או ארגון מהלוח נרשמות כעדכון על הפריט שלו.
    זה רץ לבד כל בוקר. השתמשי כשיוסי מבקש 'סנכרני מנדיי ויומן' או שואל מה סונכרן.
    preview=True = רק להראות מה ייכנס, בלי לכתוב כלום (כשיוסי מבקש 'תראי לי מה ייכנס' או 'בדיקה')."""
    if not _lock.acquire(blocking=False):
        return "סנכרון כבר רץ עכשיו — נסה שוב בעוד דקה."
    try:
        now = datetime.now(TZ)
        board, items = _board_items()
        return "\n".join(_monday_to_calendar(board, items, now, preview) + _calendar_to_monday(items, now, preview))
    finally:
        _lock.release()


MIRROR_LOG = re.compile(r"^🤖 \d{1,2}\.\d{1,2}\.\d{4}")
MIRROR_SEGMENTS = ("🩺 רופאים ומטפלים", "🤝 עמותות, מועדונים וקבוצות", "🏢 שותפים וחברות",
                   "❤️ אנשים עם פרקינסון ומשפחות", "📇 אנשי קשר נוספים")


def is_monday_mirror(e: dict) -> bool:
    """אירוע ביומן שנוצר אוטומטית מ-monday בגלל שורה ששולה עצמה פתחה — יומן הפעולות של Claude (🤖 תאריך ...)
    או איש קשר מסריקת aCare (... · 🩺 רופאים ומטפלים). בלי צבע ובלי סימון של שולה."""
    if e.get("colorId") or (e.get("extendedProperties") or {}).get("private"):
        return False
    title = (e.get("summary") or "").strip()
    return bool(MIRROR_LOG.match(title)) or any(title.endswith(" · " + s) for s in MIRROR_SEGMENTS)


def clean_monday_mirror(days: int = 3) -> str:
    """יוסי (16.11.2026): הלוגים לא אמורים להופיע ביומן. ב-monday יש חיבור שמעתיק כל שורה חדשה ליומן,
    ולכן שורות ששולה פותחת בעצמה (יומן הפעולות של Claude, אנשי קשר מסריקת aCare) הופיעו כאירועים.
    מוחקת רק אירועים כאלה, מ-days ימים אחורה עד days ימים קדימה. משימות ואירועים אמיתיים לא נוגעים."""
    now = datetime.now(TZ)
    svc, cal = tools_calendar._svc(), tools_calendar.CALENDAR_ID
    gone = 0
    for e in _list(timeMin=(now - timedelta(days=days)).isoformat(), timeMax=(now + timedelta(days=days)).isoformat(),
                   singleEvents=True, showDeleted=False):
        if is_monday_mirror(e):
            svc.events().delete(calendarId=cal, eventId=e["id"]).execute()
            gone += 1
    return f"נוקו מהיומן {gone} העתקות אוטומטיות מ-monday." if gone else ""


def _import_shares() -> None:
    try:
        import tools_posts
        for _ in range(20):  # עד 1,200 שיתופים חדשים בפעם אחת
            out = tools_posts.import_facebook_shares()
            log.info("facebook shares import: %s", out)
            if "נשארו" not in out:
                break
    except Exception:
        log.exception("facebook shares import failed")


def _claude_hour() -> int:
    import staff
    return staff.CLAUDE_LOG_HOUR


def daily_loop(check_every: int = 600) -> None:
    """הסנכרון עם היומן: פעם ביום, אחרי SYNC_HOUR בבוקר (שעון ישראל); ביום שבו שולה הופעלה מחדש אחרי השעה הזו — מחכה למחר.
    היומן של Claude: כל בוקר ב-06:00 → monday של AnyCan, לקבוצה של כל מחלקה.
    השיתופים והצפיות מפייסבוק: כל שעה (קריאת גיליון ועדכון monday, בלי AI) — כי Claude ממלא את הגיליון בשעה לא קבועה."""
    start = datetime.now(TZ)
    last = start.date() if start.hour >= SYNC_HOUR else None
    last_hour = None
    last_claude = None  # היומן של Claude → monday: כל בוקר ב-06:00 (גם אחרי הפעלה מחדש — הכפולים מסוננים)
    last_outreach = None  # סריקת aCare – למי לספר: פעם בשבוע ביום ראשון, ופעם אחת אחרי כל הפעלה (הכפולים מסוננים)
    while True:
        time.sleep(check_every)
        now = datetime.now(TZ)
        if now.hour >= SYNC_HOUR and last != now.date():
            last = now.date()
            try:
                log.info("daily monday sync: %s", sync_monday_and_calendar().replace("\n", " | "))
            except Exception:
                log.exception("daily monday sync failed")
        if now.hour >= _claude_hour() and last_claude != now.date():
            last_claude = now.date()
            try:
                import staff
                log.info("claude log → monday: %s", staff.import_claude_actions())
            except Exception:
                log.exception("claude log import failed")
            try:
                import tools_snapshot
                log.info("monday snapshot: %s", tools_snapshot.anycan_snapshot().replace("\n", " | "))
            except Exception:
                log.exception("monday snapshot failed")
        if 8 <= now.hour < 22 and (last_outreach is None or (now.weekday() == 6 and last_outreach != now.date())):
            last_outreach = now.date()
            try:
                import tools_outreach
                log.info("acare outreach scan: %s", tools_outreach.acare_outreach_scan().replace("\n", " | "))
            except Exception:
                log.exception("acare outreach scan failed")
        if last_hour != (now.date(), now.hour):
            last_hour = (now.date(), now.hour)
            try:
                out = clean_monday_mirror()
                if out:
                    log.info("monday mirror cleanup: %s", out)
            except Exception:
                log.exception("monday mirror cleanup failed")
            _import_shares()
            try:
                import tools_hub
                log.info("alpha omega two-way sync: %s", tools_hub.sync_content_hub())
            except Exception:
                log.exception("content hub sync failed")
            if now.hour >= 17:  # דו"ח המודיעין היומי מגיע ב-17:22 → תוכנית עבודה ב-monday
                try:
                    import staff
                    log.info("intel → monday: %s", staff.import_intel_actions().replace("\n", " | "))
                except Exception:
                    log.exception("intel import failed")


SYNC_TOOLS = [sync_monday_and_calendar]
