"""תמונת מצב בוקר של ה-monday של AnyCan — בשביל ניתוח משולב של monday + יומן במטה של שולה.

יוסי (15.11.2026) רוצה מעקב וניתוח של הפעילות ב-monday ביחד עם היומן. את ה-monday של AnyCan רק שולה רואה
(עם המפתח שלה), ולכן כל בוקר אחרי 06:00 שולה סופרת מה קורה בלוחות של AnyCan ורושמת את זה ביומן "יוסי קט"
כאירוע אחד בשם "🔗 monday AnyCan – תמונת מצב". הדשבורד והמשימה האוטומטית של הניתוח קוראים משם.
קריאה בלבד מ-monday — לא משנה שום פריט."""
import json
import logging
from datetime import datetime, timedelta

import tools_calendar
import tools_monday

log = logging.getLogger("shula.snapshot")
BOARDS = ("AnyCan Ai", "Social media schedule", "Supermetrics Campaign Reporting")
TAG = "shula_snapshot"
TITLE = "🔗 monday AnyCan – תמונת מצב"
DONE = ("done", "בוצע", "הושלם", "פורסם", "published", "posted", "סגור", "completed")


def _items(board_id: str) -> list:
    cols = "id name created_at updated_at group { title } column_values { type text column { title } }"
    data = tools_monday._query("query ($ids: [ID!]) { boards(ids: $ids) { items_page(limit: 500) { cursor items { %s } } } }" % cols,
                               {"ids": [board_id]}, "anycan")
    page = data["boards"][0]["items_page"]
    items = list(page["items"])
    while page.get("cursor") and len(items) < 3000:
        page = tools_monday._query("query ($c: String!) { next_items_page(cursor: $c, limit: 500) { cursor items { %s } } }" % cols,
                                   {"c": page["cursor"]}, "anycan")["next_items_page"]
        items += page["items"]
    return items


def _when(s: str):
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def board_summary(name: str, items: list, now: datetime) -> dict:
    week = now - timedelta(days=7)
    groups = {}
    upcoming = []
    for it in items:
        g = (it.get("group") or {}).get("title") or "—"
        row = groups.setdefault(g, {"n": 0, "new7": 0, "upd7": 0, "done": 0})
        row["n"] += 1
        c, u = _when(it.get("created_at")), _when(it.get("updated_at"))
        if c and c >= week:
            row["new7"] += 1
        if u and u >= week:
            row["upd7"] += 1
        status = " ".join((cv.get("text") or "") for cv in it["column_values"] if cv.get("type") == "status").lower()
        if any(w in status for w in DONE):
            row["done"] += 1
        for cv in it["column_values"]:
            if cv.get("type") == "date" and cv.get("text"):
                d = cv["text"][:10]
                if now.date().isoformat() <= d <= (now + timedelta(days=7)).date().isoformat():
                    upcoming.append({"d": d, "t": it["name"][:80], "g": g[:40]})
                break
    total = {k: sum(r[k] for r in groups.values()) for k in ("n", "new7", "upd7", "done")}
    return {"board": name, **total, "groups": groups, "next7": sorted(upcoming, key=lambda x: x["d"])[:15]}


def anycan_snapshot() -> str:
    """סופרת מה קורה ב-monday של AnyCan (הלוחות AnyCan Ai, Social media schedule, Supermetrics Campaign Reporting):
    כמה פריטים יש בכל קבוצה, כמה חדשים ועודכנו השבוע, כמה בוצעו, ומה מתוכנן ל-7 הימים הקרובים —
    ורושמת את זה ביומן כאירוע '🔗 monday AnyCan – תמונת מצב' של היום. רץ לבד כל בוקר אחרי 06:00.
    השתמשי כשיוסי שואל 'מה קורה במנדיי' או מבקש ניתוח של המנדיי."""
    now = datetime.now(tools_calendar.TZ)
    have = {b["name"].strip().lower(): b for b in tools_monday._anycan_boards()}
    out, lines = [], []
    for name in BOARDS:
        b = have.get(name.lower())
        if not b:
            lines.append(f"• {name}: לא מצאתי את הלוח")
            continue
        s = board_summary(name, _items(b["id"]), now)
        out.append(s)
        lines.append(f"• {name}: {s['n']} פריטים · {s['new7']} חדשים השבוע · {s['upd7']} עודכנו השבוע · {s['done']} בוצעו"
                     + (f" · {len(s['next7'])} מתוכננים ל-7 ימים" if s["next7"] else ""))
    day = now.date().isoformat()
    desc = ("תמונת מצב של ה-monday של AnyCan (שולה, קריאה בלבד):\n" + "\n".join(lines)
            + "\n\n<<<SNAPSHOT\n" + json.dumps({"at": now.isoformat(timespec="minutes"), "boards": out}, ensure_ascii=False) + "\nSNAPSHOT>>>")
    svc, cal = tools_calendar._svc(), tools_calendar.CALENDAR_ID
    start = now.replace(hour=6, minute=5, second=0, microsecond=0)
    body = {"summary": TITLE, "description": desc[:60000], "colorId": "2", "transparency": "transparent",
            "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
            "end": {"dateTime": (start + timedelta(minutes=15)).isoformat(), "timeZone": "Asia/Jerusalem"},
            "reminders": {"useDefault": False, "overrides": []},
            "extendedProperties": {"private": {TAG: day}}}
    found = svc.events().list(calendarId=cal, privateExtendedProperty=f"{TAG}={day}", maxResults=5).execute().get("items", [])
    if found:
        svc.events().patch(calendarId=cal, eventId=found[0]["id"], body=body).execute()
    else:
        svc.events().insert(calendarId=cal, body=body).execute()
    return "תמונת המצב של monday נרשמה ביומן:\n" + "\n".join(lines)


SNAPSHOT_TOOLS = [anycan_snapshot]
