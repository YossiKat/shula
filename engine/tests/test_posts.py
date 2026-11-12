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


def test_facebook_shares_are_grouped_under_their_post_and_never_twice(monkeypatch):
    cols = [{"id": "at", "title": "📅 Shared at", "type": "date"}, {"id": "to", "title": "👥 Shared to", "type": "text"}]
    sheet = [{"date": "2026-11-12", "time": "12:34", "post": "העוזר החדש", "group": "Parkinson's Warriors", "link": "https://fb/1", "pending": False},
             {"date": "2026-11-12", "time": "12:33", "post": "העוזר החדש", "group": "DBS Surgery", "link": "https://fb/2", "pending": True},
             {"date": "2026-11-11", "time": "21:58", "post": "הכירו את aCare Home", "group": "Leven met Parkinson", "link": "https://fb/3", "pending": False}]
    calls = _fake(monkeypatch, columns=cols, groups=[{"id": "g1", "title": tools_posts.GROUP}])
    monkeypatch.setattr(tools_posts, "_sheet_rows", lambda: sheet)
    have = {"פייסבוק · הכירו את aCare Home": {"id": "50", "subs": {"2026-11-11 21:58 · Leven met Parkinson"}}}
    monkeypatch.setattr(tools_posts, "_existing_posts", lambda b, g: have)
    out = tools_posts.import_facebook_shares()
    kinds = [c[0] for c in calls]
    assert kinds == ["create_item", "create_subitem", "create_subitem", "change_multiple_column_values"]
    assert calls[0][1]["n"] == "פייסבוק · העוזר החדש"
    assert calls[1][1] == {"p": "900", "n": "2026-11-12 12:33 · DBS Surgery (ממתין לאישור מנהל)"}
    assert calls[2][1]["n"] == "2026-11-12 12:34 · Parkinson's Warriors"
    assert json.loads(calls[3][1]["v"]) == {"to": "2 שיתופים ל-2 קבוצות, 1 ממתינים לאישור", "at": {"date": "2026-11-12"}}
    assert "נרשמו ב-monday 2 שיתופים מפייסבוק תחת 1 פוסטים" in out and "הכול מעודכן" in out
    calls.clear()
    assert "נרשמו ב-monday 0" in tools_posts.import_facebook_shares() and calls == []


def test_import_stops_at_the_limit_and_says_what_is_left(monkeypatch):
    cols = [{"id": "at", "title": "📅 Shared at", "type": "date"}, {"id": "to", "title": "👥 Shared to", "type": "text"}]
    sheet = [{"date": "2026-11-12", "time": f"12:3{i}", "post": "העוזר החדש", "group": f"Group {i}", "link": f"https://fb/{i}", "pending": False}
             for i in range(3)]
    calls = _fake(monkeypatch, columns=cols, groups=[{"id": "g1", "title": tools_posts.GROUP}])
    monkeypatch.setattr(tools_posts, "_sheet_rows", lambda: sheet)
    monkeypatch.setattr(tools_posts, "_existing_posts", lambda b, g: {})
    out = tools_posts.import_facebook_shares(limit=2)
    assert [c[0] for c in calls].count("create_subitem") == 2 and "נשארו עוד 1" in out


def test_import_prepares_missing_columns_first(monkeypatch):
    calls = _fake(monkeypatch, groups=[{"id": "g1", "title": tools_posts.GROUP}])
    out = tools_posts.import_facebook_shares()
    assert [c[0] for c in calls] == ["create_column"] * len(tools_posts.COLUMNS) and "לא הצלחתי" in out
