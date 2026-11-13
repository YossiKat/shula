import json

import tools_hub
import tools_monday
import tools_posts


def _fake(monkeypatch, columns, groups=(), imported=()):
    calls = []
    board = {"id": "88", "name": "Supermetrics Campaign Reporting", "columns": list(columns), "groups": list(groups)}
    monkeypatch.setattr(tools_posts, "_board", lambda name="": board)
    monkeypatch.setattr(tools_hub, "_imported", lambda b, g, c, sc="": {i: {"id": "x" + i, "updated": "t"} for i in imported})

    def query(gql, variables, account="alphaomega"):
        assert account == "anycan"
        kind = gql.split("{")[1].split("(")[0].strip()
        calls.append((kind, variables))
        if kind == "create_column":
            return {"create_column": {"id": "c_" + variables["t"]}}
        if kind == "create_group":
            return {"create_group": {"id": "ghub"}}
        return {"create_item": {"id": "1"}}
    monkeypatch.setattr(tools_monday, "_query", query)
    return calls


HEADER = ["AO item id", "Name", "Status|status", "Platform|dropdown", "Date|date", "Campagin Timeline|timeline",
          "Owner|people", "Post Content|long_text", "Target Audience|text"]
ROWS = [["111", "Captain Steady — The First Morning", "Done", "Instagram, Facebook", "2026-10-29 17:00",
         "2026-10-30 - 2026-11-07", "Yossi Kat", "טקסט הפוסט", "Global"],
        ["222", "Old item", "", "", "", "", "", "", ""]]


def test_hub_items_are_imported_with_their_columns(monkeypatch):
    calls = _fake(monkeypatch, columns=[{"id": "status", "title": "Status", "type": "status"},
                                        {"id": "date4", "title": "Date", "type": "text"}], imported={"222"})
    monkeypatch.setattr(tools_posts, "_csv_with_header", lambda sid: [HEADER] + ROWS)
    out = tools_hub.import_content_hub()
    made = [c[1]["t"] for c in calls if c[0] == "create_column"]
    assert made == ["AO item id", "Platform", "Date · AO", "Campagin Timeline", "Owner (אלפא אומגה)", "Post Content", "Target Audience"]
    assert ("create_group", {"b": "88", "n": tools_hub.HUB_GROUP}) in calls
    item = [c[1] for c in calls if c[0] == "create_item"]
    assert len(item) == 1 and item[0]["n"] == "Captain Steady — The First Morning" and item[0]["g"] == "ghub"
    v = json.loads(item[0]["v"])
    assert v["c_AO item id"] == "111" and v["status"] == {"label": "Done"}
    assert v["c_Platform"] == {"labels": ["Instagram", "Facebook"]}
    assert v["c_Date · AO"] == {"date": "2026-10-29", "time": "17:00:00"}
    assert v["c_Campagin Timeline"] == {"from": "2026-10-30", "to": "2026-11-07"}
    assert v["c_Owner (אלפא אומגה)"] == "Yossi Kat" and v["c_Post Content"] == {"text": "טקסט הפוסט"}
    assert "יובאו 1 פריטים" in out and "הכול יובא" in out


def test_hub_import_stops_at_the_limit(monkeypatch):
    calls = _fake(monkeypatch, columns=[], groups=[{"id": "ghub", "title": tools_hub.HUB_GROUP}])
    monkeypatch.setattr(tools_posts, "_csv_with_header", lambda sid: [HEADER] + ROWS)
    out = tools_hub.import_content_hub(limit=1)
    assert [c[0] for c in calls].count("create_item") == 1 and "נשארו עוד 1" in out
    assert "create_group" not in [c[0] for c in calls]


def _cv(id, kind, text="", value=None):
    return {"id": id, "type": kind, "text": text, "value": value}


FIELDS = {"date4": {"an": "pd", "an_kind": "date", "ao_kind": "date", "ao_only": False},
          "status": {"an": "s1", "an_kind": "status", "ao_kind": "status", "ao_only": False},
          "person": {"an": "own", "an_kind": "text", "ao_kind": "people", "ao_only": True}}


def _item(name, date=None, status="", owner=""):
    return {"name": name, "column_values": [
        _cv("pd", "date", date or "", json.dumps({"date": date}) if date else None), _cv("s1", "status", status),
        _cv("own", "text", owner), _cv("date4", "date", date or "", json.dumps({"date": date}) if date else None),
        _cv("status", "status", status), _cv("person", "people", owner)]}


def test_first_sync_yossi_wins_but_never_clears_alpha_omega():
    an = _item("Captain Steady", date="2026-11-18", status="")
    ao = _item("Captain Steady", date="2026-07-03", status="Waiting for Confirmation", owner="Yossi Kat")
    to_an, to_ao, state = tools_hub._merge(FIELDS, an, ao, {})
    assert to_ao == {"date4": {"date": "2026-11-18"}}
    assert to_an == {"s1": {"label": "Waiting for Confirmation"}, "own": "Yossi Kat"}
    assert state["date4"] == tools_hub._fp("2026-11-18") and "person" not in state


def test_later_change_on_either_side_moves_across():
    base = {"name": tools_hub._fp("A"), "date4": tools_hub._fp("2026-11-18"), "status": tools_hub._fp("Draft")}
    an = _item("A", date="2026-11-20", status="Draft")      # יוסי הזיז תאריך
    ao = _item("A", date="2026-11-18", status="Done")       # הצוות שינה סטטוס
    to_an, to_ao, state = tools_hub._merge(FIELDS, an, ao, base)
    assert to_ao == {"date4": {"date": "2026-11-20"}}
    assert to_an == {"s1": {"label": "Done"}}
    assert state["status"] == tools_hub._fp("Done")


def test_values_round_trip():
    assert tools_hub._write("date", "2026-10-29 17:00:00") == {"date": "2026-10-29", "time": "17:00:00"}
    assert tools_hub._norm("date", _cv("x", "date", "", '{"date":"2026-10-29","time":"17:00:00"}')) == "2026-10-29 17:00:00"
    assert tools_hub._write("timeline", "2026-10-30|2026-11-07") == {"from": "2026-10-30", "to": "2026-11-07"}
    assert tools_hub._write("dropdown", "Facebook, LinkedIn") == {"labels": ["Facebook", "LinkedIn"]}
    assert tools_hub._write("status", "") == {}


def _two_way(monkeypatch, mine, hub, ao_extra=(), updates=None):
    monkeypatch.setenv("MONDAY_API_TOKEN", "ao")
    board = {"id": "88", "name": "Social media schedule",
             "columns": [{"id": "s1", "title": "Status", "type": "status"}, {"id": "pd", "title": "Publish Date", "type": "date"},
                         {"id": "aid", "title": "AO item id", "type": "text"}, {"id": "aup", "title": "AO updated", "type": "text"},
                         {"id": "st", "title": "Sync state", "type": "long_text"}],
             "groups": [{"id": "ghub", "title": tools_hub.HUB_GROUP}, {"id": "gposts", "title": "📣 פוסטים ושיתופים"}]}
    monkeypatch.setattr(tools_posts, "_board", lambda name="": board)
    monkeypatch.setattr(tools_hub, "_ao_items", lambda: ([("Status", "status"), ("Date", "date")], hub))
    calls = []
    updates = updates or {}

    def query(gql, v, account="alphaomega"):
        kind = gql.split("{")[1].split("(")[0].strip()
        calls.append((kind, v, account))
        if kind == "boards" and "columns { id title type }" in gql:
            return {"boards": [{"columns": [{"id": "status", "title": "Status", "type": "status"},
                                            {"id": "date4", "title": "Date", "type": "date"}]}]}
        if kind == "boards" and "groups { id title }" in gql:
            return {"boards": [{"groups": [{"id": "group_mm4hxnhc", "title": "🎬 Content Hub"}]}]}
        if kind == "boards":
            return {"boards": [{"items_page": {"cursor": None, "items": mine}}]}
        if kind == "items" and "updates" in gql:
            return {"items": [{"id": i, "updates": updates.get(i, [])} for i in v["i"]]}
        if kind == "items":
            return {"items": [it for it in ao_extra if it["id"] in v["i"]]}
        if kind == "create_group":
            return {"create_group": {"id": "gnew"}}
        if kind == "create_item":
            return {"create_item": {"id": "new1"}}
        return {kind: {"id": "1"}}
    monkeypatch.setattr(tools_monday, "_query", query)
    return calls


def _row(id, name, group, ao_id="", date=None, status="", state=""):
    return {"id": id, "name": name, "updated_at": "t", "group": {"id": group, "title": "📣 פוסטים ושיתופים" if group == "gposts" else tools_hub.HUB_GROUP},
            "column_values": [_cv("aid", "text", ao_id), _cv("aup", "text", ""), _cv("st", "long_text", state),
                              _cv("s1", "status", status), _cv("pd", "date", date or "", json.dumps({"date": date}) if date else None)]}


def _hubitem(id, name, date=None, status=""):
    return {"id": id, "name": name, "updated_at": "u" + id, "group": {"id": "group_mm4hxnhc", "title": "🎬"},
            "column_values": [_cv("date4", "date", date or "", json.dumps({"date": date}) if date else None), _cv("status", "status", status)]}


def test_two_way_sync_sends_dates_new_items_and_updates(monkeypatch):
    mine = [_row("a1", "Captain Steady", "ghub", ao_id="111", date="2026-11-18", status="Draft"),
            _row("a2", "פייסבוק · שיתוף", "gposts")]
    hub = [_hubitem("111", "Captain Steady", date="2026-07-03", status="Draft"), _hubitem("222", "חדש באלפא")]
    ups = {"a1": [{"id": "u1", "text_body": "🎬 פוסט מוכן: סרטון", "body": "<p>🎬 פוסט מוכן: סרטון</p>", "creator": {"name": "Yossi Kat"},
                   "replies": [{"text_body": "קישור", "body": "<p>קישור</p>", "creator": {"name": "Yossi Kat"}}]}]}
    calls = _two_way(monkeypatch, mine, hub, updates=ups)
    out = tools_hub.sync_content_hub()
    writes = [(c[0], c[1], c[2]) for c in calls if c[0] in ("create_item", "change_multiple_column_values", "create_group", "create_update")]
    # פריט חדש באלפא אומגה נוצר אצל יוסי
    assert writes[0][0] == "create_item" and writes[0][2] == "anycan" and json.loads(writes[0][1]["v"])["aid"] == "222"
    # קבוצת השיתופים נוצרת באלפא אומגה והפריט נשלח לשם, והמזהה נרשם אצל יוסי
    assert ("create_group", {"b": tools_hub.AO_BOARD, "n": "📣 פוסטים ושיתופים"}, "alphaomega") in writes
    assert any(w[0] == "create_item" and w[2] == "alphaomega" and w[1]["g"] == "gnew" for w in writes)
    assert any(w[0] == "change_multiple_column_values" and w[2] == "anycan" and json.loads(w[1]["v"]).get("aid") == "new1" for w in writes)
    # התאריך של יוסי עובר לאלפא אומגה
    ao_set = [json.loads(w[1]["v"]) for w in writes if w[0] == "change_multiple_column_values" and w[2] == "alphaomega"]
    assert ao_set == [{"date4": {"date": "2026-11-18"}}]
    # העדכון מועתק לאלפא אומגה עם התגובה ועם סימון
    up = [w for w in writes if w[0] == "create_update"]
    assert len(up) == 1 and up[0][2] == "alphaomega" and up[0][1]["i"] == "111"
    assert up[0][1]["b"].startswith("<p>🔁 מ-AnyCan") and "קישור" in up[0][1]["b"]
    assert "1 חדשים אצלך, 1 חדשים באלפא אומגה, 1 פריטים עודכנו, 1 עדכונים הועתקו" in out


def test_two_way_sync_does_not_copy_an_update_twice(monkeypatch):
    mine = [_row("a1", "X", "ghub", ao_id="111", status="Draft")]
    hub = [_hubitem("111", "X", status="Draft")]
    ups = {"a1": [{"id": "u1", "text_body": "שלום", "body": "<p>שלום</p>", "creator": {"name": "Y"}, "replies": []}],
           "111": [{"id": "u2", "text_body": "🔁 מ-AnyCan · Y שלום", "body": "", "creator": {"name": "Y"}, "replies": []}]}
    calls = _two_way(monkeypatch, mine, hub, updates=ups)
    tools_hub.sync_content_hub()
    assert "create_update" not in [c[0] for c in calls]


def test_preview_writes_nothing(monkeypatch):
    mine = [_row("a1", "X", "ghub", ao_id="111", date="2026-11-18")]
    calls = _two_way(monkeypatch, mine, [_hubitem("111", "X", date="2026-07-03")])
    out = tools_hub.sync_content_hub(preview=True)
    assert not [c for c in calls if c[0].startswith(("create", "change"))] and out.startswith("תצוגה מקדימה")


def test_live_sync_without_the_alpha_omega_key_explains(monkeypatch):
    monkeypatch.delenv("MONDAY_API_TOKEN", raising=False)
    assert "MONDAY_API_TOKEN" in tools_hub.sync_content_hub()
