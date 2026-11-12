"""מעקב פוסטים ושיתופים ב-monday של AnyCan: קבוצה "פוסטים ושיתופים" בלוח AnyCan Ai,
עם אותן עמודות שיש בלוח של Alpha Omega (חשיפה, צפיות, תגובות, הצעד האורגני הבא) ועוד עמודת הורדות."""
import json
from datetime import datetime

import tools_calendar
import tools_monday

GROUP = "📣 פוסטים ושיתופים"
COLUMNS = [  # (כותרת, סוג)
    ("📊 Reach", "numbers"), ("👁️ Views", "numbers"), ("💬 Interactions", "numbers"), ("⬇️ Downloads", "numbers"),
    ("🌱 Next organic step", "text"), ("⏰ Organic step at", "date"),
]


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


POSTS_TOOLS = [setup_posts_tracking, log_post_share]
