"""משימות מאלפא אומגה (וואטסאפ ומייל) → המחלקות במטה, ב-monday של AnyCan.
יוסי (20.11.2026): כל דבר שעולה בוואטסאפ עם אנשי אלפא אומגה צריך להפוך למשימה אצל המחלקה הנכונה במטה,
ולעבור בין המחלקות כשצריך (למשל ביקורים: סוזן מתאמת, יונתן רואה את הכסף).
כל ערב Claude קורא את הוואטסאפ, ובגיליון 'משימות למחלקות – מטה שולה' כותב שורה לכל משימה:
מזהה, תאריך, מקור, איש קשר, מחלקה, גם אצל, משימה, הצעד הבא ליוסי, עד מתי, דחיפות, קישור מייל, סטטוס.
שולה קוראת את הגיליון כל שעה ופותחת כל משימה בקבוצה של המחלקה בלוח AnyCan Ai, עם דחיפות, תאריך יעד ומקור,
ושורת '↗️' אצל כל מחלקה שמופיעה ב'גם אצל'. משימה שכבר נפתחה לא נפתחת שוב. שורה שסומנה 'בוצע' מקבלת ✅ בפריט.
רק ה-monday של AnyCan — אף פעם לא אלפא אומגה."""
import csv
import io
import logging
import os

import google_auth
import staff
import tools_hub
import tools_monday

log = logging.getLogger("shula.aotasks")
SHEET_ID = os.environ.get("AO_TASKS_FILE_ID", "1AsuadOzzD9KDigFJAExaHm8mYQIC7U4j1vDcCwrHvMo")
SHULA_GROUP = "⭐ שולה – ראש המטה"
MARK = "📲 "          # כך מזהים ב-monday משימה שהגיעה ממעקב אלפא אומגה
DONE = "✅ #"         # סימון בעדכון: המשימה הזאת כבר סומנה כבוצעה
MAX_TASKS = 40        # הגנה: לא יותר מ-40 משימות בריצה אחת
COLS = 12             # מזהה..סטטוס


def _rows() -> list[list[str]]:
    drive = google_auth.service("drive", "v3", google_auth.MAIN)
    raw = drive.files().export(fileId=SHEET_ID, mimeType="text/csv").execute()
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    return [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]


def dept_key(name: str) -> str | None:
    """'סוזן' → admin. 'שולה' → 'shula' (קבוצה משלה). שם לא מוכר → None."""
    n = (name or "").strip().replace("'", "׳")
    if not n:
        return None
    if "שולה" in n:
        return "shula"
    for staff_name, key in staff._NAMES.items():
        if staff_name in n:
            return key
    return None


def _group_title(key: str) -> str:
    return SHULA_GROUP if key == "shula" else staff.DEPARTMENTS[key]["group"]


def _who(key: str) -> str:
    if key == "shula":
        return "⭐ שולה"
    d = staff.DEPARTMENTS[key]
    return f"{d['emoji']} {d['name']}"


def task_name(task: str, contact: str) -> str:
    return f"{MARK}{task.strip()} – {contact.strip()}"[:250]


def _due(text: str) -> str:
    d = staff._row_date(text)
    return d.isoformat() if d else ""


def _items(board_id: str, group_id: str) -> dict:
    """שם → מזהה, לכל הפריטים בקבוצה."""
    data = tools_monday._query(
        "query ($b: [ID!], $g: [String]) { boards(ids: $b) { groups(ids: $g) { items_page(limit: 500) { items { id name } } } } }",
        {"b": [board_id], "g": [group_id]}, "anycan")
    groups = data["boards"][0].get("groups") or []
    return {it["name"].strip(): it["id"] for g in groups for it in g["items_page"]["items"]}


def _updates(item_id: str) -> list:
    items = tools_monday._query("query ($ids: [ID!]) { items(ids: $ids) { updates(limit: 50) { text_body } } }",
                                {"ids": [item_id]}, "anycan").get("items") or []
    return [u.get("text_body") or "" for u in (items[0].get("updates") if items else []) or []]


def _update(item_id: str, body: str) -> None:
    tools_monday._query("mutation ($i: ID!, $b: String!) { create_update(item_id: $i, body: $b) { id } }",
                        {"i": item_id, "b": body[:2000]}, "anycan")


def import_ao_tasks(preview: bool = False) -> str:
    """פותחת ב-monday של AnyCan את המשימות שעלו מהוואטסאפ והמיילים עם אנשי אלפא אומגה (מהגיליון 'משימות למחלקות – מטה שולה'):
    כל משימה נכנסת לקבוצה של המחלקה שלה (סוזן, יונתן, ג׳סיקה, אמילי, אוליביה, רות, או שולה) עם דחיפות, תאריך יעד ומקור,
    ועדכון בפריט: איש הקשר, הצעד הבא של יוסי וקישור למייל. מחלקה ב'גם אצל' מקבלת שורת '↗️' בקבוצה שלה.
    משימה שכבר נפתחה לא נפתחת שוב; משימה שסומנה 'בוצע' בגיליון מקבלת ✅ בפריט. רץ לבד כל שעה.
    השתמשי כשיוסי שואל 'מה פתוח מול אלפא אומגה', 'תכניסי את המשימות מהוואטסאפ למנדיי'. preview=True = רק להראות מה ייכנס."""
    rows = [(list(r) + [""] * COLS)[:COLS] for r in _rows()[1:]]
    rows = [r for r in rows if r[0].strip() and r[6].strip()]
    if not rows:
        return "אין משימות מאלפא אומגה בגיליון."
    board = None if preview else staff._board()
    cols = None
    groups, made, done, skipped, lines = {}, 0, 0, 0, []

    def group(key):
        if key not in groups:
            gid = staff._group_id(board, _group_title(key))
            groups[key] = (gid, _items(board["id"], gid))
        return groups[key]

    for tid, when, source, contact, dept, also, task, step, due, urgency, link, status in rows:
        if made >= MAX_TASKS:
            lines.append(f"עצרתי אחרי {MAX_TASKS} משימות — השאר ייכנסו בריצה הבאה.")
            break
        key = dept_key(dept)
        if not key:
            skipped += 1
            lines.append(f"- {tid}: מחלקה לא מוכרת '{dept}'")
            continue
        name = task_name(task, contact)
        is_done = "בוצע" in status
        if preview:
            if not is_done:
                lines.append(f"- {_who(key)}: {task.strip()} ({contact.strip()})")
                made += 1
            continue
        try:
            gid, have = group(key)
            if is_done:
                item = have.get(name)
                if item and not any(DONE + tid.strip() in u for u in _updates(item)):
                    _update(item, f"✅ בוצע (לפי מעקב אלפא אומגה)\n{DONE}{tid.strip()}")
                    done += 1
                    lines.append(f"- ✅ {_who(key)}: {task.strip()}")
                continue
            if name in have:
                continue
            if cols is None:
                cols = staff._cols(board)
            label = next((v for k, v in staff._URGENT.items() if k in urgency), "🟠 חשוב")
            values = {cols["🔥 דחיפות"]: {"label": label},
                      cols["🧬 מקור"]: f"{source.strip() or 'וואטסאפ'} · {tid.strip()} · {when.strip()}"}
            if _due(due):
                values[cols["📅 תאריך יעד"]] = {"date": _due(due)}
            item = tools_hub._create(board["id"], gid, name, values, "anycan")
            have[name] = item
            others = [k for k in (dept_key(a) for a in also.split(",")) if k and k != key]
            body = (f"מקור: מעקב אלפא אומגה ({source.strip() or 'וואטסאפ'}), {when.strip()}\n"
                    f"איש קשר: {contact.strip()}\nמשימה: {task.strip()}\n"
                    + (f"הצעד הבא ליוסי: {step.strip()}\n" if step.strip() else "")
                    + (f"עד: {due.strip()}\n" if due.strip() else "")
                    + (f"מייל: {link.strip()}\n" if link.strip() else "")
                    + (f"גם אצל: {', '.join(_who(k) for k in others)}\n" if others else "")
                    + f"🆔 {tid.strip()}")
            _update(item, body)
            for k in others:  # המשימה עוברת גם למחלקות האחרות
                ogid, ohave = group(k)
                oname = f"↗️ מ{_who(key)}: {task.strip()} – {contact.strip()}"[:250]
                if oname not in ohave:
                    ohave[oname] = tools_hub._create(board["id"], ogid, oname, {}, "anycan")
            made += 1
            lines.append(f"- {_who(key)}: {task.strip()} ({contact.strip()})"
                         + (f" ↗️ {', '.join(_who(k) for k in others)}" if others else ""))
        except Exception as e:  # תווית חסרה, קבוצה שנמחקה וכו' — ממשיכים לשאר
            skipped += 1
            lines.append(f"- {tid}: לא נכנס ({str(e)[:120]})")
    if not made and not done and not skipped:
        return "כל המשימות מאלפא אומגה כבר נמצאות ב-monday."
    if preview:
        return f"ייפתחו ב-monday {made} משימות מאלפא אומגה:\n" + "\n".join(lines[:40])
    head = f"נפתחו ב-monday {made} משימות מאלפא אומגה" + (f", {done} סומנו בוצע" if done else "") \
        + (f", {skipped} לא נכנסו" if skipped else "") + ":"
    return "\n".join([head] + lines[:40])


AOTASKS_TOOLS = [import_ao_tasks]
