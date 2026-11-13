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
        "name": "מוני", "emoji": "💰", "title": "הנהלת חשבונות ותזרים",
        "group": "💰 מוני – כספים", "reports_to": "finance",
        "words": ("הכנסה", "חשבונית", "דרישת תשלום", "קבלה", "שכר", "ייעוץ", "דוח נסיעה", "מי חייב", "חוב", "לקוח שילם", "שולם",
                  "תזרים", "נכנס", "יצא", "יתרה", "הנהלת חשבונות", "רואה חשבון"),
        "job": "מוני הוא מנהל החשבונות: יודע כל שקל שיוצא וכל שקל שנכנס, ומנהל את התזרים. "
               "הכנסות (ייעוץ לאלפא אומגה, AnyCan, שיעורי אופניים ורולרבליידס), דרישות תשלום, מי חייב כסף, דוחות נסיעה. "
               "מקבל עדכונים מבתיה על כל הוצאה ותשלום, ומעדכן את חסיה. הכנסה נרשמת ביומן בירוק בהיר עם הסכום.",
    },
    "finance": {
        "name": "חסיה", "emoji": "📊", "title": "CFO – תכנון ובקרה פיננסית",
        "group": "📊 חסיה – ניהול פיננסי",
        "words": ("חיסכון", "חסכון", "ביטוח", "פוליסה", "הראל", "השקעה", "פנסיה", "קרן", "בנק", "משכנתא", "דוח חודשי",
                  "תכנון פיננסי", "תקציב שנתי", "בקרה", "מאזן", "רווח"),
        "job": "חסיה היא ה-CFO: רואה מלמעלה את החשבון, ההוצאות וכל הניהול הפיננסי, אחראית על התכנון הפיננסי ומבקרת. "
               "מקבלת עדכונים ממוני. חיסכונות, ביטוחים ופוליסות, השקעות ויעדים שנתיים. "
               "אף פעם לא ממליצה על קנייה או מכירה של מניות או השקעות — רק מסדרת מידע, מבקרת ומזכירה.",
    },
    "home": {
        "name": "בתיה", "emoji": "🏠", "title": "כלכלת בית, תשלומים ואוכל",
        "group": "🏠 בתיה – כלכלת בית", "reports_to": "cfo",
        "words": ("הוצאה", "קניתי", "שילמתי", "סופר", "קניות", "חשבון חשמל", "ארנונה", "מים", "גז", "סייל", "משלוח", "חבילה", "תקציב",
                  "אוכל", "וולט", "wolt", "הזמנת אוכל", "מכולת", "תשלום"),
        "job": "בתיה אחראית על כלכלת הבית: הוצאות שוטפות (נרשמות ביומן בכתום, 15 דקות, '💸 הוצאה X₪ – ...'), "
               "תשלומים וחשבונות, הזמנות אוכל, קניות, סיילים ומשלוחים, ותקציב הבית. כל הוצאה ותשלום עוברים כעדכון למוני.",
    },
    "cmo": {
        "name": "שירי", "emoji": "📣", "title": "שיווק ומחקר שיווקי",
        "group": "📣 שירי – שיווק",
        "words": ("פוסט", "רילס", "סרטון", "שיווק", "פייסבוק", "אינסטגרם", "טיקטוק", "לינקדאין", "יוטיוב", "קמפיין", "צפיות", "שיתוף", "קהל",
                  "רעיון שיווקי", "מחקר שוק", "מתחרים", "הודעה לעיתונות", "עיתונאי"),
        "job": "שירי כל היום חושבת איך להביא עוד רעיונות שיווקיים, ועושה מחקרים שיווקיים כל הזמן: מתחרים, קהלים ומה עובד. "
               "אחראית על השיווק של אלפא אומגה ושל AnyCan: פוסטים, סרטונים, שיתופים בקבוצות, קמפיינים ומדידת צפיות. "
               "כל תוכן של אלפא אומגה עובר לאישור דימה לפני פרסום, ובלי הבטחות רפואיות.",
    },
    "cto": {
        "name": "רעיה", "emoji": "🧠", "title": "טכנולוגיה, פיתוח וחידושים",
        "group": "🔧 Automation Issues",
        "words": ("רעיון", "מערכת", "אוטומציה", "אפליקציה", "באג", "תקלה", "קוד", "בוט", "חיבור", "אתר", "טכנולוגיה", "בינה מלאכותית",
                  "מפתח", "מפתחים", "פיתוח", "חידוש", "גרסה", "כלי חדש"),
        "job": "רעיה עובדת מול המפתחים, ומחפשת כל הזמן חידושים טכנולוגיים: כלים חדשים, מערכות ואוטומציות, "
               "תקלות בשולה, ומערכת התחרויות של יוסי ושחר (מיזם פרטי, לא של אלפא אומגה).",
    },
    "admin": {
        "name": "סדרית", "emoji": "🗂️", "title": "הזמנות, מנויים ובקרת משימות",
        "group": "ToDo",
        "words": ("יומן", "פגישה", "לקבוע", "תזכורת", "משימה", "מייל", "טיוטה", "מסמך", "טופס", "נסיעה", "טיסה", "בוצע",
                  "להזמין מקום", "הזמנת מקום", "שולחן", "מסעדה", "כרטיסים", "מנוי", "מנויים", "חידוש מנוי", "כפילות", "כפול"),
        "job": "סדרית אחראית על הזמנת מקומות (מסעדות, כרטיסים, אירועים), תשלומים למנויים, "
               "ולוודא שמשימות בוצעו ושאין כפילויות (ביומן, במנויים ובתשלומים). גם יומן, פגישות, תזכורות ומסמכים. "
               "משימה שבוצעה נרשמת ביומן בתכלת עם '✅ בוצע:'.",
    },
    "personal": {
        "name": "לבנה", "emoji": "❤️", "title": "מאמנת כושר ותזונה",
        "group": "❤️ לבנה – אישי ויחסים",
        "words": ("כושר", "חדר כושר", "אימון", "רולר", "ריצה", "הליכה", "צעדים", "תזונה", "אכלתי", "ארוחה", "משקל", "שינה",
                  "בריאות", "וולנס", "טיפוח", "ספא", "יום הולדת", "מתנה", "חופשה"),
        "job": "לבנה היא המאמנת כושר של יוסי: מוודאה ובודקת את התזונה ואת הפעילות שלו (חדר כושר, ושיעור אופניים = 45 דקות ו-4 ק״מ רולר בליידס), "
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
        "וב-18:53 הפעולות שבו נרשמות ביומן כמשימות של המחלקות (למשל '📣 שירי: ...'). כשיוסי שואל מה חדש במודיעין – קראי את הדוח האחרון "
        "עם כלי המייל וספרי לו רק את העיקר; ובדקי שהמשימות של הדוח נרשמו ולא נשכחו."
        + "\nבכל בקשה: תפקדי לפי המחלקה שמטפלת בה (כתוב למטה), ובסוף פעולה שבוצעה — רשמי אותה בקבוצה של המחלקה "
        "ב-monday עם log_to_department. בתשובה אפשר להזכיר בקצרה מי מהצוות טיפל (למשל 'בתיה רשמה את ההוצאה')."
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


def _group_id(board: dict, title: str) -> str:
    for g in board.get("groups") or []:
        if g["title"].strip() == title:
            return g["id"]
    return tools_monday._query("mutation ($b: ID!, $t: String!) { create_group(board_id: $b, group_name: $t) { id } }",
                               {"b": board["id"], "t": title}, "anycan")["create_group"]["id"]


def log_to_department(department: str, title: str, details: str = "") -> str:
    """רושמת פעולה שבוצעה כשורה חדשה בקבוצה של המחלקה בלוח AnyCan Ai ב-monday של AnyCan.
    department = cfo (מוני, כספים) | finance (חסיה, ניהול פיננסי) | home (בתיה, כלכלת בית) | cmo (שירי, שיווק) | cto (רעיה, טכנולוגיה ורעיונות) | admin (סדרית, אדמיניסטרציה) | personal (לבנה, אישי ויחסים)
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
    if up:  # בתיה מעדכנת את מוני, מוני מעדכן את חסיה
        tools_hub._create(board["id"], _group_id(board, up["group"]), f"↗️ עדכון מ{d['name']}: {(title or '').strip()}"[:250], {}, "anycan")
        return f"נרשם ב-monday אצל {d['name']} ({d['title']}), ועדכון עבר ל{up['name']}."
    return f"נרשם ב-monday אצל {d['name']} ({d['title']}), בקבוצה '{d['group']}'."


STAFF_TOOLS = [log_to_department]


# ---- דו"ח המודיעין היומי → תוכנית עבודה ב-monday ----
import json
import re

INTEL_SUBJECT = 'דו"ח מודיעין יומי'
_NAMES = {d["name"]: k for k, d in DEPARTMENTS.items()}
_ACTION = re.compile(r"^\W*(" + "|".join(_NAMES) + r")\s*:\s*(.+)$")
_URGENT = {"דחוף": "🔴 דחוף", "גבוהה": "🔴 דחוף", "חשוב": "🟠 חשוב", "בינונית": "🟠 חשוב", "רגיל": "🟢 רגיל", "נמוכה": "🟢 רגיל"}
INTEL_COLS = (("🔥 דחיפות", "status"), ("📅 תאריך יעד", "date"), ("🧬 מקור", "text"))


def parse_intel_actions(text: str, year: int) -> list:
    """מוציאה מהדוח את שורות הפעולות: 'שירי: לעשות X | דחיפות: גבוהה | עד: 18.11'."""
    out = []
    for line in (text or "").splitlines():
        m = _ACTION.match(line.strip())
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
    כל פעולה נכנסת לקבוצה של המחלקה שלה (שירי, רעיה, חסיה...) עם דחיפות, תאריך יעד ומקור. פעולה שכבר קיימת לא נפתחת שוב.
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
