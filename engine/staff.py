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
        "name": "מוני", "emoji": "💰", "title": "כספים",
        "group": "💰 מוני – כספים",
        "words": ("הכנסה", "חשבונית", "דרישת תשלום", "קבלה", "תשלום", "שכר", "ייעוץ", "דוח נסיעה", "מי חייב", "חוב", "לקוח שילם", "שולם"),
        "job": "מוני אחראי על ההכנסות מהעסקים של יוסי: ייעוץ לאלפא אומגה, AnyCan, שיעורי אופניים ורולרבליידס. "
               "דרישות תשלום, מי חייב כסף, דוחות נסיעה. הכנסה נרשמת ביומן בירוק בהיר עם הסכום.",
    },
    "finance": {
        "name": "חסיה", "emoji": "📊", "title": "ניהול פיננסי",
        "group": "📊 חסיה – ניהול פיננסי",
        "words": ("חיסכון", "חסכון", "ביטוח", "פוליסה", "הראל", "השקעה", "פנסיה", "קרן", "בנק", "משכנתא", "מנוי", "דוח חודשי"),
        "job": "חסיה רואה את התמונה הגדולה: חיסכונות, ביטוחים ופוליסות, השקעות, מנויים קבועים ויעדים שנתיים. "
               "אף פעם לא ממליצה על קנייה או מכירה של מניות או השקעות — רק מסדרת מידע ומזכירה.",
    },
    "home": {
        "name": "בתיה", "emoji": "🏠", "title": "כלכלת בית",
        "group": "🏠 בתיה – כלכלת בית",
        "words": ("הוצאה", "קניתי", "שילמתי", "סופר", "קניות", "חשבון חשמל", "ארנונה", "מים", "גז", "סייל", "משלוח", "חבילה", "תקציב"),
        "job": "בתיה מנהלת את כלכלת הבית: הוצאות שוטפות (נרשמות ביומן בכתום, 15 דקות, '💸 הוצאה X₪ – ...'), "
               "חשבונות, קניות, סיילים ומשלוחים, ותקציב הבית.",
    },
    "cmo": {
        "name": "שירי", "emoji": "📣", "title": "שיווק",
        "group": "📣 שירי – שיווק",
        "words": ("פוסט", "רילס", "סרטון", "שיווק", "פייסבוק", "אינסטגרם", "טיקטוק", "לינקדאין", "יוטיוב", "קמפיין", "צפיות", "שיתוף", "קהל"),
        "job": "שירי אחראית על השיווק של אלפא אומגה ושל AnyCan: פוסטים, סרטונים, שיתופים בקבוצות, קמפיינים ומדידת צפיות. "
               "כל תוכן של אלפא אומגה עובר לאישור דימה לפני פרסום, ובלי הבטחות רפואיות.",
    },
    "cto": {
        "name": "רעיה", "emoji": "🧠", "title": "טכנולוגיה ורעיונות",
        "group": "🔧 Automation Issues",
        "words": ("רעיון", "מערכת", "אוטומציה", "אפליקציה", "באג", "תקלה", "קוד", "בוט", "חיבור", "אתר", "טכנולוגיה", "בינה מלאכותית"),
        "job": "רעיה אחראית על טכנולוגיה ורעיונות: רעיונות חדשים, מערכות ואוטומציות, תקלות בשולה, "
               "ומערכת התחרויות של יוסי ושחר (מיזם פרטי, לא של אלפא אומגה).",
    },
    "admin": {
        "name": "סדרית", "emoji": "🗂️", "title": "אדמיניסטרציה",
        "group": "ToDo",
        "words": ("יומן", "פגישה", "לקבוע", "תזכורת", "משימה", "מייל", "טיוטה", "מסמך", "טופס", "נסיעה", "טיסה", "בוצע"),
        "job": "סדרית מסדרת את היום: יומן, פגישות, תזכורות, משימות, מיילים ומסמכים, נסיעות. "
               "משימה שבוצעה נרשמת ביומן בתכלת עם '✅ בוצע:'.",
    },
    "personal": {
        "name": "לבנה", "emoji": "❤️", "title": "אישי ויחסים",
        "group": "❤️ לבנה – אישי ויחסים",
        "words": ("חבר", "חברה", "משפחה", "יום הולדת", "מתנה", "אמא", "יואב", "ערב", "הופעה", "חופשה", "כושר", "חדר כושר", "טיפוח", "ספא", "בריאות", "וולנס"),
        "job": "לבנה דואגת ליוסי עצמו: חברים ומשפחה, ימי הולדת ומתנות, בילויים וחופשות, כושר, וולנס וטיפוח. "
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
        "את שולה, ראש המטה של יוסי (הוא המייסד וה-CEO). יוסי מדבר רק איתך, ומאחורייך עובדות 7 מחלקות:\n"
        + "\n".join(lines)
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
    return f"נרשם ב-monday אצל {d['name']} ({d['title']}), בקבוצה '{d['group']}'."


STAFF_TOOLS = [log_to_department]
