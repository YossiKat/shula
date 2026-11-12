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
    assert [c[0] for c in calls] == ["create_column"] * (len(tools_posts.COLUMNS) - 1) + ["create_group"]
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


def test_facebook_shares_are_imported_one_row_each_and_never_twice(monkeypatch):
    cols = [{"id": "at", "title": "📅 Shared at", "type": "date"}, {"id": "to", "title": "👥 Shared to", "type": "text"},
            {"id": "ln", "title": "🔗 Post link", "type": "text"}]
    sheet = [{"date": "2026-11-12", "time": "12:34", "post": "העוזר החדש", "group": "Parkinson's Warriors", "link": "https://fb/1", "pending": False},
             {"date": "2026-11-12", "time": "12:33", "post": "העוזר החדש", "group": "DBS Surgery", "link": "https://fb/2", "pending": True},
             {"date": "2026-11-11", "time": "21:58", "post": "הכירו את aCare Home", "group": "Leven met Parkinson", "link": "https://fb/3", "pending": False}]
    calls = _fake(monkeypatch, columns=cols, groups=[{"id": "g1", "title": tools_posts.GROUP}])
    monkeypatch.setattr(tools_posts, "_sheet_rows", lambda: sheet)
    monkeypatch.setattr(tools_posts, "_existing_links", lambda b, g, c: {"https://fb/3"})
    out = tools_posts.import_facebook_shares(limit=1)
    assert "נרשמו ב-monday 1" in out and "נשארו עוד 1" in out
    assert calls[0][1]["n"] == "פייסבוק · העוזר החדש · Parkinson's Warriors"
    assert json.loads(calls[0][1]["v"]) == {"to": "Parkinson's Warriors", "ln": "https://fb/1", "at": {"date": "2026-11-12"}}
    calls.clear()
    monkeypatch.setattr(tools_posts, "_existing_links", lambda b, g, c: {"https://fb/3", "https://fb/1"})
    out = tools_posts.import_facebook_shares()
    assert len(calls) == 1 and calls[0][1]["n"].endswith("DBS Surgery (ממתין לאישור מנהל)") and "הכול מעודכן" in out


def test_import_prepares_missing_columns_first(monkeypatch):
    calls = _fake(monkeypatch, groups=[{"id": "g1", "title": tools_posts.GROUP}])
    out = tools_posts.import_facebook_shares()
    assert [c[0] for c in calls] == ["create_column"] * len(tools_posts.COLUMNS) and "לא הצלחתי" in out
