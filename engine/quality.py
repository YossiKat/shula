"""קלייר – בקרת איכות: כל מייל שיוצא (טיוטה או שליחה) עובר כאן קודם.
בודקת שאין שאריות (מקומות ריקים, [לבדוק], TODO), טעויות פשוטות, וסימנים שהמייל נכתב או נערך על ידי AI."""
import re

LEFTOVERS = ("[לבדוק", "לבדוק:", "todo", "tbd", "xxx", "placeholder", "lorem", "[שם", "<שם", "[name", "[your name",
             "[insert", "[company", "[date", "[תאריך", "[טלפון", "[מספר", "{{", "}}")
AI_SIGNS = ("as an ai", "language model", "i hope this email finds you well", "i hope this message finds you well",
            "i hope you're doing well", "delve", "certainly!", "great question", "here's a draft", "here is a draft",
            "feel free to adjust", "הנה טיוטה", "הנה המייל", "הנה נוסח", "כמודל שפה", "בתור בינה מלאכותית",
            "אשמח לעזור בכל שאלה נוספת", "generated with", "🤖", "subject:", "נושא:")
MARKDOWN = ("**", "##", "```", "__")


def check_email(subject: str, body: str) -> list[str]:
    """מחזירה רשימת בעיות. רשימה ריקה = המייל עבר את בקרת האיכות."""
    problems: list[str] = []
    subject, body = (subject or "").strip(), (body or "").strip()
    if not subject:
        problems.append("אין נושא למייל")
    if not body:
        problems.append("המייל ריק")
    text = f"{subject}\n{body}"
    low = text.lower()
    for w in LEFTOVERS:
        if w in low:
            problems.append(f"שארית שלא מולאה: '{w}'")
    for w in AI_SIGNS:
        if w in low:
            problems.append(f"נשמע כמו AI: '{w}'")
    for w in MARKDOWN:
        if w in text:
            problems.append(f"סימן עיצוב של AI שלא ייראה טוב במייל: '{w}'")
    if "—" in text:
        problems.append("קו ארוך (—) – סימן מוכר לכתיבה של AI; להחליף בפסיק או בנקודה")
    for m in re.finditer(r"(?<!\w)([^\W\d_]{2,})\s+\1(?!\w)", text):
        problems.append(f"מילה כפולה: '{m.group(1)} {m.group(1)}'")
    if "  " in body.replace("\n", ""):
        problems.append("רווח כפול באמצע שורה")
    return problems


def gate(subject: str, body: str) -> str:
    """'' אם הכל תקין; אחרת הודעה לשולה מה לתקן לפני שהמייל יוצא."""
    problems = check_email(subject, body)
    if not problems:
        return ""
    return ("🔍 קלייר (בקרת איכות) עצרה את המייל – לתקן ולנסות שוב:\n- " + "\n- ".join(problems))
