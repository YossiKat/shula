"""מעקב פוסטים ושיתופים ב-monday של AnyCan: קבוצה "פוסטים ושיתופים" בלוח AnyCan Ai,
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
    ("📅 Shared at", "date"), ("👥 Shared to", "text"), ("🔗 Post link", "text"),
]
# גיליון בדרייב של יוסי עם השיתופים שלו בפייסבוק (Claude ממלא אותו מיומן הפעילות): תאריך, שעה, פוסט, קבוצה, קישור, ממתין
SHARES_SHEET_ID = os.environ.get("FB_SHARES_SHEET_ID", "10pFuwwS7KQXY4-DIAYiIeqKq88pWESQ_e7PKMIi27fY")
IMPORT_BATCH = 60


def _board() -> dict:
    want = tools_monday.ANYCAN_DEFAULT_BOARD.lower()
    boards = tools_monday._anycan_boards()
    match = [b for b in boards if b["name"].strip().lower() == want] or [b for b in boards if want in b["name"].lower()]
    if not match:
        raise RuntimeError(f"לא מצאתי את הלוח '{tools_monday.ANYCAN_DEFAULT_BOARD}' ב-monday של AnyCan")
    data = tools_monday._query("query ($ids: [ID!]) { boards(ids: $ids) { id name columns { id title type } groups { id title } } }",
                               {"ids": [match[0]["id"]]}, "anycan")
    return data["boards"][0]


def setup_posts_tracking() -> str:
    """מכינה ב-monday של AnyCan (לוח AnyCan Ai) את המעקב אחרי פוסטים ושיתופים: קבוצה 'פוסטים ושיתופים' ועמודות
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
        return "הכול כבר קיים בלוח AnyCan Ai — לא נוצר שום דבר חדש."
    return "נוצרו בלוח AnyCan Ai: " + ", ".join(made)


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


def _sheet_rows() -> list[dict]:
    import google_auth
    raw = google_auth.service("drive", "v3", google_auth.MAIN).files().export(fileId=SHARES_SHEET_ID, mimeType="text/csv").execute()
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    out = []
    for r in list(csv.reader(io.StringIO(text)))[1:]:
        r = [c.strip() for c in (r + [""] * 6)[:6]]
        if r[0] and r[4]:
            out.append({"date": r[0], "time": r[1], "post": r[2], "group": r[3], "link": r[4], "pending": r[5].lower() in ("כן", "yes", "true", "1")})
    return out


PENDING = " (ממתין לאישור מנהל)"


def _existing_posts(board_id: str, group_id: str) -> dict:
    """{שם הפוסט: {"id": ..., "subs": שמות תת-השורות שכבר רשומות}} בקבוצת 'פוסטים ושיתופים'."""
    fields = "id name subitems { name }"
    q = "query ($b: [ID!], $g: [String!]) { boards(ids: $b) { groups(ids: $g) { items_page(limit: 100) { cursor items { %s } } } } }" % fields
    page = tools_monday._query(q, {"b": [board_id], "g": [group_id]}, "anycan")["boards"][0]["groups"][0]["items_page"]
    out = {}
    while True:
        for it in page["items"]:
            out[it["name"]] = {"id": it["id"], "subs": {sub["name"].replace(PENDING, "") for sub in it.get("subitems") or []}}
        if not page.get("cursor"):
            return out
        page = tools_monday._query("query ($c: String!) { next_items_page(cursor: $c, limit: 100) { cursor items { %s } } }" % fields,
                                   {"c": page["cursor"]}, "anycan")["next_items_page"]


def import_facebook_shares(limit: int = IMPORT_BATCH) -> str:
    """מכניסה ל-monday של AnyCan (קבוצת 'פוסטים ושיתופים') את השיתופים של יוסי לקבוצות פייסבוק מתוך הגיליון 'שיתופים בפייסבוק'
    שבדרייב: שורה אחת לכל פוסט, ומתחתיה תת-שורה לכל קבוצה שהפוסט שותף אליה. שיתוף שכבר רשום לא נרשם שוב.
    עד 60 שיתופים בכל פעם — אם נשארו, לבקש שוב. השתמשי כשיוסי מבקש 'תכניסי את השיתופים מפייסבוק למנדיי' או 'המשך ייבוא'.
    רץ לבד כל בוקר."""
    need = ["📅 shared at", "👥 shared to"]
    for attempt in range(2):
        board = _board()
        group = next((g for g in board["groups"] if g["title"].strip() == GROUP), None)
        cols = {c["title"].strip().lower(): c["id"] for c in board["columns"]}
        if group and all(n in cols for n in need):
            break
        if attempt == 0:
            setup_posts_tracking()  # יוצרת את מה שחסר (קבוצה או עמודות)
    else:
        return "לא הצלחתי להכין את הקבוצה והעמודות בלוח AnyCan Ai."
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
        try:
            last = max(r["date"] for r in mine)
            datetime.strptime(last, "%Y-%m-%d")
            values[cols["📅 shared at"]] = {"date": last}
        except ValueError:
            pass
        tools_monday._query(
            "mutation ($b: ID!, $i: ID!, $v: JSON!) { change_multiple_column_values(board_id: $b, item_id: $i, column_values: $v) { id } }",
            {"b": board["id"], "i": posts[post]["id"], "v": json.dumps(values, ensure_ascii=False)}, "anycan")
    return (f"נרשמו ב-monday {done} שיתופים מפייסבוק תחת {len(touched)} פוסטים (מתוך {len(rows)} שיתופים בגיליון)."
            + (f" נשארו עוד {left} — בקש 'המשך ייבוא'." if left else " הכול מעודכן."))


POSTS_TOOLS = [setup_posts_tracking, log_post_share, import_facebook_shares]
