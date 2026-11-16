"""המטה של שולה: שולה היא ראש המטה, ומאחוריה 7 מחלקות — לכל אחת שם, תפקיד וקבוצה משלה
בלוח AnyCan Ai ב-monday של AnyCan.

יוסי מדבר רק עם שולה. לכל הודעה שולה מזהה איזו מחלקה מטפלת בה (route), מקבלת את "תיאור התפקיד"
של המחלקה, ובסוף רושמת את מה שנעשה בקבוצה של המחלקה ב-monday (log_to_department).
קבוצה שעוד לא קיימת בלוח נפתחת לבד בפעם הראשונה."""
import tools_hub
import tools_monday

BOARD_NAME = tools_monday.ANYCAN_DEFAULT_BOARD  # AnyCan Ai

# key: (שם, אמוג'י, תחום, קבוצה ב-monday, מילות מפתח, תיאור תפקיד)
DEPARTMENTS = {
    "cfo": {
        "name": "יונתן", "emoji": "💰", "title": "הנהלת חשבונות ותזרים",
        "group": "💰 יונתן – כספים", "reports_to": "finance",
        "words": ("הכנסה", "חשבונית", "דרישת תשלום", "קבלה", "שכר", "ייעוץ", "דוח נסיעה", "מי חייב", "חוב", "לקוח שילם", "שולם",
                  "תזרים", "נכנס", "יצא", "יתרה", "הנהלת חשבונות", "רואה חשבון"),
        "job": "יונתן הוא מנהל החשבונות: יודע כל שקל שיוצא וכל שקל שנכנס, ומנהל את התזרים. "
               "הכנסות (ייעוץ לאלפא אומגה, AnyCan, שיעורי אופניים ורולרבליידס), דרישות תשלום, מי חייב כסף, דוחות נסיעה. "
               "מקבל עדכונים מננסי על כל הוצאה ותשלום, ומעדכן את רות. הכנסה נרשמת ביומן בירוק בהיר עם הסכום.",
    },
    "finance": {
        "name": "רות", "emoji": "📊", "title": "CFO – תכנון ובקרה פיננסית",
        "group": "📊 רות – ניהול פיננסי",
        "words": ("חיסכון", "חסכון", "ביטוח", "פוליסה", "הראל", "השקעה", "פנסיה", "קרן", "בנק", "משכנתא", "דוח חודשי",
                  "תכנון פיננסי", "תקציב שנתי", "בקרה", "מאזן", "רווח"),
        "job": "רות היא ה-CFO: רואה מלמעלה את החשבון, ההוצאות וכל הניהול הפיננסי, אחראית על התכנון הפיננסי ומבקרת. "
               "מקבלת עדכונים מיונתן. חיסכונות, ביטוחים ופוליסות, השקעות ויעדים שנתיים. "
               "אף פעם לא ממליצה על קנייה או מכירה של מניות או השקעות — רק מסדרת מידע, מבקרת ומזכירה.",
    },
    "home": {
        "name": "ננסי", "emoji": "🏠", "title": "כלכלת בית, תשלומים ואוכל",
        "group": "🏠 ננסי – כלכלת בית", "reports_to": "cfo",
        "words": ("הוצאה", "קניתי", "שילמתי", "סופר", "קניות", "חשבון חשמל", "ארנונה", "מים", "גז", "סייל", "משלוח", "חבילה", "תקציב",
                  "אוכל", "וולט", "wolt", "הזמנת אוכל", "מכולת", "תשלום"),
        "job": "ננסי אחראית על כלכלת הבית: הוצאות שוטפות (נרשמות ביומן בכתום, 15 דקות, '💸 הוצאה X₪ – ...'), "
               "תשלומים וחשבונות, הזמנות אוכל, קניות, סיילים ומשלוחים, ותקציב הבית. כל הוצאה ותשלום עוברים כעדכון ליונתן.",
    },
    "cmo": {
        "name": "ג׳סיקה", "emoji": "📣", "title": "שיווק ומחקר שיווקי",
        "group": "📣 ג׳סיקה – שיווק",
        "words": ("פוסט", "רילס", "סרטון", "שיווק", "פייסבוק", "אינסטגרם", "טיקטוק", "לינקדאין", "יוטיוב", "קמפיין", "צפיות", "שיתוף", "קהל",
                  "רעיון שיווקי", "מחקר שוק", "מתחרים", "הודעה לעיתונות", "עיתונאי"),
        "job": "ג׳סיקה כל היום חושבת איך להביא עוד רעיונות שיווקיים, ועושה מחקרים שיווקיים כל הזמן: מתחרים, קהלים ומה עובד. "
               "אחראית על השיווק של אלפא אומגה ושל AnyCan: פוסטים, סרטונים, שיתופים בקבוצות, קמפיינים ומדידת צפיות. "
               "כל תוכן של אלפא אומגה עובר לאישור דימה לפני פרסום, ובלי הבטחות רפואיות.",
    },
    "cto": {
        "name": "אמילי", "emoji": "🧠", "title": "טכנולוגיה, פיתוח וחידושים",
        "group": "🔧 Automation Issues",
        "words": ("רעיון", "מערכת", "אוטומציה", "אפליקציה", "באג", "תקלה", "קוד", "בוט", "חיבור", "אתר", "טכנולוגיה", "בינה מלאכותית",
                  "מפתח", "מפתחים", "פיתוח", "חידוש", "גרסה", "כלי חדש"),
        "job": "אמילי עובדת מול המפתחים, ומחפשת כל הזמן חידושים טכנולוגיים: כלים חדשים, מערכות ואוטומציות, "
               "תקלות בשולה, ומערכת התחרויות של יוסי ושחר (מיזם פרטי, לא של אלפא אומגה).",
    },
    "admin": {
        "name": "סוזן", "emoji": "🗂️", "title": "הזמנות, מנויים ובקרת משימות",
        "group": "ToDo",
        "words": ("יומן", "פגישה", "לקבוע", "תזכורת", "משימה", "מייל", "טיוטה", "מסמך", "טופס", "נסיעה", "טיסה", "בוצע",
                  "להזמין מקום", "הזמנת מקום", "שולחן", "מסעדה", "כרטיסים", "מנוי", "מנויים", "חידוש מנוי", "כפילות", "כפול"),
        "job": "סוזן אחראית על הזמנת מקומות (מסעדות, כרטיסים, אירועים), תשלומים למנויים, "
               "ולוודא שמשימות בוצעו ושאין כפילויות (ביומן, במנויים ובתשלומים). גם יומן, פגישות, תזכורות ומסמכים. "
               "משימה שבוצעה נרשמת ביומן בתכלת עם '✅ בוצע:'.",
    },
    "personal": {
        "name": "ג׳ניפר", "emoji": "❤️", "title": "מאמנת כושר ותזונה",
        "group": "❤️ ג׳ניפר – אישי ויחסים",
        "words": ("כושר", "חדר כושר", "אימון", "רולר", "ריצה", "הליכה", "צעדים", "תזונה", "אכלתי", "ארוחה", "משקל", "שינה",
                  "בריאות", "וולנס", "טיפוח", "ספא", "יום הולדת", "מתנה", "חופשה"),
        "job": "ג׳ניפר היא המאמנת כושר של יוסי: מוודאה ובודקת את התזונה ואת הפעילות שלו (חדר כושר, ושיעור אופניים = 45 דקות ו-4 ק״מ רולר בליידס), "
               "ונותנת המלצות. בלי מספרים קיצוניים ובלי דיאטות חריפות. גם חברים ומשפחה, ימי הולדת ובילויים. "
               "שומרת על פרטיות — מה שיוסי מספר על אנשים אחרים נשאר ביניהם.",
    },
}


def route(message: str) -> str | None:
    """איזו מחלקה מטפלת בהודעה — לפי מילות המפתח. None = שולה בעצמה."""
    m = (message or "").lower()
    scores = {k: sum(1 for w in d["words"] if w in m) for k, d in DEPARTMENTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else None


def roster_text() -> str:
    """רשימת הצוות לחלק הקבוע של ההוראות."""
    lines = [f"- {d['emoji']} {d['name']} – {d['title']}: {d['job']}" for d in DEPARTMENTS.values()]
    return (
        "את שולה, ראש המטה של יוסי (הוא המייסד וה-CEO). את אחראית על הכל מלמעלה, ומעודכנת בעיקר ולא בטפל: "
        "ליוסי מספרים רק מה שחשוב ודורש החלטה. יוסי מדבר רק איתך, ומאחורייך עובדות 7 מחלקות:\n"
        + "\n".join(lines)
        + "\nאת המפקחת: הכל עובר דרכך. כל יום ב-17:22 מגיע ליוסי במייל 'דו\"ח מודיעין יומי' (מחקר, מתחרים, טכנולוגיה ותרופות בפרקינסון), "
        "וב-18:53 הפעולות שבו נרשמות ביומן כמשימות של המחלקות (למשל '📣 ג׳סיקה: ...'). כשיוסי שואל מה חדש במודיעין – קראי את הדוח האחרון "
        "עם כלי המייל וספרי לו רק את העיקר; ובדקי שהמשימות של הדוח נרשמו ולא נשכחו."
        + "\nבכל בקשה: תפקדי לפי המחלקה שמטפלת בה (כתוב למטה), ובסוף פעולה שבוצעה — רשמי אותה בקבוצה של המחלקה "
        "ב-monday עם log_to_department. בתשובה אפשר להזכיר בקצרה מי מהצוות טיפל (למשל 'ננסי רשמה את ההוצאה')."
    )


def focus_text(message: str) -> str:
    """החלק המשתנה: מי מטפלת בהודעה הזאת."""
    key = route(message)
    if not key:
        return ""
    d = DEPARTMENTS[key]
    return f"המחלקה שמטפלת בהודעה הזאת: {d['emoji']} {d['name']} ({d['title']}, department='{key}').\n"


def _board() -> dict:
    boards = tools_monday._anycan_boards()
    match = [b for b in boards if b["name"].strip().lower() == BOARD_NAME.lower()]
    if not match:
        raise RuntimeError(f"לא מצאתי את הלוח {BOARD_NAME} ב-monday של AnyCan")
    data = tools_monday._query("query ($ids: [ID!]) { boards(ids: $ids) { id groups { id title } } }",
                               {"ids": [match[0]["id"]]}, "anycan")
    return data["boards"][0]


# השמות הקודמים של בעלי התפקידים (מוני→רייצ׳ל בנובמבר 2026, רייצ׳ל→יונתן ב-16.11.2026). קבוצה ב-monday עם השם הישן מקבלת את השם החדש.
OLD_NAMES = {'יונתן': ('רייצ׳ל', 'מוני'), 'רות': ('חסיה',), 'ננסי': ('בתיה',), 'ג׳סיקה': ('שירי',), 'אמילי': ('רעיה',), 'סוזן': ('סדרית',), 'ג׳ניפר': ('לבנה',)}


def _old_titles(title: str) -> list:
    """כל השמות הקודמים של קבוצה (16.11.2026: יונתן → יונתן; לפני כן מוני → יונתן)."""
    out = []
    for new, olds in OLD_NAMES.items():
        if new in title:
            out += [title.replace(new, old) for old in olds]
    return out


def _old_title(title: str) -> str:
    olds = _old_titles(title)
    return olds[0] if olds else title


def _group_id(board: dict, title: str) -> str:
    for g in board.get("groups") or []:
        if g["title"].strip() == title:
            return g["id"]
    olds = _old_titles(title)
    for g in board.get("groups") or []:
        if g["title"].strip() in olds:
            tools_monday._query("mutation ($b: ID!, $g: String!, $v: String!) { update_group(board_id: $b, group_id: $g, "
                                "group_attribute: title, new_value: $v) { id } }",
                                {"b": board["id"], "g": g["id"], "v": title}, "anycan")
            g["title"] = title
            return g["id"]
    return tools_monday._query("mutation ($b: ID!, $t: String!) { create_group(board_id: $b, group_name: $t) { id } }",
                               {"b": board["id"], "t": title}, "anycan")["create_group"]["id"]


def log_to_department(department: str, title: str, details: str = "") -> str:
    """רושמת פעולה שבוצעה כשורה חדשה בקבוצה של המחלקה בלוח AnyCan Ai ב-monday של AnyCan.
    department = cfo (יונתן, כספים) | finance (רות, ניהול פיננסי) | home (ננסי, כלכלת בית) | cmo (ג׳סיקה, שיווק) | cto (אמילי, טכנולוגיה ורעיונות) | admin (סוזן, אדמיניסטרציה) | personal (ג׳ניפר, אישי ויחסים)
    title = שם קצר לשורה, למשל 'הוצאה 21₪ – בית הלחם'
    details = פרטים נוספים (נכתבים כעדכון על השורה)"""
    d = DEPARTMENTS.get((department or "").strip().lower())
    if not d:
        return "מחלקה לא מוכרת. האפשרויות: " + ", ".join(DEPARTMENTS)
    board = _board()
    gid = _group_id(board, d["group"])
    item = tools_hub._create(board["id"], gid, (title or "").strip() or "פעולה", {}, "anycan")
    if details.strip():
        tools_monday._query("mutation ($i: ID!, $b: String!) { create_update(item_id: $i, body: $b) { id } }",
                            {"i": item, "b": details.strip()[:2000]}, "anycan")
    up = DEPARTMENTS.get(d.get("reports_to") or "")
    if up:  # ננסי מעדכנת את יונתן, יונתן מעדכן את רות
        tools_hub._create(board["id"], _group_id(board, up["group"]), f"↗️ עדכון מ{d['name']}: {(title or '').strip()}"[:250], {}, "anycan")
        return f"נרשם ב-monday אצל {d['name']} ({d['title']}), ועדכון עבר ל{up['name']}."
    return f"נרשם ב-monday אצל {d['name']} ({d['title']}), בקבוצה '{d['group']}'."


STAFF_TOOLS = [log_to_department]


# ---- דו"ח המודיעין היומי → תוכנית עבודה ב-monday ----
import json
import re

INTEL_SUBJECT = 'דו"ח מודיעין יומי'
_NAMES = {d["name"]: k for k, d in DEPARTMENTS.items()}
_NAMES.update({old: k for k, d in DEPARTMENTS.items() for old in OLD_NAMES.get(d["name"], ())})  # דוחות ישנים
_ACTION = re.compile(r"^\W*(" + "|".join(_NAMES) + r")\s*:\s*(.+)$")
_URGENT = {"דחוף": "🔴 דחוף", "גבוהה": "🔴 דחוף", "חשוב": "🟠 חשוב", "בינונית": "🟠 חשוב", "רגיל": "🟢 רגיל", "נמוכה": "🟢 רגיל"}
INTEL_COLS = (("🔥 דחיפות", "status"), ("📅 תאריך יעד", "date"), ("🧬 מקור", "text"))


def parse_intel_actions(text: str, year: int) -> list:
    """מוציאה מהדוח את שורות הפעולות: 'ג׳סיקה: לעשות X | דחיפות: גבוהה | עד: 18.11'."""
    out = []
    for line in (text or "").splitlines():
        m = _ACTION.match(line.strip().replace("'", "׳"))
        if not m:
            continue
        parts = [p.strip() for p in m.group(2).split("|")]
        act = {"dept": _NAMES[m.group(1)], "title": parts[0][:200], "urgency": "🟠 חשוב", "due": ""}
        for p in parts[1:]:
            if p.startswith("דחיפות"):
                word = p.split(":", 1)[-1].strip()
                act["urgency"] = next((v for k, v in _URGENT.items() if k in word), act["urgency"])
            elif p.startswith("עד"):
                d = re.search(r"(\d{1,2})[./](\d{1,2})", p)
                if d:
                    act["due"] = f"{year}-{int(d.group(2)):02d}-{int(d.group(1)):02d}"
        if act["title"]:
            out.append(act)
    return out


def _cols(board: dict) -> dict:
    data = tools_monday._query("query ($ids: [ID!]) { boards(ids: $ids) { columns { id title type } } }",
                               {"ids": [board["id"]]}, "anycan")["boards"][0]["columns"]
    have = {c["title"].strip(): c["id"] for c in data}
    ids = {}
    for title, kind in INTEL_COLS:
        ids[title] = have.get(title) or tools_monday._query(
            "mutation ($b: ID!, $t: String!, $k: ColumnType!) { create_column(board_id: $b, title: $t, column_type: $k) { id } }",
            {"b": board["id"], "t": title, "k": kind}, "anycan")["create_column"]["id"]
    return ids


def _names_in_group(board_id: str, group_id: str) -> set:
    data = tools_monday._query(
        "query ($b: [ID!], $g: [String]) { boards(ids: $b) { groups(ids: $g) { items_page(limit: 500) { items { name } } } } }",
        {"b": [board_id], "g": [group_id]}, "anycan")
    groups = data["boards"][0].get("groups") or []
    return {it["name"].strip() for g in groups for it in g["items_page"]["items"]}


def import_intel_actions(days: int = 2) -> str:
    """לוקחת את הפעולות מ'דו"ח מודיעין יומי' האחרון במייל ופותחת אותן כתוכנית עבודה ב-monday של AnyCan:
    כל פעולה נכנסת לקבוצה של המחלקה שלה (ג׳סיקה, אמילי, רות...) עם דחיפות, תאריך יעד ומקור. פעולה שכבר קיימת לא נפתחת שוב.
    רץ לבד כל ערב אחרי שהדוח מגיע. השתמשי כשיוסי מבקש 'תכניסי את הדוח למנדיי' או 'תפתחי תוכנית עבודה מהמודיעין'."""
    import tools_gmail
    from datetime import date
    found = tools_gmail.search_emails(f'subject:"{INTEL_SUBJECT}" newer_than:{int(days)}d', max_results=3, account="gmail")
    ids = re.findall(r"^\[([^\]]+)\]", found, flags=re.M)
    if not ids:
        return "אין דו\"ח מודיעין חדש."
    text = tools_gmail.read_email(ids[0])
    when = re.search(r"נושא:.*?(\d{2}\.\d{2}\.\d{4})", text)
    acts = parse_intel_actions(text, date.today().year)
    if not acts:
        return "בדוח האחרון לא מצאתי שורות פעולה."
    board = _board()
    cols = _cols(board)
    made = []
    for a in acts:
        d = DEPARTMENTS[a["dept"]]
        gid = _group_id(board, d["group"])
        name = f"🧬 {a['title']}"[:250]
        if name in _names_in_group(board["id"], gid):
            continue
        values = {cols["🔥 דחיפות"]: {"label": a["urgency"]}, cols["🧬 מקור"]: f"{INTEL_SUBJECT} {when.group(1) if when else ''}".strip()}
        if a["due"]:
            values[cols["📅 תאריך יעד"]] = {"date": a["due"]}
        tools_hub._create(board["id"], gid, name, values, "anycan")
        made.append(f"{d['emoji']} {d['name']}: {a['title']} ({a['urgency']})")
    if not made:
        return "כל הפעולות מהדוח כבר נמצאות ב-monday."
    return "נפתחו ב-monday " + str(len(made)) + " משימות מהמודיעין:\n" + "\n".join(made)


STAFF_TOOLS.append(import_intel_actions)


# ---- יומן הפעולות של Claude → monday של AnyCan, כל בוקר ב-06:00 ----
# יוסי (15.11.2026): כל פעולה ש-Claude עושה בשבילו (נרשמת בגיליון "יומן הפעולות של Claude")
# נכנסת כל בוקר ב-06:00 ל-monday של AnyCan, לקבוצה של המחלקה שעשתה אותה. רק AnyCan — אף פעם לא אלפא אומגה.
import os

CLAUDE_LOG_HOUR = int(os.environ.get("CLAUDE_LOG_SYNC_HOUR", "6"))
CLAUDE_LOG_MAX = 150     # הגנה: לא יותר מ-150 שורות בריצה אחת
CLAUDE_MARK = "🤖 "      # כך מזהים ב-monday שורה שהגיעה מהיומן של Claude
_DATE = re.compile(r"^\s*(\d{1,2})[./](\d{1,2})[./](\d{4})")


def _row_date(text: str):
    from datetime import date
    m = _DATE.match(text or "")
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def dept_of_action(where: str, what: str, details: str = "") -> str:
    """לאיזו מחלקה שייכת פעולה מהיומן: קודם לפי שם של בעלת תפקיד (גם השמות הישנים), אחר כך לפי מילות המפתח. ברירת מחדל: סוזן."""
    text = f"{where} {what} {details}".replace("'", "׳")
    for name, key in _NAMES.items():
        if name in text:
            return key
    return route(text) or "admin"


def claude_action_name(row: list) -> str:
    r = (list(row) + [""] * 5)[:5]
    return f"{CLAUDE_MARK}{r[0].strip()} {r[1].strip()} · {r[3].strip() or r[2].strip() or 'פעולה'}"[:250]


def import_claude_actions(days: int = 2) -> str:
    """מכניסה ל-monday של AnyCan את הפעולות ש-Claude עשה בשביל יוסי (מהגיליון 'יומן הפעולות של Claude'):
    כל פעולה היא שורה בקבוצה של המחלקה שעשתה אותה (יונתן, רות, ננסי, ג׳סיקה, אמילי, סוזן, ג׳ניפר), עם הפרטים כעדכון.
    שורה שכבר נכנסה לא נכנסת שוב. רץ לבד כל בוקר ב-06:00 על היומיים האחרונים.
    השתמשי כשיוסי מבקש 'תכניסי את הפעולות של Claude למנדיי'."""
    import tools_claude_log
    from datetime import date, timedelta
    since = date.today() - timedelta(days=max(0, int(days)))
    rows = [r for r in tools_claude_log._rows()[1:] if (_row_date(r[0] if r else "") or date.min) >= since]
    if not rows:
        return "אין פעולות חדשות של Claude ביומיים האחרונים."
    board = _board()
    have, made = {}, {}
    for r in rows:
        if sum(made.values()) >= CLAUDE_LOG_MAX:
            break
        r = (list(r) + [""] * 5)[:5]
        key = dept_of_action(r[2], r[3], r[4])
        d = DEPARTMENTS[key]
        gid = _group_id(board, d["group"])
        if gid not in have:
            have[gid] = _names_in_group(board["id"], gid)
        name = claude_action_name(r)
        if name in have[gid]:
            continue
        item = tools_hub._create(board["id"], gid, name, {}, "anycan")
        have[gid].add(name)
        body = f"מקור: יומן הפעולות של Claude\nאיפה: {r[2]}\nמה: {r[3]}" + (f"\nפרטים: {r[4]}" if r[4].strip() else "")
        tools_monday._query("mutation ($i: ID!, $b: String!) { create_update(item_id: $i, body: $b) { id } }",
                            {"i": item, "b": body[:2000]}, "anycan")
        made[key] = made.get(key, 0) + 1
    if not made:
        return "כל הפעולות של Claude כבר נמצאות ב-monday."
    parts = [f"{DEPARTMENTS[k]['emoji']} {DEPARTMENTS[k]['name']}: {n}" for k, n in made.items()]
    return f"נכנסו ל-monday {sum(made.values())} פעולות של Claude — " + ", ".join(parts)


STAFF_TOOLS.append(import_claude_actions)
