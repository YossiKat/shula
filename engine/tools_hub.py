"""ייבוא ה-Content Hub של Alpha Omega (סטוריז, סרטונים ופוסטים) לתוך ה-monday של AnyCan.
Claude מוריד את הפריטים מהלוח של Alpha Omega לגיליון בדרייב, ושולה מכניסה אותם לקבוצה
"🎬 Content Hub" בלוח Supermetrics Campaign Reporting — פריט אחד לכל פריט, עם כל העמודות שיש בהן מידע.
פריט שכבר יובא (לפי מזהה הפריט באלפא אומגה) לא מיובא שוב.
כשיש מפתח של אלפא אומגה, sync_content_hub קוראת ישר מהלוח שלהם כל שעה ומעדכנת חדשים ושינויים."""
import hashlib
import json
import os
import re
import threading

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


ITEM_FIELDS = "id name updated_at group { id title } column_values { id type text value }"
KINDS = {"status", "dropdown", "date", "timeline", "text", "long_text", "numbers"}
STATE_COL = "Sync state"  # מה היה בכל שדה בסנכרון האחרון (טביעה קצרה) — כך יודעים איזה צד שינה
ALIASES = {"Date": "Publish Date"}  # עמודה באלפא אומגה ← העמודה המקבילה בלוח של יוסי
COPY_MARK = "🔁"
MAX_WRITES = 120   # פריטים שנכתבים בריצה אחת; השאר בשעה הבאה
MAX_UPDATES = 40   # עדכונים שמועתקים בריצה אחת
_lock = threading.Lock()


def _pages(gql: str, variables: dict, account: str, path) -> list:
    page = path(tools_monday._query(gql, variables, account))
    items = []
    while True:
        items += page["items"]
        if not page.get("cursor"):
            return items
        page = tools_monday._query("query ($c: String!) { next_items_page(cursor: $c, limit: 100) { cursor items { %s } } }" % ITEM_FIELDS,
                                   {"c": page["cursor"]}, account)["next_items_page"]


def _ao_items() -> tuple[list, list]:
    """הפריטים בקבוצת ה-Content Hub בלוח של אלפא אומגה, ורשימת העמודות שיש בהן מידע."""
    fields = ITEM_FIELDS.replace("value }", "value column { title } }")
    q = "query ($b: [ID!], $g: [String!]) { boards(ids: $b) { groups(ids: $g) { items_page(limit: 100) { cursor items { %s } } } } }" % fields
    page = tools_monday._query(q, {"b": [AO_BOARD], "g": [AO_GROUP]}, "alphaomega")["boards"][0]["groups"][0]["items_page"]
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


def _ao_by_ids(ids: list) -> dict:
    out = {}
    for i in range(0, len(ids), 100):
        data = tools_monday._query("query ($i: [ID!]) { items(ids: $i, limit: 100) { %s } }" % ITEM_FIELDS,
                                   {"i": ids[i:i + 100]}, "alphaomega")
        out.update({it["id"]: it for it in data.get("items") or []})
    return out


def _norm(kind: str, c: dict | None) -> str:
    """ערך אחיד להשוואה בין שני החשבונות."""
    if not c:
        return ""
    if kind in ("date", "timeline"):
        try:
            raw = json.loads(c.get("value") or "null") or {}
        except (TypeError, ValueError):
            raw = {}
        if kind == "date":
            return (raw["date"] + (" " + raw["time"] if raw.get("time") else "")) if raw.get("date") else ""
        return f"{raw['from']}|{raw.get('to') or raw['from']}" if raw.get("from") else ""
    return (c.get("text") or "").strip()


def _write(kind: str, s: str):
    """ערך לכתיבה ב-monday מתוך הערך האחיד; ריק = ניקוי."""
    if kind == "date":
        d, _, t = s.partition(" ")
        return {"date": d, **({"time": t} if t else {})} if s else {}
    if kind == "timeline":
        f, _, to = s.partition("|")
        return {"from": f, "to": to or f} if s else {}
    if kind == "status":
        return {"label": s[:100]} if s else {}
    if kind == "dropdown":
        return {"labels": [x.strip() for x in s.split(",") if x.strip()][:10]} if s else {}
    if kind == "long_text":
        return {"text": s[:5000]}
    return s[:2000]


def _fp(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:10]


def _merge(fields: dict, an: dict, ao: dict, state: dict) -> tuple[dict, dict, dict]:
    """השוואה שדה-שדה: מה שהשתנה בצד אחד מאז הסנכרון הקודם עובר לצד השני.
    שינוי בשני הצדדים (או פעם ראשונה) — הערך של יוסי גובר, ואם אצלו ריק נשאר הערך של אלפא אומגה.
    מחזירה (לכתוב ב-AnyCan, לכתוב באלפא אומגה, מצב חדש)."""
    to_an, to_ao, new = {}, {}, {}
    an_vals = {c["id"]: c for c in an["column_values"]}
    ao_vals = {c["id"]: c for c in ao["column_values"]}
    rows = [("name", "name", "text", "text", False)] + [(k, f["an"], f["an_kind"], f["ao_kind"], f["ao_only"]) for k, f in fields.items()]
    for key, an_id, an_kind, ao_kind, ao_only in rows:
        if key == "name":
            a, o = (an["name"] or "").strip(), (ao["name"] or "").strip()
        else:
            a, o = _norm(an_kind, an_vals.get(an_id)), _norm(ao_kind, ao_vals.get(key))
        if ao_only:  # אנשים מחשבון אחר — רק מאלפא אומגה ליוסי
            if a != o:
                to_an[an_id] = _write(an_kind, o)
            continue
        base = state.get(key)
        if a == o:
            win = a
        elif base and _fp(a) == base:
            win = o
        elif base and _fp(o) == base:
            win = a
        else:
            win = a or o
        if win != a:
            to_an[an_id] = win[:250] if key == "name" else _write(an_kind, win)
        if win != o:
            to_ao[key] = win[:250] if key == "name" else _write(ao_kind, win)
        new[key] = _fp(win)
    return to_an, to_ao, new


def _set(board_id: str, item_id: str, values: dict, account: str) -> None:
    tools_monday._query(
        "mutation ($b: ID!, $i: ID!, $v: JSON!) "
        "{ change_multiple_column_values(board_id: $b, item_id: $i, column_values: $v, create_labels_if_missing: true) { id } }",
        {"b": board_id, "i": item_id, "v": json.dumps(values, ensure_ascii=False)}, account)


def _create(board_id: str, group_id: str, name: str, values: dict, account: str) -> str:
    return tools_monday._query(
        "mutation ($b: ID!, $g: String!, $n: String!, $v: JSON) "
        "{ create_item(board_id: $b, group_id: $g, item_name: $n, column_values: $v, create_labels_if_missing: true) { id } }",
        {"b": board_id, "g": group_id, "n": (name or "פריט")[:250], "v": json.dumps(values, ensure_ascii=False)}, account)["create_item"]["id"]


def _fields(board: dict, ids: dict) -> dict:
    """העמודות המשותפות: {מזהה עמודה באלפא אומגה: העמודה המקבילה בלוח של יוסי}."""
    ao_cols = tools_monday._query("query ($b: [ID!]) { boards(ids: $b) { columns { id title type } } }",
                                  {"b": [AO_BOARD]}, "alphaomega")["boards"][0]["columns"]
    by_title = {}
    for c in ao_cols:
        if c["type"] in KINDS or c["type"] == "people":
            by_title.setdefault(c["title"].strip(), c)
    out, used = {}, set()
    for title, (cid, kind) in ids.items():
        ao = by_title.get(title)
        if ao and title not in (ID_COL, SYNC_COL, STATE_COL) and kind in KINDS:
            out[ao["id"]] = {"an": cid, "an_kind": kind, "ao_kind": ao["type"], "ao_only": ao["type"] == "people"}
            used.add(cid)
    for c in board["columns"]:  # עמודות של יוסי בשם זהה לעמודה באלפא אומגה (למשל 📊 Reach)
        ao = by_title.get(c["title"].strip())
        if ao and ao["id"] not in out and c["id"] not in used and ao["type"] in KINDS and c["type"] in KINDS:
            out[ao["id"]] = {"an": c["id"], "an_kind": c["type"], "ao_kind": ao["type"], "ao_only": False}
    return out


def _updates(ids: list, account: str) -> dict:
    out = {}
    q = ("query ($i: [ID!]) { items(ids: $i, limit: 25) { id updates(limit: 30) "
         "{ id text_body body creator { name } replies { text_body body creator { name } } } } }")
    for i in range(0, len(ids), 25):
        for it in tools_monday._query(q, {"i": ids[i:i + 25]}, account).get("items") or []:
            out[it["id"]] = it.get("updates") or []
    return out


def _key(text: str) -> str:
    return " ".join((text or "").split())[:150]


def _copy_updates(pairs: list, budget: int, preview: bool) -> int:
    """עדכונים (תגובות) שנכתבו בצד אחד ועוד לא הועתקו — מועתקים לפריט המקביל, עם סימון מאיפה הגיעו."""
    an_up = _updates([a for a, _ in pairs], "anycan")
    ao_up = _updates([o for _, o in pairs], "alphaomega")
    done = 0
    for an_id, ao_id in pairs:
        for src, dst, dst_id, account, where in ((an_up.get(an_id, []), ao_up.get(ao_id, []), ao_id, "alphaomega", "AnyCan"),
                                                   (ao_up.get(ao_id, []), an_up.get(an_id, []), an_id, "anycan", "אלפא אומגה")):
            there = [_key(u.get("text_body")) for u in dst]
            for u in reversed(src):  # מהישן לחדש
                k = _key(u.get("text_body"))
                if not k or k.startswith(COPY_MARK) or any(k in t for t in there):
                    continue
                if done >= budget:
                    return done
                done += 1
                if preview:
                    continue
                who = (u.get("creator") or {}).get("name") or ""
                body = f"<p>{COPY_MARK} מ-{where} · {who}</p>" + (u.get("body") or u.get("text_body") or "")
                for r in u.get("replies") or []:
                    body += f"<p>↳ {(r.get('creator') or {}).get('name') or ''}:</p>" + (r.get("body") or r.get("text_body") or "")
                tools_monday._query("mutation ($i: ID!, $b: String!) { create_update(item_id: $i, body: $b) { id } }",
                                    {"i": dst_id, "b": body}, account)
                there.append(k)
    return done


def sync_content_hub(limit: int = MAX_WRITES, preview: bool = False) -> str:
    """סנכרון בשני הכיוונים בין הלוח של יוסי ב-monday של AnyCan (Social media schedule / Content Hub) לבין
    הלוח AlphaCare Marketing של אלפא אומגה:
    • פריט חדש ב-Content Hub של אלפא אומגה נוסף אצל יוסי; פריט חדש אצל יוסי (בכל קבוצה) נוסף באלפא אומגה, בקבוצה באותו שם.
    • שינוי בשדה (שם, תאריך, סטטוס, ערוץ, תוכן ועוד) עובר לצד השני; כששני הצדדים שונים בפעם הראשונה — הערך של יוסי גובר.
    • עדכונים (תגובות) מועתקים בין שני הפריטים. פריט שנמחק באלפא אומגה מסומן אצל יוסי ולא נמחק.
    רץ לבד כל שעה. preview=True = רק לספור מה ישתנה, בלי לכתוב (כשיוסי מבקש 'תראי לי מה ישתנה').
    השתמשי כשיוסי מבקש 'תסנכרני עם אלפא אומגה' או שואל אם שני הלוחות מעודכנים."""
    if not os.environ.get(tools_monday.TOKENS["alphaomega"], "").strip():
        return "אין עדיין מפתח של המנדיי של אלפא אומגה (MONDAY_API_TOKEN ב-Render) — הסנכרון האוטומטי לא פועל."
    if not _lock.acquire(blocking=False):
        return "סנכרון עם אלפא אומגה כבר רץ עכשיו."
    try:
        return _sync(limit, preview)
    finally:
        _lock.release()


def _sync(limit: int, preview: bool) -> str:
    cols, hub = _ao_items()
    board = tools_posts._board()
    titles = {c["title"].strip().lower(): c for c in board["columns"]}
    alias = {t: titles[a.lower()] for t, a in ALIASES.items() if a.lower() in titles}
    group, ids = _ensure(board, [c for c in cols if c[0] not in alias] + [(SYNC_COL, "text"), (STATE_COL, "long_text")])
    for t, c in alias.items():
        ids[t] = (c["id"], c["type"])
    fields = _fields(board, ids)
    id_col, sync_col, state_col = ids[ID_COL][0], ids[SYNC_COL][0], ids[STATE_COL][0]

    mine = _pages("query ($b: [ID!]) { boards(ids: $b) { items_page(limit: 100) { cursor items { %s } } } }" % ITEM_FIELDS,
                  {"b": [board["id"]]}, "anycan", lambda d: d["boards"][0]["items_page"])
    val = lambda it, cid: next((c.get("text") or "" for c in it["column_values"] if c["id"] == cid), "").strip()
    paired, alone, fresh = {}, [], set()
    for it in mine:
        (paired.__setitem__(val(it, id_col), it) if val(it, id_col) else alone.append(it))
    ao = {it["id"]: it for it in hub}
    ao.update(_ao_by_ids([i for i in paired if i not in ao]))

    added = sent = changed = marked = writes = 0
    ao_groups = None
    # 1. חדש באלפא אומגה → אצל יוסי
    for ao_id, it in ao.items():
        if ao_id in paired or writes >= limit:
            continue
        values = {id_col: ao_id, sync_col: it["updated_at"]}
        to_an, _, state = _merge(fields, {"name": it["name"], "column_values": []}, it, {})
        values.update({k: v for k, v in to_an.items() if v not in ({}, "")})
        values[state_col] = {"text": json.dumps(state)}
        if not preview:
            _create(board["id"], group, it["name"], values, "anycan")
        added += 1
        writes += 1
    # 2. חדש אצל יוסי → באלפא אומגה, בקבוצה באותו שם
    for it in alone:
        if writes >= limit:
            break
        if not preview:
            if ao_groups is None:
                ao_groups = {g["title"].strip(): g["id"] for g in tools_monday._query(
                    "query ($b: [ID!]) { boards(ids: $b) { groups { id title } } }", {"b": [AO_BOARD]}, "alphaomega")["boards"][0]["groups"]}
            title = it["group"]["title"].strip()
            gid = AO_GROUP if it["group"]["id"] == group else ao_groups.get(title)
            if not gid:
                gid = tools_monday._query("mutation ($b: ID!, $n: String!) { create_group(board_id: $b, group_name: $n) { id } }",
                                          {"b": AO_BOARD, "n": title}, "alphaomega")["create_group"]["id"]
                ao_groups[title] = gid
            _, to_ao, state = _merge(fields, it, {"name": "", "column_values": []}, {})
            new_id = _create(AO_BOARD, gid, it["name"], {k: v for k, v in to_ao.items() if k != "name" and v not in ({}, "")}, "alphaomega")
            _set(board["id"], it["id"], {id_col: new_id, state_col: {"text": json.dumps(state)}}, "anycan")
            paired[new_id] = it
            fresh.add(new_id)
        sent += 1
        writes += 1
    # 3. פריטים משותפים — שדה-שדה
    pairs = []
    for ao_id, it in paired.items():
        if ao_id in fresh:  # נוצר עכשיו באלפא אומגה עם כל הערכים
            pairs.append((it["id"], ao_id))
            continue
        other = ao.get(ao_id)
        if not other:
            if val(it, sync_col) != DELETED and len(hub):
                if not preview:
                    _set(board["id"], it["id"], {sync_col: DELETED}, "anycan")
                marked += 1
            continue
        pairs.append((it["id"], ao_id))
        if writes >= limit:
            continue
        try:
            state = json.loads(val(it, state_col) or "{}")
        except ValueError:
            state = {}
        to_an, to_ao, new = _merge(fields, it, other, state)
        if not (to_an or to_ao) and new == state:
            continue
        if not preview:
            if to_ao:
                _set(AO_BOARD, ao_id, to_ao, "alphaomega")
            _set(board["id"], it["id"], {**to_an, sync_col: other["updated_at"], state_col: {"text": json.dumps(new)}}, "anycan")
        if to_an or to_ao:
            changed += 1
        writes += 1
    copied = _copy_updates(pairs, MAX_UPDATES, preview) if pairs else 0
    head = "תצוגה מקדימה (לא נכתב כלום): " if preview else ""
    if not (added or sent or changed or marked or copied):
        return head + "שני הלוחות מסונכרנים — אין שינויים."
    return (head + f"סנכרון עם אלפא אומגה: {added} חדשים אצלך, {sent} חדשים באלפא אומגה, {changed} פריטים עודכנו, "
            f"{copied} עדכונים הועתקו, {marked} סומנו כנמחקים באלפא אומגה."
            + (" נשארו עוד שינויים — ימשיכו בשעה הבאה." if writes >= limit else ""))


HUB_TOOLS = [import_content_hub, sync_content_hub]
