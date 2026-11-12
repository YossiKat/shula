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


def _ao(id, name, updated, status="Done", date_value=None):
    cv = [{"id": "status", "type": "status", "text": status, "value": None, "column": {"title": "Status"}},
          {"id": "date4", "type": "date", "text": "2026-10-29 19:00" if date_value else "",
           "value": date_value, "column": {"title": "Date"}},
          {"id": "f1", "type": "formula", "text": "123", "value": None, "column": {"title": "Score"}}]
    return {"id": id, "name": name, "updated_at": updated, "column_values": cv}


def _sync_fake(monkeypatch, ao, have):
    monkeypatch.setenv("MONDAY_API_TOKEN", "ao")
    calls = _fake(monkeypatch, columns=[{"id": "s1", "title": "Status", "type": "status"},
                                        {"id": "d1", "title": "Date", "type": "date"},
                                        {"id": "aid", "title": "AO item id", "type": "text"},
                                        {"id": "aup", "title": "AO updated", "type": "text"}],
                  groups=[{"id": "ghub", "title": tools_hub.HUB_GROUP}])
    monkeypatch.setattr(tools_hub, "_ao_items", lambda: ([("Status", "status"), ("Date", "date")], ao))
    monkeypatch.setattr(tools_hub, "_imported", lambda b, g, c, sc="": have)
    return calls


def test_live_sync_adds_new_updates_changed_and_marks_deleted(monkeypatch):
    ao = [_ao("1", "חדש", "2026-11-12T10:00:00Z", date_value='{"date":"2026-10-29","time":"17:00:00"}'),
          _ao("2", "שונה", "2026-11-12T11:00:00Z", status="Working on it"),
          _ao("3", "לא שונה", "2026-11-01T09:00:00Z")]
    have = {"2": {"id": "x2", "updated": "2026-11-10T08:00:00Z"}, "3": {"id": "x3", "updated": "2026-11-01T09:00:00Z"},
            "9": {"id": "x9", "updated": "2026-10-01T09:00:00Z"}}
    calls = _sync_fake(monkeypatch, ao, have)
    out = tools_hub.sync_content_hub()
    kinds = [c[0] for c in calls]
    assert kinds == ["create_item", "change_multiple_column_values", "change_multiple_column_values"]
    new = json.loads(calls[0][1]["v"])
    assert new["d1"] == {"date": "2026-10-29", "time": "17:00:00"} and new["s1"] == {"label": "Done"}
    assert new["aid"] == "1" and new["aup"] == "2026-11-12T10:00:00Z" and "Score" not in str(new)
    upd = json.loads(calls[1][1]["v"])
    assert calls[1][1]["i"] == "x2" and upd["s1"] == {"label": "Working on it"} and upd["d1"] == {} and upd["name"] == "שונה"
    assert calls[2][1]["i"] == "x9" and json.loads(calls[2][1]["v"]) == {"aup": tools_hub.DELETED}
    assert out == "Content Hub: 1 חדשים, 1 עודכנו, 1 סומנו כנמחקים באלפא אומגה."


def test_live_sync_without_the_alpha_omega_key_explains(monkeypatch):
    monkeypatch.delenv("MONDAY_API_TOKEN", raising=False)
    assert "MONDAY_API_TOKEN" in tools_hub.sync_content_hub()
