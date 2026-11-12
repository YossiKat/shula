"""כלי monday לשולה — קריאה בלבד משני החשבונות של יוסי:
Alpha Omega (הלוח AlphaCare Marketing & Campaign ideas and requests) ו-AnyCan Tech (הלוחות AnyCan Ai, Budget, Inventory)."""
import os

import requests

API = "https://api.monday.com/v2"
BOARDS = {
    "alphacare": os.environ.get("MONDAY_BOARD_ID", "18418682126"),
}
# לכל חשבון monday יש מפתח משלו
TOKENS = {"alphaomega": "MONDAY_API_TOKEN", "anycan": "MONDAY_ANYCAN_API_TOKEN"}
ANYCAN_DEFAULT_BOARD = "AnyCan Ai"


def _query(gql: str, variables: dict, account: str = "alphaomega") -> dict:
    env = TOKENS.get(account, TOKENS["alphaomega"])
    token = os.environ.get(env, "")
    if not token:
        raise RuntimeError(f"monday של {account} עדיין לא מחובר (חסר {env} ב-Render)")
    r = requests.post(API, json={"query": gql, "variables": variables},
                      headers={"Authorization": token, "Content-Type": "application/json"}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(str(data["errors"])[:300])
    return data["data"]


def get_monday_items(search: str = "", limit: int = 30, board: str = "alphacare") -> str:
    """מחזיר משימות ובקשות מלוח ה-monday של Alpha Omega (AlphaCare Marketing & Campaign ideas and requests).
    search = מילה לסינון (שם משימה, סטטוס, אחראי) — ריק מחזיר את המשימות האחרונות.
    limit = כמה משימות לכל היותר (עד 100)."""
    if board not in BOARDS and not str(board).isdigit():
        return get_anycan_monday_items(search, limit, board)
    board_id = BOARDS.get(board, board)
    gql = """query ($ids: [ID!], $limit: Int!) {
      boards(ids: $ids) { name items_page(limit: $limit) { items {
        id name updated_at group { title } column_values { column { title } text }
      } } } }"""
    data = _query(gql, {"ids": [board_id], "limit": max(1, min(int(limit), 100))})
    return _format_board(data.get("boards") or [], search)


def _format_board(boards: list, search: str) -> str:
    if not boards:
        return "לא מצאתי את הלוח ב-monday."
    rows = []
    s = (search or "").strip().lower()
    for it in boards[0]["items_page"]["items"]:
        cols = "; ".join(f"{c['column']['title']}: {c['text']}" for c in it["column_values"] if c.get("text"))
        line = f"- {it['name']} [{it['group']['title']}] {cols} (עודכן {it['updated_at'][:10]})"
        if not s or s in line.lower():
            rows.append(line)
    if not rows:
        return f"אין משימות שמתאימות ל-'{search}' בלוח {boards[0]['name']}."
    return (f"<monday_data>\nלוח: {boards[0]['name']}\n" + "\n".join(rows[:60]) + "\n</monday_data>")


def _anycan_boards() -> list:
    data = _query("query { boards(limit: 100, state: active) { id name type } }", {}, "anycan")
    return [b for b in data.get("boards") or [] if b.get("type") in (None, "board")]


def get_anycan_monday_items(search: str = "", limit: int = 30, board: str = ANYCAN_DEFAULT_BOARD) -> str:
    """מחזיר פריטים מה-monday של AnyCan Tech (החשבון של יוסי, 'מנדיי anycan.ai') — לידים, מרפאות, אנשי קשר, תקציב, מלאי.
    board = שם הלוח: 'AnyCan Ai' (ברירת מחדל), 'Budget', 'Inventory'. 'list' = רשימת כל הלוחות בחשבון.
    search = מילה לסינון (שם, קבוצה, סטטוס, אחראי, מדינה) — ריק מחזיר את הפריטים הראשונים.
    limit = כמה פריטים לכל היותר (עד 100)."""
    boards = _anycan_boards()
    want = (board or ANYCAN_DEFAULT_BOARD).strip().lower()
    if want == "list":
        return "<monday_data>\nהלוחות ב-monday של AnyCan:\n" + "\n".join(f"- {b['name']}" for b in boards) + "\n</monday_data>"
    match = ([b for b in boards if b["name"].strip().lower() == want]
             or [b for b in boards if want in b["name"].lower()])
    if not match:
        return f"לא מצאתי לוח בשם '{board}' ב-monday של AnyCan. הלוחות שיש: " + ", ".join(b["name"] for b in boards)
    gql = """query ($ids: [ID!], $limit: Int!) {
      boards(ids: $ids) { name items_page(limit: $limit) { items {
        id name updated_at group { title } column_values { column { title } text }
      } } } }"""
    data = _query(gql, {"ids": [match[0]["id"]], "limit": max(1, min(int(limit), 100))}, "anycan")
    return _format_board(data.get("boards") or [], search)


def get_monday_updates(account: str = "anycan", search: str = "", limit: int = 20) -> str:
    """מחזיר את העדכונים והפוסטים האחרונים שנכתבו ב-monday (מי כתב, מתי, על איזה פריט ומה נכתב) — מהחדש לישן.
    account = 'anycan' (ה-monday של AnyCan Tech, ברירת מחדל) או 'alphaomega' (ה-monday של Alpha Omega).
    search = מילה לסינון (שם כותב, שם פריט או מילה מהתוכן). limit = כמה עדכונים לכל היותר (עד 50).
    השתמשי כשיוסי שואל 'מה התעדכן במנדיי', 'מי כתב מה', 'מה חדש בלוח'."""
    account = account if account in TOKENS else "anycan"
    gql = """query ($limit: Int!) { updates(limit: $limit) {
      id text_body created_at creator { name } item { name board { name } } replies { text_body creator { name } }
    } }"""
    data = _query(gql, {"limit": max(1, min(int(limit), 50))}, account)
    s = (search or "").strip().lower()
    rows = []
    for u in data.get("updates") or []:
        item = u.get("item") or {}
        where = item.get("name") or "פריט שנמחק"
        if (item.get("board") or {}).get("name"):
            where += f" (לוח {item['board']['name']})"
        who = (u.get("creator") or {}).get("name") or "לא ידוע"
        body = " ".join((u.get("text_body") or "").split())[:400]
        line = f"- {(u.get('created_at') or '')[:10]} | {who} | {where}: {body}"
        for r in u.get("replies") or []:
            line += f"\n    ↳ {(r.get('creator') or {}).get('name') or 'לא ידוע'}: {' '.join((r.get('text_body') or '').split())[:200]}"
        if not s or s in line.lower():
            rows.append(line)
    if not rows:
        return "אין עדכונים חדשים ב-monday." if not s else f"אין עדכונים שמתאימים ל-'{search}'."
    return "<monday_data>\nעדכונים אחרונים ב-monday (" + account + "):\n" + "\n".join(rows) + "\n</monday_data>"


MONDAY_TOOLS = [get_monday_items, get_anycan_monday_items, get_monday_updates]
