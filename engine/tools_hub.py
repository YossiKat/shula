"""ייבוא ה-Content Hub של Alpha Omega (סטוריז, סרטונים ופוסטים) לתוך ה-monday של AnyCan.
Claude מוריד את הפריטים מהלוח של Alpha Omega לגיליון בדרייב, ושולה מכניסה אותם לקבוצה
"🎬 Content Hub" בלוח Supermetrics Campaign Reporting — פריט אחד לכל פריט, עם כל העמודות שיש בהן מידע.
פריט שכבר יובא (לפי מזהה הפריט באלפא אומגה) לא מיובא שוב.
כשיש מפתח של אלפא אומגה, sync_content_hub קוראת ישר מהלוח שלהם כל שעה ומעדכנת חדשים ושינויים."""
import json
import os
import re

import tools_monday
import tools_posts

HUB_SHEET_ID = os.environ.get("AO_HUB_SHEET_ID", "1aSty9zdBdnld_chuhNmDJ8EDI0QWWQwoSczArDPRWeE")
HUB_GROUP = "🎬 Content Hub (מאלפא אומגה)"
ID_COL = "AO item id"
SYNC_COL = "AO updated"  # מתי הפריט עודכן לאחרונה באלפא אומגה — כך יודעים מה השתנה
AO_BOARD = os.environ.get("AO_HUB_BOARD_ID", "18418682126")
AO_GROUP = os.environ.get("AO_HUB_GROUP_ID", "group_mm4hxnhc")
SKIP_TYPES = {"subtasks", "file", "formula", "mirror", "board_relation", "dependency", "button", "auto_number",
              "creation_log", "last_updated", "item_id", "doc", "progress", "battery"}
DELETED = "🗑️ נמחק באלפא אומגה"
PEOPLE_AS_TEXT = " (אלפא אומגה)"  # אנשים מחשבון אחר נרשמים כטקסט
BATCH = 40
ALLOWED = {"status", "dropdown", "date", "timeline", "text", "long_text"}


def _rows() -> tuple[list[tuple[str, str]], list[list[str]]]:
    raw = tools_posts._csv_with_header(HUB_SHEET_ID)
    header, rows = raw[0], raw[1:]
    cols = []
    for h in header[2:]:
        title, _, kind = h.rpartition("|")
        cols.append((title or h, kind if kind in ALLOWED or kind == "people" else "text"))
    return cols, rows


def _value(kind: str, text: str):
    text = (text or "").strip()
    if not text:
        return None
    if kind == "status":
        return {"label": text[:100]}
    if kind == "dropdown":
        return {"labels": [t.strip() for t in text.split(",") if t.strip()][:10]}
    if kind == "date":
        m = re.match(r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{1,2}:\d{2}))?", text)
        if not m:
            return None
        return {"date": m.group(1), **({"time": m.group(2).zfill(5) + ":00"} if m.group(2) else {})}
    if kind == "timeline":
        d = re.findall(r"\d{4}-\d{2}-\d{2}", text)
        return {"from": d[0], "to": d[-1]} if d else None
    if kind == "long_text":
        return {"text": text[:5000]}
    return text[:2000]


def _ensure(board: dict, cols: list) -> tuple[str, dict]:
    """הקבוצה והעמודות בלוח; עמודה קיימת באותו שם ובאותו סוג משמשת שוב, אחרת נוצרת חדשה."""
    have = {(c["title"].strip().lower(), c["type"]): c["id"] for c in board["columns"]}
    by_title = {c["title"].strip().lower(): c for c in board["columns"]}
    ids = {}
    for title, kind in [(ID_COL, "text")] + cols:
        mk = "text" if kind == "people" else kind
        name = title + PEOPLE_AS_TEXT if kind == "people" else title
        key = (name.strip().lower(), "long_text" if mk == "long_text" else mk)
        cid = have.get(key)
        if not cid and name.strip().lower() in by_title:  # אותו שם, סוג אחר — עמודה נפרדת
            name = f"{name} · AO"
            cid = have.get((name.strip().lower(), mk))
        if not cid:
            cid = tools_monday._query(
                "mutation ($b: ID!, $t: String!, $k: ColumnType!) { create_column(board_id: $b, title: $t, column_type: $k) { id } }",
                {"b": board["id"], "t": name, "k": mk}, "anycan")["create_column"]["id"]
        ids[title] = (cid, "text" if kind == "people" else mk)
    group = next((g["id"] for g in board["groups"] if g["title"].strip() == HUB_GROUP), None)
    if not group:
        group = tools_monday._query("mutation ($b: ID!, $n: String!) { create_group(board_id: $b, group_name: $n) { id } }",
                                    {"b": board["id"], "n": HUB_GROUP}, "anycan")["create_group"]["id"]
    return group, ids


def _imported(board_id: str, group_id: str, id_col: str, sync_col: str = "") -> dict:
    """{מזהה באלפא אומגה: {"id": מזהה הפריט ב-AnyCan, "updated": מתי עודכן באלפא אומגה כשהועתק}}."""
    ids = f'"{id_col}"' + (f', "{sync_col}"' if sync_col else "")
    fields = "id column_values(ids: [%s]) { id text }" % ids
    q = "query ($b: [ID!], $g: [String!]) { boards(ids: $b) { groups(ids: $g) { items_page(limit: 500) { cursor items { %s } } } } }" % fields
    page = tools_monday._query(q, {"b": [board_id], "g": [group_id]}, "anycan")["boards"][0]["groups"][0]["items_page"]
    out = {}
    while True:
        for it in page["items"]:
            vals = {c["id"]: c.get("text") or "" for c in it["column_values"]}
            if vals.get(id_col):
                out[vals[id_col]] = {"id": it["id"], "updated": vals.get(sync_col, "")}
        if not page.get("cursor"):
            return out
        page = tools_monday._query("query ($c: String!) { next_items_page(cursor: $c, limit: 500) { cursor items { %s } } }" % fields,
                                   {"c": page["cursor"]}, "anycan")["next_items_page"]


def import_content_hub(limit: int = BATCH) -> str:
    """מייבאת את ה-Content Hub של Alpha Omega (סטוריז, סרטונים ופוסטים) לקבוצה '🎬 Content Hub (מאלפא אומגה)'
    בלוח Supermetrics Campaign Reporting ב-monday של AnyCan, עם כל העמודות: סטטוסים, פלטפורמה, תאריכים, קהל, תוכן הפוסט ועוד.
    פריט שכבר יובא לא מיובא שוב. עד 40 פריטים בכל פעם — אם נשארו, לבקש שוב ('המשך ייבוא קונטנט').
    השתמשי כשיוסי מבקש לייבא את הקונטנט האב / Content Hub מאלפא אומגה."""
    cols, rows = _rows()
    board = tools_posts._board()
    group, ids = _ensure(board, cols)
    seen = _imported(board["id"], group, ids[ID_COL][0])
    todo = [r for r in rows if r and r[0].strip() and r[0].strip() not in seen]
    done = 0
    for r in todo[:max(1, min(int(limit), 100))]:
        r = r + [""] * (2 + len(cols) - len(r))
        values = {ids[ID_COL][0]: r[0].strip()}
        for (title, kind), text in zip(cols, r[2:]):
            v = _value(ids[title][1], text)
            if v is not None:
                values[ids[title][0]] = v
        tools_monday._query(
            "mutation ($b: ID!, $g: String!, $n: String!, $v: JSON) "
            "{ create_item(board_id: $b, group_id: $g, item_name: $n, column_values: $v, create_labels_if_missing: true) { id } }",
            {"b": board["id"], "g": group, "n": (r[1] or "פריט")[:250], "v": json.dumps(values, ensure_ascii=False)}, "anycan")
        done += 1
    left = len(todo) - done
    return (f"יובאו {done} פריטים מה-Content Hub של אלפא אומגה ללוח {board['name']} (מתוך {len(rows)})."
            + (f" נשארו עוד {left} — בקש 'המשך ייבוא קונטנט'." if left else " הכול יובא."))


def _ao_items() -> tuple[list, list]:
    """הפריטים בקבוצת ה-Content Hub בלוח של אלפא אומגה (קריאה בלבד, עם המפתח של אלפא אומגה)."""
    fields = "id name updated_at column_values { id type text value column { title } }"
    page = tools_monday._query(
        "query ($b: [ID!], $g: [String!]) { boards(ids: $b) { groups(ids: $g) { items_page(limit: 100) { cursor items { %s } } } } }" % fields,
        {"b": [AO_BOARD], "g": [AO_GROUP]}, "alphaomega")["boards"][0]["groups"][0]["items_page"]
    items = []
    while True:
        items += page["items"]
        if not page.get("cursor"):
            break
        page = tools_monday._query("query ($c: String!) { next_items_page(cursor: $c, limit: 100) { cursor items { %s } } }" % fields,
                                   {"c": page["cursor"]}, "alphaomega")["next_items_page"]
    cols = []
    for it in items:
        for c in it["column_values"]:
            key = (c["column"]["title"], c["type"])
            if c["type"] not in SKIP_TYPES and (c.get("text") or "").strip() and key not in cols:
                cols.append(key)
    return cols, items


def _ao_value(kind: str, c: dict):
    """ערך לכתיבה ב-AnyCan. תאריכים נלקחים מהערך הגולמי (UTC) כדי שהשעה לא תזוז."""
    if kind in ("date", "timeline") and c.get("value"):
        try:
            raw = json.loads(c["value"])
        except (TypeError, ValueError):
            raw = None
        if kind == "date" and raw and raw.get("date"):
            return {"date": raw["date"], **({"time": raw["time"]} if raw.get("time") else {})}
        if kind == "timeline" and raw and raw.get("from"):
            return {"from": raw["from"], "to": raw.get("to") or raw["from"]}
    return _value(kind, c.get("text") or "")


def sync_content_hub(limit: int = 150) -> str:
    """מסנכרנת את ה-Content Hub של אלפא אומגה עם ההעתק ב-monday של AnyCan (לוח Supermetrics Campaign Reporting):
    פריט חדש באלפא אומגה נוסף, פריט שהשתנה מתעדכן, ופריט שנמחק שם מסומן 'נמחק באלפא אומגה' (לא נמחק אצל יוסי).
    רץ לבד כל שעה. השתמשי כשיוסי מבקש 'תסנכרני את הקונטנט האב' או שואל אם הוא מעודכן."""
    if not os.environ.get(tools_monday.TOKENS["alphaomega"], "").strip():
        return "אין עדיין מפתח של המנדיי של אלפא אומגה (MONDAY_API_TOKEN ב-Render) — הסנכרון האוטומטי לא פועל."
    cols, items = _ao_items()
    board = tools_posts._board()
    group, ids = _ensure(board, cols + [(SYNC_COL, "text")])
    have = _imported(board["id"], group, ids[ID_COL][0], ids[SYNC_COL][0])
    added = changed = marked = 0
    present = set()
    for it in items:
        present.add(it["id"])
        mine = have.get(it["id"])
        if mine and mine["updated"] == it["updated_at"]:
            continue
        if added + changed >= limit:
            break
        values = {ids[ID_COL][0]: it["id"], ids[SYNC_COL][0]: it["updated_at"]}
        for c in it["column_values"]:
            key = c["column"]["title"]
            if (key, c["type"]) not in cols or key not in ids:
                continue
            v = _ao_value(ids[key][1], c)
            cid = ids[key][0]
            if v is not None:
                values[cid] = v
            elif mine:  # התרוקן באלפא אומגה → מתרוקן גם כאן
                values[cid] = {"text": "", "long_text": {"text": ""}}.get(ids[key][1], {})
        if mine:
            tools_monday._query(
                "mutation ($b: ID!, $i: ID!, $v: JSON!) "
                "{ change_multiple_column_values(board_id: $b, item_id: $i, column_values: $v, create_labels_if_missing: true) { id } }",
                {"b": board["id"], "i": mine["id"], "v": json.dumps({**values, "name": (it["name"] or "פריט")[:250]}, ensure_ascii=False)},
                "anycan")
            changed += 1
        else:
            tools_monday._query(
                "mutation ($b: ID!, $g: String!, $n: String!, $v: JSON) "
                "{ create_item(board_id: $b, group_id: $g, item_name: $n, column_values: $v, create_labels_if_missing: true) { id } }",
                {"b": board["id"], "g": group, "n": (it["name"] or "פריט")[:250],
                 "v": json.dumps({k: v for k, v in values.items() if v is not None}, ensure_ascii=False)}, "anycan")
            added += 1
    for ao_id, mine in have.items():
        if ao_id not in present and mine["updated"] != DELETED and len(items):
            tools_monday._query(
                "mutation ($b: ID!, $i: ID!, $v: JSON!) { change_multiple_column_values(board_id: $b, item_id: $i, column_values: $v) { id } }",
                {"b": board["id"], "i": mine["id"], "v": json.dumps({ids[SYNC_COL][0]: DELETED}, ensure_ascii=False)}, "anycan")
            marked += 1
    if not (added or changed or marked):
        return "ה-Content Hub מעודכן — אין שינויים באלפא אומגה."
    return f"Content Hub: {added} חדשים, {changed} עודכנו, {marked} סומנו כנמחקים באלפא אומגה."


HUB_TOOLS = [import_content_hub, sync_content_hub]
