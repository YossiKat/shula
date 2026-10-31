"""כלי monday לשולה — קריאה בלבד מהלוח של Alpha Omega (AlphaCare Marketing & Campaign ideas and requests)."""
import os

import requests

API = "https://api.monday.com/v2"
BOARDS = {
    "alphacare": os.environ.get("MONDAY_BOARD_ID", "18418682126"),
}


def _query(gql: str, variables: dict) -> dict:
    token = os.environ.get("MONDAY_API_TOKEN", "")
    if not token:
        raise RuntimeError("monday עדיין לא מחובר (חסר MONDAY_API_TOKEN ב-Render)")
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
    board_id = BOARDS.get(board, board)
    gql = """query ($ids: [ID!], $limit: Int!) {
      boards(ids: $ids) { name items_page(limit: $limit) { items {
        id name updated_at group { title } column_values { column { title } text }
      } } } }"""
    data = _query(gql, {"ids": [board_id], "limit": max(1, min(int(limit), 100))})
    boards = data.get("boards") or []
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


MONDAY_TOOLS = [get_monday_items]
