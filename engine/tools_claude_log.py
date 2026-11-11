"""יומן הפעולות של Claude — גיליון בדרייב של יוסי שבו Claude רושם כל פעולה שעשה בשבילו. שולה קוראת אותו (קריאה בלבד)."""
import csv
import io
import os

import google_auth

LOG_FILE_ID = os.environ.get("CLAUDE_LOG_FILE_ID", "1qfcyEqQ-mqFkM-x_pSVax3ZBe5GrlLF_YPLMHqgzfpw")


def _rows() -> list[list[str]]:
    drive = google_auth.service("drive", "v3", google_auth.MAIN)
    raw = drive.files().export(fileId=LOG_FILE_ID, mimeType="text/csv").execute()
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    return [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]


def get_claude_actions(search: str = "", limit: int = 20) -> str:
    """מחזיר את הפעולות האחרונות ש-Claude עשה בשביל יוסי (במנדיי, ביומן, במיילים, בקבצים ועוד) — מהחדש לישן.
    search = מילה לסינון (תאריך כמו 11.11.2026, מקום כמו 'מנדיי', או מילה מהתיאור). limit = כמה פעולות לכל היותר (עד 60).
    השתמשי כשיוסי שואל 'מה Claude עשה', 'מה נעשה היום', 'האם זה כבר טופל'."""
    rows = _rows()[1:]  # בלי שורת הכותרת
    s = (search or "").strip().lower()
    lines = []
    for r in reversed(rows):
        r = (r + [""] * 5)[:5]
        line = f"- {r[0]} {r[1]} | {r[2]} | {r[3]}" + (f" — {r[4]}" if r[4].strip() else "")
        if not s or s in line.lower():
            lines.append(line[:500])
    if not lines:
        return "אין עדיין פעולות ביומן של Claude." if not s else f"לא מצאתי ביומן של Claude פעולות שמתאימות ל-'{search}'."
    return "<claude_log_data>\n" + "\n".join(lines[:max(1, min(int(limit), 60))]) + "\n</claude_log_data>"


CLAUDE_LOG_TOOLS = [get_claude_actions]
