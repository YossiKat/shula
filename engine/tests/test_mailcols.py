from datetime import date

import tools_mailcols


def _fake(monkeypatch, rows, items):
    calls = []

    def query(gql, variables, account="alphaomega"):
        assert account == "anycan"  # רק ה-monday של AnyCan
        calls.append((gql.split("{", 1)[1].split("(")[0].strip() if gql.lstrip().startswith("mutation") else "query", variables))
        if "items(ids" in gql:
            return {"items": [items[i] for i in variables["ids"] if i in items]}
        if "create_column" in gql:
            return {"create_column": {"id": "next_step"}}
        return {}

    monkeypatch.setattr(tools_mailcols, "_rows", lambda: [["head"]] + rows)
    monkeypatch.setattr(tools_mailcols.tools_monday, "_query", query)
    return calls


def _item(i, updates=(), cols=("Stage", "Priority", "Date")):
    return {"id": i, "name": "Rober Shehadeh", "board": {"id": "b1"},
            "column_values": [{"id": c.lower(), "type": "status", "column": {"title": c}} for c in cols],
            "updates": [{"text_body": u} for u in updates]}


TODAY = date.today().isoformat()


def test_change_is_applied_and_explained(monkeypatch):
    calls = _fake(monkeypatch, [["c1", TODAY, "111", "Rober", "Stage", "Waiting For Respopnse", "מייל 19.11"]],
                  {"111": _item("111")})
    out = tools_mailcols.apply_mail_changes()
    assert "נכנסו ל-monday 1" in out
    sets = [v for k, v in calls if k == "change_simple_column_value"]
    assert sets == [{"b": "b1", "i": "111", "c": "stage", "v": "Waiting For Respopnse"}]
    upd = [v for k, v in calls if k == "create_update"][0]
    assert "🔧 #c1" in upd["b"] and "מייל 19.11" in upd["b"]


def test_change_already_in_the_item_is_not_repeated(monkeypatch):
    calls = _fake(monkeypatch, [["c1", TODAY, "111", "Rober", "Stage", "Done", ""]],
                  {"111": _item("111", updates=["🔧 Stage ← Done\n🔧 #c1"])})
    tools_mailcols.apply_mail_changes()
    assert not [k for k, _ in calls if k != "query"]


def test_next_step_column_is_created_once(monkeypatch):
    calls = _fake(monkeypatch, [["c2", TODAY, "111", "Rober", "👉 הצעד הבא", "לחכות לתשובה עד 26.11", "מייל"]],
                  {"111": _item("111")})
    tools_mailcols.apply_mail_changes()
    kinds = [k for k, _ in calls]
    assert kinds.count("create_column") == 1 and "change_simple_column_value" in kinds


def test_unknown_columns_and_old_rows_are_ignored(monkeypatch):
    calls = _fake(monkeypatch, [["c3", TODAY, "111", "Rober", "Owner", "x", ""],
                                ["c4", "2020-01-01", "111", "Rober", "Stage", "Done", ""]],
                  {"111": _item("111")})
    tools_mailcols.apply_mail_changes()
    assert not [k for k, _ in calls if k != "query"]


def test_preview_changes_nothing(monkeypatch):
    calls = _fake(monkeypatch, [["c5", TODAY, "111", "Rober", "Priority", "High", "מייל"]], {"111": _item("111")})
    out = tools_mailcols.apply_mail_changes(preview=True)
    assert "Priority ← High" in out
    assert not [k for k, _ in calls if k != "query"]
