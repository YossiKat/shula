"""מעקב פוסטים ושיתופים ב-monday של AnyCan: קבוצה "פוסטים ושיתופים" בלוח Supermetrics Campaign Reporting,
עם אותן עמודות שיש בלוח של Alpha Omega (חשיפה, צפיות, תגובות, הצעד האורגני הבא) ועוד עמודת הורדות."""
import csv
import io
import json
import os
from datetime import datetime

import tools_calendar
import tools_monday

GROUP = "📣 פוסטים ושיתופים"
COLUMNS = [  # (כותרת, סוג)
    ("📊 Reach", "numbers"), ("👁️ Views", "numbers"), ("💬 Interactions", "numbers"), ("⬇️ Downloads", "numbers"),
    ("🌱 Next organic step", "text"), ("⏰ Organic step at", "date"),
    ("📅 Shared at", "date"), ("👥 Shared to", "text"), ("🔗 Post link", "text"), ("📈 Growth", "text"),
]
# גיליון בדרייב עם מדידה יומית של כל פוסט מקורי: תאריך בדיקה, פוסט, קישור למקורי, צפיות, לייקים, תגובות, שיתופים
ORIGINALS_SHEET_ID = os.environ.get("FB_ORIGINALS_SHEET_ID", "1tByY-jkAB6U2fOugigSqJfO32ToKtfTN-LAn0S-DDRY")
STAT_COLS = ["🔗 post link", "👁️ views", "💬 interactions", "📈 growth"]
# גיליון בדרייב של יוסי עם השיתופים שלו בפייסבוק (Claude ממלא אותו מיומן הפעילות): תאריך, שעה, פוסט, קבוצה, קישור, ממתין
SHARES_SHEET_ID = os.environ.get("FB_SHARES_SHEET_ID", "10pFuwwS7KQXY4-DIAYiIeqKq88pWESQ_e7PKMIi27fY")
IMPORT_BATCH = 60


# הלוח שבו מתנהל המעקב אחרי פוסטים ושיתופים (יוסי בחר: Supermetrics Campaign Reporting).
POSTS_BOARD = os.environ.get("MONDAY_POSTS_BOARD", "Supermetrics Campaign Reporting")
OLD_BOARD = tools_monday.ANYCAN_DEFAULT_BOARD  # כאן היה המעקב לפני כן — הפריטים עוברים משם


def _board(name: str = "") -> dict:
    name = name or POSTS_BOARD
    want = name.strip().lower()
    boards = tools_monday._anycan_boards()
    match = [b for b in boards if b["name"].strip().lower() == want] or [b for b in boards if want in b["name"].lower()]
    if not match:
        raise RuntimeError(f"לא מצאתי את הלוח '{name}' ב-monday של AnyCan")
    data = tools_monday._query("query ($ids: [ID!]) { boards(ids: $ids) { id name columns { id title type } groups { id title } } }",
                               {"ids": [match[0]["id"]]}, "anycan")
    return data["boards"][0]


_moved = False  # אחרי מעבר מוצלח אחד לא בודקים שוב עד ההפעלה הבאה


def move_posts_tracking() -> str:
    """מעבירה את קבוצת 'פוסטים ושיתופים' (כל הפוסטים, השורות הקטנות של הקבוצות והעמודות) מהלוח AnyCan Ai
    ללוח Supermetrics Campaign Reporting, ומעבירה לארכיון את הקבוצה הריקה שנשארה. מה שכבר עבר לא עובר שוב.
    רץ לבד לפני כל ייבוא; השתמשי גם כשיוסי מבקש 'תעבירי את המעקב פוסטים ל-Supermetrics'."""
    global _moved
    if _moved or OLD_BOARD.strip().lower() == POSTS_BOARD.strip().lower():
        return "המעקב כבר נמצא בלוח " + POSTS_BOARD + "."
    try:
        old = _board(OLD_BOARD)
    except RuntimeError:
        _moved = True
        return "המעקב כבר נמצא בלוח " + POSTS_BOARD + "."
    old_group = next((g for g in old["groups"] if g["title"].strip() == GROUP), None)
    if not old_group:
        _moved = True
        return "המעקב כבר נמצא בלוח " + POSTS_BOARD + "."
    setup_posts_tracking()  # קבוצה ועמודות בלוח החדש
    new = _board()
    new_group = next(g for g in new["groups"] if g["title"].strip() == GROUP)
    ids = []
    page = tools_monday._query(
        "query ($b: [ID!], $g: [String!]) { boards(ids: $b) { groups(ids: $g) { items_page(limit: 100) { cursor items { id } } } } }",
        {"b": [old["id"]], "g": [old_group["id"]]}, "anycan")["boards"][0]["groups"][0]["items_page"]
    while True:
        ids += [it["id"] for it in page["items"]]
        if not page.get("cursor"):
            break
        page = tools_monday._query("query ($c: String!) { next_items_page(cursor: $c, limit: 100) { cursor items { id } } }",
                                   {"c": page["cursor"]}, "anycan")["next_items_page"]
    for item_id in ids:
        # בלי מפת עמודות: monday מתאים לבד לפי שם וסוג (העמודות שלנו זהות בשני הלוחות).
        # מפה ידנית חייבת לכלול כל עמודה בלוח המקור, ועמודות נוסחה אי אפשר למפות — ולכן נכשלה.
        tools_monday._query(
            "mutation ($b: ID!, $g: ID!, $i: ID!) { move_item_to_board(board_id: $b, group_id: $g, item_id: $i) { id } }",
            {"b": new["id"], "g": new_group["id"], "i": item_id}, "anycan")
    tools_monday._query("mutation ($b: ID!, $g: String!) { archive_group(board_id: $b, group_id: $g) { id } }",
                        {"b": old["id"], "g": old_group["id"]}, "anycan")
    _moved = True
    return f"הועברו {len(ids)} פוסטים (עם כל השיתופים שלהם) מהלוח {OLD_BOARD} ללוח {POSTS_BOARD}. הקבוצה הריקה הועברה לארכיון."


def setup_posts_tracking() -> str:
    """מכינה ב-monday של AnyCan (לוח Supermetrics Campaign Reporting) את המעקב אחרי פוסטים ושיתופים: קבוצה 'פוסטים ושיתופים' ועמודות
    Reach, Views, Interactions, Downloads, Next organic step, Organic step at. מה שכבר קיים לא נוצר שוב.
    השתמשי פעם אחת, כשיוסי מבקש 'תכיני את המעקב אחרי פוסטים במנדיי'."""
    board = _board()
    have = {c["title"].strip().lower() for c in board["columns"]}
    made = []
    for title, kind in COLUMNS:
        if title.lower() in have:
            continue
        tools_monday._query("mutation ($b: ID!, $t: String!, $k: ColumnType!) { create_column(board_id: $b, title: $t, column_type: $k) { id } }",
                            {"b": board["id"], "t": title, "k": kind}, "anycan")
        made.append(title)
    if not any(g["title"].strip() == GROUP for g in board["groups"]):
        tools_monday._query("mutation ($b: ID!, $n: String!) { create_group(board_id: $b, group_name: $n) { id } }",
                            {"b": board["id"], "n": GROUP}, "anycan")
        made.append(f"הקבוצה {GROUP}")
    if not made:
        return f"הכול כבר קיים בלוח {board['name']} — לא נוצר שום דבר חדש."
    return f"נוצרו בלוח {board['name']}: " + ", ".join(made)


def log_post_share(title: str, platform: str = "", shared_to: str = "", link: str = "", next_step: str = "",
                   next_step_date: str = "") -> str:
    """רושמת ב-monday של AnyCan (קבוצת 'פוסטים ושיתופים') פוסט שיוסי פרסם או שיתוף שעשה.
    title = על מה הפוסט; platform = פייסבוק/אינסטגרם/טיקטוק/יוטיוב/לינקדאין; shared_to = לאן שותף (שם קבוצה או עמוד);
    link = קישור לפוסט; next_step = הצעד האורגני הבא; next_step_date = מתי (YYYY-MM-DD).
    השתמשי כשיוסי אומר 'שיתפתי את הפוסט על... בקבוצה...' או 'תרשמי פוסט'."""
    title = (title or "").strip()
    if not title:
        return "לא נרשם — חסר על מה הפוסט."
    board = _board()
    group = next((g for g in board["groups"] if g["title"].strip() == GROUP), None)
    if not group:
        return "המעקב עדיין לא הוכן בלוח. בקש ממני 'תכיני את המעקב אחרי פוסטים במנדיי'."
    cols = {c["title"].strip().lower(): c["id"] for c in board["columns"]}
    values = {}
    if next_step and "🌱 next organic step" in cols:
        values[cols["🌱 next organic step"]] = next_step[:250]
    if next_step_date and "⏰ organic step at" in cols:
        datetime.strptime(next_step_date, "%Y-%m-%d")
        values[cols["⏰ organic step at"]] = {"date": next_step_date}
    name = " · ".join(p for p in (platform.strip(), title, f"שותף ל: {shared_to.strip()}" if shared_to.strip() else "") if p)[:250]
    item = tools_monday._query(
        "mutation ($b: ID!, $g: String!, $n: String!, $v: JSON) { create_item(board_id: $b, group_id: $g, item_name: $n, column_values: $v) { id } }",
        {"b": board["id"], "g": group["id"], "n": name, "v": json.dumps(values, ensure_ascii=False)}, "anycan")["create_item"]
    when = datetime.now(tools_calendar.TZ).strftime("%d.%m.%Y %H:%M")
    body = f"נרשם ע\"י שולה ב-{when}." + (f"<br>קישור: {link.strip()}" if link.strip() else "")
    tools_monday._query("mutation ($item: ID!, $body: String!) { create_update(item_id: $item, body: $body) { id } }",
                        {"item": item["id"], "body": body}, "anycan")
    return f"נרשם ב-monday (פוסטים ושיתופים): {name}"


def _csv(sheet_id: str) -> list[list[str]]:
    import google_auth
    raw = google_auth.service("drive", "v3", google_auth.MAIN).files().export(fileId=sheet_id, mimeType="text/csv").execute()
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    return list(csv.reader(io.StringIO(text)))[1:]


def _num(v: str):
    v = (v or "").replace(",", "").strip()
    return int(float(v)) if v.replace(".", "", 1).isdigit() else None


def _original_stats() -> dict:
    """{שם הפוסט: {"link", "first": מדידה ראשונה, "last": מדידה אחרונה}} מתוך גיליון המדידות היומיות."""
    out = {}
    rows = [[c.strip() for c in (r + [""] * 7)[:7]] for r in _csv(ORIGINALS_SHEET_ID)]
    for r in sorted((r for r in rows if r[0] and r[1]), key=lambda r: r[0]):
        m = {"date": r[0], "views": _num(r[3]), "likes": _num(r[4]) or 0, "comments": _num(r[5]) or 0, "shares": _num(r[6]) or 0}
        post = out.setdefault(r[1], {"link": r[2], "first": m})
        post["last"] = m
        post["link"] = r[2] or post["link"]
    return out


def _stat_values(st: dict) -> dict:
    """מה לכתוב על שורת הפוסט: קישור למקורי, צפיות, תגובות, ועלייה באחוזים מאז המדידה הראשונה."""
    first, last = st["first"], st["last"]
    day = lambda d: f"{d[8:10]}.{d[5:7]}"
    if last["views"] is None:
        growth = "אין ספירת צפיות לפוסט הזה (לא ריל)"
    elif first["date"] == last["date"] or not first["views"]:
        growth = f"נמדד לראשונה ב-{day(last['date'])}: {last['views']} צפיות"
    else:
        pct = round((last["views"] - first["views"]) * 100 / first["views"])
        growth = f"{'+' if pct >= 0 else ''}{pct}% ({first['views']} ב-{day(first['date'])} → {last['views']} ב-{day(last['date'])})"
    return {"🔗 post link": st["link"], "👁️ views": "" if last["views"] is None else str(last["views"]),
            "💬 interactions": str(last["likes"] + last["comments"] + last["shares"]), "📈 growth": growth}


def _local(r: dict):
    """שעת השיתוף (שעון ישראל) מתוך שורת הגיליון, או None אם התאריך או השעה לא תקינים."""
    import tools_calendar
    try:
        return datetime.strptime(f"{r['date']} {r['time'].zfill(5)}", "%Y-%m-%d %H:%M").replace(tzinfo=tools_calendar.TZ)
    except (ValueError, KeyError):
        return None


def _monday_datetime(r: dict):
    """עמודת תאריך ב-monday עם שעה (monday שומר את השעה ב-UTC ומציג אותה בשעון של יוסי)."""
    from zoneinfo import ZoneInfo
    when = _local(r)
    if when is None:
        try:
            datetime.strptime(r.get("date", ""), "%Y-%m-%d")
            return {"date": r["date"]}
        except ValueError:
            return None
    utc = when.astimezone(ZoneInfo("UTC"))
    return {"date": utc.strftime("%Y-%m-%d"), "time": utc.strftime("%H:%M:%S")}


SESSION_GAP = 30  # דקות: שיתופים של אותו פוסט בהפרש קטן מזה = אירוע אחד ביומן
CAL_TAG = "shula_fbshare"


def _share_sessions(rows: list[dict]) -> dict:
    """{מפתח: אירוע יומן} — אירוע אחד לכל פוסט לכל 'סבב שיתופים' (שיתופים ברצף), בשעה שבה שיתפת."""
    import tools_calendar
    from datetime import timedelta
    by_post = {}
    for r in rows:
        when = _local(r)
        if when:
            by_post.setdefault(r["post"] or "פוסט", []).append((when, r))
    out = {}
    for post, items in by_post.items():
        items.sort(key=lambda x: x[0])
        sessions = []
        for when, r in items:
            if sessions and (when - sessions[-1][-1][0]).total_seconds() <= SESSION_GAP * 60:
                sessions[-1].append((when, r))
            else:
                sessions.append([(when, r)])
        for ses in sessions:
            start, end = ses[0][0], max(ses[-1][0], ses[0][0] + timedelta(minutes=15))
            groups = len({r["group"] for _, r in ses})
            waiting = sum(r["pending"] for _, r in ses)
            key = f"{post[:40]}|{start.strftime('%Y-%m-%d %H:%M')}"
            lines = [f"{w.strftime('%H:%M')} · {r['group']}" + (" (ממתין לאישור מנהל)" if r["pending"] else "") for w, r in ses]
            out[key] = {
                "summary": f"📤 שיתפתי: {post[:60]} → {groups} קבוצות",
                "description": (f"שיתופים לקבוצות פייסבוק ({len(ses)}" + (f", {waiting} ממתינים לאישור" if waiting else "") + "):\n"
                                + "\n".join(lines) + "\n\nמתוך המעקב במנדיי של AnyCan (פוסטים ושיתופים)."),
                "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
                "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Jerusalem"},
                "colorId": tools_calendar.COLOR_IDS["monday"],
                "transparency": "transparent",
                "extendedProperties": {"private": {CAL_TAG: key, f"{CAL_TAG}_on": "1"}},
            }
    return out


def shares_to_calendar(rows: list[dict]) -> str:
    """כל סבב שיתופים מופיע ביומן 'יוסי קט' בשעה שבה שיתפת, בירוק בהיר. לא מוחק אירועים ולא נוגע באירועים אחרים."""
    import tools_calendar
    svc, cal = tools_calendar._svc(), tools_calendar.CALENDAR_ID
    wanted = _share_sessions(rows)
    existing, token = {}, None
    while True:
        res = svc.events().list(calendarId=cal, privateExtendedProperty=f"{CAL_TAG}_on=1", pageToken=token,
                                maxResults=250, showDeleted=False).execute()
        for e in res.get("items", []):
            existing[e["extendedProperties"]["private"][CAL_TAG]] = e
        token = res.get("nextPageToken")
        if not token:
            break
    added = changed = 0
    for key, ev in wanted.items():
        old = existing.get(key)
        if old is None:
            svc.events().insert(calendarId=cal, body=ev).execute()
            added += 1
        elif (old.get("summary"), old.get("description"), (old.get("end") or {}).get("dateTime", "")[:16], old.get("colorId")) != \
                (ev["summary"], ev["description"], ev["end"]["dateTime"][:16], ev["colorId"]):
            svc.events().patch(calendarId=cal, eventId=old["id"], body=ev).execute()
            changed += 1
    return f"ביומן: {added} סבבי שיתוף חדשים, {changed} עודכנו." if added or changed else ""


def _sheet_rows() -> list[dict]:
    out = []
    for r in _csv(SHARES_SHEET_ID):
        r = [c.strip() for c in (r + [""] * 6)[:6]]
        if r[0] and r[4]:
            out.append({"date": r[0], "time": r[1], "post": r[2], "group": r[3], "link": r[4], "pending": r[5].lower() in ("כן", "yes", "true", "1")})
    return out


PENDING = " (ממתין לאישור מנהל)"


def _existing_posts(board_id: str, group_id: str) -> dict:
    """{שם הפוסט: {"id": ..., "subs": שמות תת-השורות שכבר רשומות}} בקבוצת 'פוסטים ושיתופים'."""
    fields = "id name subitems { name } column_values { column { title } text }"
    q = "query ($b: [ID!], $g: [String!]) { boards(ids: $b) { groups(ids: $g) { items_page(limit: 100) { cursor items { %s } } } } }" % fields
    page = tools_monday._query(q, {"b": [board_id], "g": [group_id]}, "anycan")["boards"][0]["groups"][0]["items_page"]
    out = {}
    while True:
        for it in page["items"]:
            out[it["name"]] = {"id": it["id"], "subs": {sub["name"].replace(PENDING, "") for sub in it.get("subitems") or []},
                               "cols": {c["column"]["title"].strip().lower(): (c.get("text") or "") for c in it.get("column_values") or []}}
        if not page.get("cursor"):
            return out
        page = tools_monday._query("query ($c: String!) { next_items_page(cursor: $c, limit: 100) { cursor items { %s } } }" % fields,
                                   {"c": page["cursor"]}, "anycan")["next_items_page"]


def import_facebook_shares(limit: int = IMPORT_BATCH) -> str:
    """מכניסה ל-monday של AnyCan (קבוצת 'פוסטים ושיתופים') את השיתופים של יוסי לקבוצות פייסבוק מתוך הגיליון 'שיתופים בפייסבוק'
    שבדרייב: שורה אחת לכל פוסט, ומתחתיה תת-שורה לכל קבוצה שהפוסט שותף אליה. שיתוף שכבר רשום לא נרשם שוב.
    כל סבב שיתופים מופיע גם ביומן 'יוסי קט' בשעה שבה שיתפת, בירוק בהיר.
    על שורת הפוסט נרשמים גם שעת השיתוף האחרון, הקישור לפוסט המקורי, כמות הצפיות, ועלייה באחוזים מאז המדידה הראשונה (מגיליון המדידות היומי).
    עד 60 שיתופים בכל פעם — אם נשארו, לבקש שוב. השתמשי כשיוסי מבקש 'תכניסי את השיתופים מפייסבוק למנדיי', 'המשך ייבוא'
    או 'תעדכני צפיות'. רץ לבד כל שעה."""
    moved = ""
    try:
        out = move_posts_tracking()
        moved = "" if out.startswith("המעקב כבר") else out + " "
    except Exception as e:  # המעבר לא יעצור את הייבוא
        moved = f"(המעבר ללוח {POSTS_BOARD} לא הצליח: {str(e)[:120]}) "
    need = ["📅 shared at", "👥 shared to"] + STAT_COLS
    for attempt in range(2):
        board = _board()
        group = next((g for g in board["groups"] if g["title"].strip() == GROUP), None)
        cols = {c["title"].strip().lower(): c["id"] for c in board["columns"]}
        if group and all(n in cols for n in need):
            break
        if attempt == 0:
            setup_posts_tracking()  # יוצרת את מה שחסר (קבוצה או עמודות)
    else:
        return f"לא הצלחתי להכין את הקבוצה והעמודות בלוח {POSTS_BOARD}."
    rows = _sheet_rows()
    posts = _existing_posts(board["id"], group["id"])
    budget = max(1, min(int(limit), 200))
    done = left = 0
    touched = set()
    for r in reversed(rows):  # מהישן לחדש
        post = f"פייסבוק · {r['post'] or 'פוסט'}"[:250]
        sub = f"{r['date']} {r['time']} · {r['group']}"[:230]
        if post in posts and sub in posts[post]["subs"]:
            continue
        if done >= budget:
            left += 1
            continue
        if post not in posts:
            item = tools_monday._query(
                "mutation ($b: ID!, $g: String!, $n: String!) { create_item(board_id: $b, group_id: $g, item_name: $n) { id } }",
                {"b": board["id"], "g": group["id"], "n": post}, "anycan")["create_item"]
            posts[post] = {"id": item["id"], "subs": set()}
        tools_monday._query(
            "mutation ($p: ID!, $n: String!) { create_subitem(parent_item_id: $p, item_name: $n) { id } }",
            {"p": posts[post]["id"], "n": sub + (PENDING if r["pending"] else "")}, "anycan")
        posts[post]["subs"].add(sub)
        touched.add(post)
        done += 1
    for post in touched:  # סיכום על שורת הפוסט: כמה קבוצות, כמה ממתינים, מתי שותף לאחרונה
        mine = [r for r in rows if f"פייסבוק · {r['post'] or 'פוסט'}"[:250] == post]
        waiting = sum(r["pending"] for r in mine)
        values = {cols["👥 shared to"]: f"{len(mine)} שיתופים ל-{len({r['group'] for r in mine})} קבוצות"
                                        + (f", {waiting} ממתינים לאישור" if waiting else "")}
        last = _monday_datetime(max((r for r in mine), key=lambda r: (r["date"], r["time"].zfill(5))))
        if last:
            values[cols["📅 shared at"]] = last
        tools_monday._query(
            "mutation ($b: ID!, $i: ID!, $v: JSON!) { change_multiple_column_values(board_id: $b, item_id: $i, column_values: $v) { id } }",
            {"b": board["id"], "i": posts[post]["id"], "v": json.dumps(values, ensure_ascii=False)}, "anycan")
    updated = 0
    if all(n in cols for n in STAT_COLS):  # צפיות, קישור למקורי ועלייה באחוזים — רק כשמשהו השתנה
        for title, st in _original_stats().items():
            post = posts.get(f"פייסבוק · {title}"[:250])
            if not post:
                continue
            want = _stat_values(st)
            if all(post.get("cols", {}).get(k, "") == v for k, v in want.items()):
                continue
            tools_monday._query(
                "mutation ($b: ID!, $i: ID!, $v: JSON!) { change_multiple_column_values(board_id: $b, item_id: $i, column_values: $v) { id } }",
                {"b": board["id"], "i": post["id"], "v": json.dumps({cols[k]: v for k, v in want.items()}, ensure_ascii=False)}, "anycan")
            updated += 1
    stats = f" עודכנו צפיות ועלייה ב-{updated} פוסטים." if updated else ""
    try:
        cal = shares_to_calendar(rows)
        stats += f" {cal}" if cal else ""
    except Exception as e:  # היומן לא יעצור את המנדיי
        stats += f" (היומן לא עודכן: {str(e)[:120]})"
    return moved + (f"נרשמו ב-monday {done} שיתופים מפייסבוק תחת {len(touched)} פוסטים (מתוך {len(rows)} שיתופים בגיליון)."
            + (f" נשארו עוד {left} — בקש 'המשך ייבוא'." if left else " הכול מעודכן.") + stats)


POSTS_TOOLS = [setup_posts_tracking, log_post_share, import_facebook_shares, move_posts_tracking]
