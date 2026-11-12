import json

import tools_monday
import tools_posts


def _fake(monkeypatch, columns=(), groups=()):
    calls = []
    board = {"id": "77", "name": "AnyCan Ai", "columns": list(columns), "groups": list(groups)}
    monkeypatch.setattr(tools_monday, "_anycan_boards", lambda: [{"id": "77", "name": "AnyCan Ai", "type": "board"}])

    def query(gql, variables, account="alphaomega"):
        assert account == "anycan"
        if gql.startswith("query"):
            return {"boards": [board]}
        calls.append((gql.split("{")[1].split("(")[0].strip(), variables))
        return {"create_item": {"id": "900"}}
    monkeypatch.setattr(tools_monday, "_query", query)
    return calls


def test_setup_creates_only_what_is_missing(monkeypatch):
    calls = _fake(monkeypatch, columns=[{"id": "v", "title": "👁️ Views", "type": "numbers"}])
    out = tools_posts.setup_posts_tracking()
    assert [c[0] for c in calls] == ["create_column"] * 5 + ["create_group"]
    assert "👁️ Views" not in out and "⬇️ Downloads" in out and calls[-1][1]["n"] == tools_posts.GROUP
    full = [{"id": str(i), "title": t, "type": k} for i, (t, k) in enumerate(tools_posts.COLUMNS)]
    calls = _fake(monkeypatch, columns=full, groups=[{"id": "g1", "title": tools_posts.GROUP}])
    assert "כבר קיים" in tools_posts.setup_posts_tracking() and calls == []


def test_share_is_logged_as_a_row_in_the_posts_group(monkeypatch):
    cols = [{"id": "step", "title": "🌱 Next organic step", "type": "text"},
            {"id": "when", "title": "⏰ Organic step at", "type": "date"}]
    calls = _fake(monkeypatch, columns=cols, groups=[{"id": "g1", "title": tools_posts.GROUP}])
    out = tools_posts.log_post_share("סרטון טניס שולחן", "פייסבוק", "Parkinson's UK", "https://fb.com/p/1",
                                     "לשתף בקבוצה נוספת", "2026-11-15")
    item, update = calls
    assert item[0] == "create_item" and item[1]["g"] == "g1"
    assert item[1]["n"] == "פייסבוק · סרטון טניס שולחן · שותף ל: Parkinson's UK"
    assert json.loads(item[1]["v"]) == {"step": "לשתף בקבוצה נוספת", "when": {"date": "2026-11-15"}}
    assert update[0] == "create_update" and update[1]["item"] == "900" and "https://fb.com/p/1" in update[1]["body"]
    assert "נרשם" in out


def test_share_before_setup_explains(monkeypatch):
    calls = _fake(monkeypatch)
    assert "עדיין לא הוכן" in tools_posts.log_post_share("פוסט") and calls == []
