from types import SimpleNamespace as NS
import json

import tools_monday
import tools_posts

REAL_STATS = tools_posts._original_stats


SHARE_COLS = [{"id": "at", "title": "📅 Shared at", "type": "date"}, {"id": "to", "title": "👥 Shared to", "type": "text"},
              {"id": "ln", "title": "🔗 Post link", "type": "text"}, {"id": "vw", "title": "👁️ Views", "type": "numbers"},
              {"id": "in", "title": "💬 Interactions", "type": "numbers"}, {"id": "gr", "title": "📈 Growth", "type": "text"}]


def _fake(monkeypatch, columns=(), groups=()):
    calls = []
    board = {"id": "77", "name": "AnyCan Ai", "columns": list(columns), "groups": list(groups)}
    monkeypatch.setattr(tools_monday, "_anycan_boards", lambda: [{"id": "77", "name": "Supermetrics Campaign Reporting", "type": "board"}])

    def query(gql, variables, account="alphaomega"):
        assert account == "anycan"
        if gql.startswith("query"):
            return {"boards": [board]}
        calls.append((gql.split("{")[1].split("(")[0].strip(), variables))
        return {"create_item": {"id": "900"}}
    monkeypatch.setattr(tools_monday, "_query", query)
    monkeypatch.setattr(tools_posts, "_original_stats", lambda: {})
    monkeypatch.setattr(tools_posts, "shares_to_calendar", lambda rows: "")
    monkeypatch.setattr(tools_posts, "move_posts_tracking", lambda: "המעקב כבר נמצא בלוח")
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
    cols = SHARE_COLS
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
    assert json.loads(calls[3][1]["v"]) == {"to": "2 שיתופים ל-2 קבוצות, 1 ממתינים לאישור",
                                            "at": {"date": "2026-11-12", "time": "10:34:00"}}
    assert "נרשמו ב-monday 2 שיתופים מפייסבוק תחת 1 פוסטים" in out and "הכול מעודכן" in out
    calls.clear()
    assert "נרשמו ב-monday 0" in tools_posts.import_facebook_shares() and calls == []


def test_import_stops_at_the_limit_and_says_what_is_left(monkeypatch):
    cols = SHARE_COLS
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


def test_post_row_gets_original_link_views_and_growth_percent(monkeypatch):
    calls = _fake(monkeypatch, columns=SHARE_COLS, groups=[{"id": "g1", "title": tools_posts.GROUP}])
    posts = {"פייסבוק · העוזר החדש": {"id": "50", "subs": set(), "cols": {}}}
    rows = [["2026-11-12", "העוזר החדש", "https://fb/reel/1", "130", "3", "1", "36"],
            ["2026-11-14", "העוזר החדש", "https://fb/reel/1", "410", "9", "2", "40"],
            ["2026-11-14", "פוסט שלא במנדיי", "https://fb/p/2", "", "1", "0", "0"]]
    monkeypatch.setattr(tools_posts, "_sheet_rows", lambda: [])
    monkeypatch.setattr(tools_posts, "_existing_posts", lambda b, g: posts)
    monkeypatch.setattr(tools_posts, "_original_stats", REAL_STATS)
    monkeypatch.setattr(tools_posts, "_csv", lambda sheet_id: rows)
    out = tools_posts.import_facebook_shares()
    assert [c[0] for c in calls] == ["change_multiple_column_values"] and "עודכנו צפיות ועלייה ב-1 פוסטים" in out
    assert json.loads(calls[0][1]["v"]) == {"ln": "https://fb/reel/1", "vw": "410", "in": "51",
                                            "gr": "+215% (130 ב-12.11 → 410 ב-14.11)"}
    posts["פייסבוק · העוזר החדש"]["cols"] = {"🔗 post link": "https://fb/reel/1", "👁️ views": "410", "💬 interactions": "51",
                                             "📈 growth": "+215% (130 ב-12.11 → 410 ב-14.11)"}
    calls.clear()
    assert "עודכנו" not in tools_posts.import_facebook_shares() and calls == []


def test_first_measurement_and_posts_without_view_counts(monkeypatch):
    first = {"date": "2026-11-12", "views": 130, "likes": 3, "comments": 1, "shares": 36}
    assert tools_posts._stat_values({"link": "l", "first": first, "last": first})["📈 growth"] == "נמדד לראשונה ב-12.11: 130 צפיות"
    photo = {"date": "2026-11-12", "views": None, "likes": 5, "comments": 0, "shares": 2}
    v = tools_posts._stat_values({"link": "l", "first": photo, "last": photo})
    assert v["👁️ views"] == "" and v["💬 interactions"] == "7" and "אין ספירת צפיות" in v["📈 growth"]


class _Cal:
    def __init__(self):
        self.store, self.calls = {}, []

    def events(self):
        return self

    def list(self, calendarId, privateExtendedProperty, pageToken=None, maxResults=250, showDeleted=False):
        return NS(execute=lambda: {"items": list(self.store.values())})

    def insert(self, calendarId, body):
        def go():
            body["id"] = f"e{len(self.store)}"
            self.store[body["id"]] = body
            self.calls.append("insert")
        return NS(execute=go)

    def patch(self, calendarId, eventId, body):
        def go():
            self.store[eventId].update(body)
            self.calls.append("patch")
        return NS(execute=go)


def test_each_share_round_is_one_light_green_event_at_the_share_time(monkeypatch):
    import tools_calendar
    cal = _Cal()
    monkeypatch.setattr(tools_calendar, "_svc", lambda: cal)
    rows = [{"date": "2026-11-12", "time": "12:13", "post": "העוזר החדש", "group": "A", "link": "1", "pending": False},
            {"date": "2026-11-12", "time": "12:34", "post": "העוזר החדש", "group": "B", "link": "2", "pending": True},
            {"date": "2026-11-12", "time": "21:58", "post": "העוזר החדש", "group": "C", "link": "3", "pending": False},
            {"date": "2026-11-11", "time": "9:05", "post": "פוסט אחר", "group": "A", "link": "4", "pending": False}]
    out = tools_posts.shares_to_calendar(rows)
    assert "3 סבבי שיתוף חדשים" in out and cal.calls == ["insert"] * 3
    first = next(e for e in cal.store.values() if e["start"]["dateTime"].startswith("2026-11-12T12:13"))
    assert first["summary"] == "📤 שיתפתי: העוזר החדש → 2 קבוצות" and first["colorId"] == "2"
    assert first["end"]["dateTime"].startswith("2026-11-12T12:34") and "12:34 · B (ממתין לאישור מנהל)" in first["description"]
    assert any(e["start"]["dateTime"].startswith("2026-11-11T09:05") for e in cal.store.values())
    cal.calls.clear()
    assert tools_posts.shares_to_calendar(rows) == "" and cal.calls == []
    rows.append({"date": "2026-11-12", "time": "12:40", "post": "העוזר החדש", "group": "D", "link": "5", "pending": False})
    assert "1 עודכנו" in tools_posts.shares_to_calendar(rows) and cal.calls == ["patch"]


def test_tracking_moves_once_from_anycan_ai_to_the_supermetrics_board(monkeypatch):
    old = {"id": "77", "name": "AnyCan Ai", "groups": [{"id": "gold", "title": tools_posts.GROUP}],
           "columns": [{"id": "name", "title": "Name", "type": "name"}, {"id": "v1", "title": "👁️ Views", "type": "numbers"},
                       {"id": "st", "title": "Stage", "type": "status"}]}
    new = {"id": "88", "name": "Supermetrics Campaign Reporting", "groups": [{"id": "gnew", "title": tools_posts.GROUP}],
           "columns": [{"id": "name", "title": "Name", "type": "name"}, {"id": "v2", "title": "👁️ Views", "type": "numbers"}]}
    calls = []
    monkeypatch.setattr(tools_monday, "_anycan_boards", lambda: [{"id": "77", "name": "AnyCan Ai", "type": "board"},
                                                                 {"id": "88", "name": "Supermetrics Campaign Reporting", "type": "board"}])

    def query(gql, variables, account="alphaomega"):
        if "boards(ids: $ids)" in gql:
            return {"boards": [old if variables["ids"] == ["77"] else new]}
        if "items_page" in gql:
            return {"boards": [{"groups": [{"items_page": {"cursor": None, "items": [{"id": "1"}, {"id": "2"}]}}]}]}
        calls.append((gql.split("{")[1].split("(")[0].strip(), variables))
        return {}
    monkeypatch.setattr(tools_monday, "_query", query)
    monkeypatch.setattr(tools_posts, "setup_posts_tracking", lambda: "")
    monkeypatch.setattr(tools_posts, "_moved", False)
    out = tools_posts.move_posts_tracking()
    assert [c[0] for c in calls] == ["move_item_to_board", "move_item_to_board", "archive_group"]
    assert calls[0][1]["b"] == "88" and calls[0][1]["g"] == "gnew"
    assert "m" not in calls[0][1] and calls[0][1]["i"] == "1"
    assert calls[2][1] == {"b": "77", "g": "gold"} and "הועברו 2 פוסטים" in out
    calls.clear()
    assert "כבר נמצא" in tools_posts.move_posts_tracking() and calls == []
