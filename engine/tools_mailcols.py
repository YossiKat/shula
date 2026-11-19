"""עמודות ב-monday של AnyCan לפי המיילים של יוסי.
יוסי (19.11.2026): "לעדכן את העמודות ודרכי הפעולה בתוך המנדיי בהתאם לתוכן שמופיע בכל מייל" — בחר שזה ייעשה דרך שולה.
כל ערב Claude קורא את המיילים, ובגיליון 'שינויים למנדיי' כותב שורה לכל שינוי: פריט, עמודה, ערך חדש וסיבה.
שולה קוראת את הגיליון כל שעה ומכניסה את השינויים ל-monday של AnyCan בלבד, ועל כל שינוי כותבת עדכון בפריט.
שינוי שכבר נכנס (יש בפריט עדכון עם המזהה שלו) לא נכנס שוב."""
import csv
import io
import logging
import os
from datetime import date, datetime, timedelta

import google_auth
import tools_monday

log = logging.getLogger("shula.mailcols")
SHEET_ID = os.environ.get("MAIL_CHANGES_FILE_ID", "1SO05cYI95E7HBPqgz3lISTjzl4rOdnSrc4cL22ZXmj8")
NEXT_STEP = "👉 הצעד הבא"
ALLOWED = {"stage": "Stage", "priority": "Priority", "date": "Date", NEXT_STEP.lower(): NEXT_STEP}
MAX_CHANGES = 60  # הגנה: לא יותר מ-60 שינויים בריצה אחת
MARK = "🔧 #"     # סימון בעדכון: השינוי הזה כבר נכנס


def _rows() -> list[list[str]]:
    drive = google_auth.service("drive", "v3", google_auth.MAIN)
    raw = drive.files().export(fileId=SHEET_ID, mimeType="text/csv").execute()
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    return [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]


def _day(s: str):
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return None


def _item(item_id: str) -> dict:
    gql = """query ($ids: [ID!]) { items(ids: $ids) { id name board { id }
      column_values { id type column { title } } updates(limit: 50) { text_body } } }"""
    items = tools_monday._query(gql, {"ids": [item_id]}, "anycan").get("items") or []
    if not items:
        raise RuntimeError(f"לא מצאתי את הפריט {item_id} ב-monday של AnyCan")
    return items[0]


def _column(item: dict, title: str) -> dict | None:
    for c in item["column_values"]:
        if (c.get("column") or {}).get("title", "").strip().lower() == title.lower():
            return c
    return None


def _next_step_column(item: dict) -> dict:
    """העמודה '👉 הצעד הבא' בלוח של הפריט — נוצרת בפעם הראשונה (גם בלוח תתי-הפריטים)."""
    col = _column(item, NEXT_STEP)
    if col:
        return col
    made = tools_monday._query(
        "mutation ($b: ID!, $t: String!) { create_column(board_id: $b, title: $t, column_type: long_text) { id } }",
        {"b": item["board"]["id"], "t": NEXT_STEP}, "anycan")["create_column"]
    return {"id": made["id"], "type": "long_text", "column": {"title": NEXT_STEP}}


def _set(item: dict, col: dict, value: str) -> None:
    tools_monday._query(
        "mutation ($b: ID!, $i: ID!, $c: String!, $v: String!) {"
        " change_simple_column_value(board_id: $b, item_id: $i, column_id: $c, value: $v) { id } }",
        {"b": item["board"]["id"], "i": item["id"], "c": col["id"], "v": value}, "anycan")


def apply_mail_changes(days: int = 2, preview: bool = False) -> str:
    """מכניסה ל-monday של AnyCan את השינויים שנמצאו במיילים של יוסי (מהגיליון 'שינויים למנדיי'):
    Stage, Priority, Date ו'👉 הצעד הבא' על הפריט של האדם, ועדכון קצר בפריט שמסביר מה השתנה ולמה.
    רץ לבד כל שעה על היומיים האחרונים. השתמשי כשיוסי מבקש 'תכניסי את השינויים מהמיילים למנדיי'.
    preview=True = רק להראות מה ייכנס, בלי לשנות כלום."""
    since = date.today() - timedelta(days=max(0, int(days)))
    rows = [(list(r) + [""] * 7)[:7] for r in _rows()[1:]]
    rows = [r for r in rows if (_day(r[1]) or date.min) >= since and r[0].strip() and r[2].strip().isdigit()]
    done, skipped, lines = 0, 0, []
    for cid, _, item_id, name, column, value, why in rows:
        if done >= MAX_CHANGES:
            lines.append(f"עצרתי אחרי {MAX_CHANGES} שינויים — השאר ייכנסו בריצה הבאה.")
            break
        title = ALLOWED.get(column.strip().lower())
        if not title or not value.strip():
            skipped += 1
            continue
        try:
            item = _item(item_id.strip())
            stamp = MARK + cid.strip()
            if any(stamp in (u.get("text_body") or "") for u in item.get("updates") or []):
                continue
            if preview:
                lines.append(f"- {item['name']}: {title} ← {value.strip()} ({why.strip()})")
                done += 1
                continue
            col = _next_step_column(item) if title == NEXT_STEP else _column(item, title)
            if not col:
                skipped += 1
                lines.append(f"- {item['name']}: אין עמודה {title} בלוח שלו")
                continue
            _set(item, col, value.strip())
            body = f"🔧 {title} ← {value.strip()}\nלמה: {why.strip() or 'לפי המייל'}\n{stamp}"
            tools_monday._query("mutation ($i: ID!, $b: String!) { create_update(item_id: $i, body: $b) { id } }",
                                {"i": item["id"], "b": body[:2000]}, "anycan")
            done += 1
            lines.append(f"- {item['name']}: {title} ← {value.strip()}")
        except Exception as e:  # תווית שלא קיימת בלוח, פריט שנמחק וכו' — ממשיכים לשאר
            skipped += 1
            lines.append(f"- {name or item_id}: לא נכנס ({str(e)[:120]})")
    if not done and not skipped:
        return "אין שינויים חדשים מהמיילים."
    head = (f"ייכנסו ל-monday {done} שינויים מהמיילים:" if preview
            else f"נכנסו ל-monday {done} שינויים מהמיילים" + (f", {skipped} לא נכנסו" if skipped else "") + ":")
    return "\n".join([head] + lines[:40])


MAILCOLS_TOOLS = [apply_mail_changes]
