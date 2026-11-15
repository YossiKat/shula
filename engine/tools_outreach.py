"""סריקת כל ה-monday של AnyCan: למי כדאי לספר על העבודה של יוסי באלפא אומגה ועל aCare Home.

יוסי (15.11.2026): "ששולה תעשה בדיקה בכל הרשומות של מנדיי anycan.ai ותראה איזה קשרים אפשר לעדכן
על ההתפתחויות שלי באלפא אומגה ולספר על aCare".
שולה עוברת על כל הלוחות, מוצאת אנשי קשר וארגונים שמתאימים (רופאים ומטפלים, עמותות ומועדונים, שותפים וחברות,
משפחות), ופותחת לכל אחד שורה בקבוצה "🤝 aCare – למי לספר" בלוח AnyCan Ai, עם הסיבה וטיוטת הודעה.
לא שולחת כלום לאף אחד — יוסי מחליט, ודימה מאשרת כל נוסח לפני שליחה. בלי טענות רפואיות.
לא נוגעת ב-monday של אלפא אומגה."""
import logging
import re
from datetime import datetime, timedelta

import tools_calendar
import tools_hub
import tools_monday

log = logging.getLogger("shula.outreach")
GROUP = "🤝 aCare – למי לספר"
MAX_NEW = 150
SKIP_BOARDS = ("budget", "inventory", "supermetrics", "social media schedule", "subitems")
SKIP_GROUP_WORDS = ("רייצ׳ל", "רות –", "ננסי", "ג׳סיקה", "ג׳ניפר", "automation issues", "todo", "aCare – למי לספר",
                    "פוסטים ושיתופים", "content hub")
PARKINSON = ("parkinson", "פרקינסון", "ppp", "pingpongparkinson", "movement disorder", "dbs")
SEGMENTS = [  # (מפתח, שם, מילים)
    ("clinic", "🩺 רופאים ומטפלים", ("נוירולוג", "neurolog", "רופא", "doctor", "dr.", "dr ", "ד\"ר", "ד״ר", "פיזיותרפ", "physio",
                                     "מרפאה", "clinic", "hospital", "בית חולים", "מרכז רפואי", "medical center", "אחות", "nurse",
                                     "ריפוי בעיסוק", "occupational", "קלינאי", "speech", "therap", "מטפל")),
    ("community", "🤝 עמותות, מועדונים וקבוצות", ("עמות", "association", "foundation", "קרן", "מועדון", "club", "support group",
                                                 "קבוצת תמיכה", "society", "federation", "איגוד", "ארגון", "organization", "ppp", "pingpong", "פינג")),
    ("partner", "🏢 שותפים וחברות", ("company", "חברת", "startup", "סטארט", "partner", "שותף", "investor", "משקיע", "ltd", "inc",
                                    "gmbh", "health tech", "healthtech", "digital health", "ventures", "בע\"מ", "בע״מ")),
    ("family", "❤️ אנשים עם פרקינסון ומשפחות", ("משפחה", "caregiver", "patient", "מטופל", "בן משפחה", "בת משפחה", "חולה")),
]
NAMES = {k: n for k, n, _ in SEGMENTS} | {"other": "📇 אנשי קשר נוספים"}


def _is_latin(text: str) -> bool:
    letters = re.findall(r"[A-Za-z֐-׿]", text)
    return bool(letters) and sum(c.isascii() for c in letters) > len(letters) / 2


def _draft(seg: str, name: str) -> str:
    first = (name.split() or [""])[0]
    if _is_latin(name):
        body = {
            "clinic": "I'd love to hear your professional view in a short call.",
            "community": "I'd be happy to come and present it to your members in a short meeting.",
            "partner": "I'd be glad to explore whether there is room to work together.",
        }.get(seg, "I'd be happy to tell you more.")
        return (f"Hi {first}, I hope you're well. I wanted to share an update: I now serve as Parkinson's advisor at "
                f"Alpha Omega, where we develop aCare Home — an app that accompanies people with Parkinson's and their "
                f"families in daily life. {body} Best, Yossi Kat")
    body = {
        "clinic": "אשמח לספר לך עוד בשיחה קצרה ולשמוע את דעתך המקצועית.",
        "community": "אשמח להגיע אליכם למפגש קצר ולהציג את האפליקציה לחברים.",
        "partner": "אשמח לבדוק איתך אם יש מקום לשיתוף פעולה.",
        "family": "אם זה יכול לעניין אותך או מישהו שאתה מכיר, אשמח לספר עוד.",
    }.get(seg, "אשמח לספר לך עוד.")
    return (f"שלום {first}, מה שלומך? רציתי לעדכן שאני משמש היום כיועץ פרקינסון באלפא אומגה. "
            f"אנחנו מפתחים את aCare Home – אפליקציה שמלווה אנשים עם פרקינסון ובני משפחה ביום-יום. {body} יוסי קט")


def classify(board: str, group: str, item: dict) -> dict | None:
    """מחזירה {seg, score, why, email, phone} לאיש קשר שכדאי לעדכן, או None."""
    cols = item.get("column_values") or []
    email = next((c.get("text") for c in cols if c.get("type") == "email" and c.get("text")), "")
    phone = next((c.get("text") for c in cols if c.get("type") == "phone" and c.get("text")), "")
    text = " ".join([item.get("name") or "", group, board] + [c.get("text") or "" for c in cols]).lower()
    if not email:
        m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
        email = m.group(0) if m else ""
    hits, seg, best = [], "other", 0
    for key, _, words in SEGMENTS:
        found = [w.strip() for w in words if w in text]
        if len(found) > best:
            seg, best = key, len(found)
        hits += found
    pk = [w for w in PARKINSON if w in text]
    score = best * 2 + len(pk) * 3 + (2 if email or phone else 0)
    if score < 4 or not (email or phone or best):
        return None
    why = []
    if pk:
        why.append("קשור לפרקינסון (" + ", ".join(sorted(set(pk))[:3]) + ")")
    if hits:
        why.append("מילים: " + ", ".join(sorted(set(hits))[:5]))
    if email or phone:
        why.append("יש פרטי קשר")
    return {"seg": seg, "score": score, "why": "; ".join(why), "email": email, "phone": phone}


def _all_items(board_id: str) -> list:
    cols = "id name group { title } column_values { type text column { title } }"
    data = tools_monday._query("query ($ids: [ID!]) { boards(ids: $ids) { items_page(limit: 500) { cursor items { %s } } } }" % cols,
                               {"ids": [board_id]}, "anycan")
    page = data["boards"][0]["items_page"]
    items = list(page["items"])
    while page.get("cursor") and len(items) < 3000:
        page = tools_monday._query("query ($c: String!) { next_items_page(cursor: $c, limit: 500) { cursor items { %s } } }" % cols,
                                   {"c": page["cursor"]}, "anycan")["next_items_page"]
        items += page["items"]
    return items


def acare_outreach_scan(preview: bool = False) -> str:
    """עוברת על כל הרשומות ב-monday של AnyCan ומוצאת אנשי קשר וארגונים שכדאי לעדכן על העבודה של יוסי באלפא אומגה
    ולספר להם על aCare Home (רופאים ומטפלים, עמותות ומועדונים, שותפים וחברות, משפחות).
    כל אחד נפתח כשורה בקבוצה '🤝 aCare – למי לספר' בלוח AnyCan Ai, עם הסיבה, מאיפה הוא, וטיוטת הודעה. מי שכבר שם — לא נפתח שוב.
    לא שולחת כלום: יוסי מחליט למי לשלוח, ודימה מאשרת את הנוסח. רץ לבד פעם בשבוע (יום ראשון).
    השתמשי כשיוסי מבקש 'למי לספר על aCare', 'תסרקי את המנדיי לאלפא אומגה'. preview=True = רק להראות, בלי לכתוב."""
    import staff
    boards = tools_monday._anycan_boards()
    found, seen = [], set()
    for b in boards:
        if any(w in b["name"].lower() for w in SKIP_BOARDS):
            continue
        try:
            items = _all_items(b["id"])
        except Exception:
            log.exception("outreach: board %s", b["name"])
            continue
        for it in items:
            group = (it.get("group") or {}).get("title") or ""
            if any(w.lower() in group.lower() for w in SKIP_GROUP_WORDS):
                continue
            c = classify(b["name"], group, it)
            if not c:
                continue
            key = (c["email"] or it["name"]).strip().lower()
            if key in seen:
                continue
            seen.add(key)
            found.append({**c, "name": it["name"].strip(), "board": b["name"], "bid": b["id"], "group": group, "id": it["id"]})
    found.sort(key=lambda x: -x["score"])
    counts = {}
    for f in found:
        counts[f["seg"]] = counts.get(f["seg"], 0) + 1
    head = f"מצאתי {len(found)} אנשי קשר שכדאי לעדכן על aCare: " + ", ".join(f"{NAMES[k]} {n}" for k, n in counts.items())
    if preview or not found:
        return head + ("\n" + "\n".join(f"- {f['name']} · {NAMES[f['seg']]} ({f['board']})" for f in found[:30]) if found else "")
    board = staff._board()
    gid = staff._group_id(board, GROUP)
    have = staff._names_in_group(board["id"], gid)
    made = []
    for f in found:
        if len(made) >= MAX_NEW:
            break
        title = f"{f['name']} · {NAMES[f['seg']]}"[:250]
        if title in have:
            continue
        item = tools_hub._create(board["id"], gid, title, {}, "anycan")
        have.add(title)
        body = (f"<b>למה:</b> {f['why']}<br><b>מאיפה:</b> לוח {f['board']}, קבוצה {f['group']} — "
                f"https://anycan-team.monday.com/boards/{f['bid']}/pulses/{f['id']}<br>"
                + (f"<b>מייל:</b> {f['email']}<br>" if f["email"] else "")
                + (f"<b>טלפון:</b> {f['phone']}<br>" if f["phone"] else "")
                + f"<br><b>טיוטת הודעה (לאישור דימה לפני שליחה, בלי טענות רפואיות):</b><br>{_draft(f['seg'], f['name'])}")
        tools_monday._query("mutation ($i: ID!, $b: String!) { create_update(item_id: $i, body: $b) { id } }",
                            {"i": item, "b": body[:3000]}, "anycan")
        made.append(f)
    _work_plan(found, made, counts)
    return head + f"\nנפתחו {len(made)} שורות חדשות בקבוצה '{GROUP}' בלוח AnyCan Ai." + ("" if made else " (כולם כבר היו שם)")


PRIORITY = ["clinic", "community", "partner", "family", "other"]
PER_WEEK = 10
PLAN_TAG = "shula_outreach_plan"


def work_plan(found: list) -> list:
    """תוכנית עבודה: הכי מתאימים קודם (רופאים ומטפלים, אחר כך עמותות, שותפים, משפחות), 10 פניות בשבוע.
    מחזירה את הרשימה עם 'week' לכל אחד."""
    order = sorted(found, key=lambda f: (PRIORITY.index(f["seg"]), -f["score"], not (f["email"] or f["phone"])))
    return [{**f, "week": i // PER_WEEK + 1} for i, f in enumerate(order)]


def _work_plan(found: list, made: list, counts: dict) -> None:
    """אירוע אחד ביומן עם כל תוכנית העבודה (מתעדכן באותו יום, לא אירוע לכל איש קשר)."""
    now = datetime.now(tools_calendar.TZ)
    plan = work_plan(found)
    weeks = {}
    for f in plan[:120]:
        how = "מייל" if f["email"] else ("טלפון" if f["phone"] else "אין פרטי קשר – לבדוק")
        weeks.setdefault(f["week"], []).append(f"• {f['name']} | {NAMES[f['seg']]} | {how} | {f['board']}")
    body = ("תוכנית עבודה – למי לספר על aCare ועל העבודה שלך באלפא אומגה.\n"
            f"שולה סרקה את כל ה-monday של AnyCan: {len(found)} אנשי קשר ({len(made)} חדשים היום).\n"
            + " · ".join(f"{NAMES[k]} {n}" for k, n in counts.items()) + "\n"
            "סדר: קודם רופאים ומטפלים, אחר כך עמותות ומועדונים, שותפים, משפחות. 10 פניות בשבוע.\n"
            "כל שורה בקבוצה '🤝 aCare – למי לספר' בלוח AnyCan Ai – עם טיוטת הודעה. לא נשלח כלום; כל נוסח לאישור דימה.\n")
    for w, lines in weeks.items():
        body += f"\nשבוע {w}:\n" + "\n".join(lines) + "\n"
    if len(plan) > 120:
        body += f"\nועוד {len(plan) - 120} – בקבוצה במנדיי."
    start = now.replace(second=0, microsecond=0)
    ev = {"summary": f"🤝 aCare – תוכנית עבודה: {len(found)} אנשי קשר, {PER_WEEK} בשבוע",
          "description": body[:8000], "colorId": tools_calendar.COLOR_IDS["monday"], "transparency": "transparent",
          "reminders": {"useDefault": False, "overrides": []},
          "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
          "end": {"dateTime": (start + timedelta(minutes=15)).isoformat(), "timeZone": "Asia/Jerusalem"},
          "extendedProperties": {"private": {PLAN_TAG: now.date().isoformat()}}}
    svc, cal = tools_calendar._svc(), tools_calendar.CALENDAR_ID
    old = svc.events().list(calendarId=cal, privateExtendedProperty=f"{PLAN_TAG}={now.date().isoformat()}",
                            maxResults=5).execute().get("items", [])
    if old:
        ev.pop("start"); ev.pop("end")
        svc.events().patch(calendarId=cal, eventId=old[0]["id"], body=ev).execute()
    else:
        svc.events().insert(calendarId=cal, body=ev).execute()


OUTREACH_TOOLS = [acare_outreach_scan]
