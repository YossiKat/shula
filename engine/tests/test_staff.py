import staff
import tools_hub
import tools_monday


def test_route_picks_the_right_department():
    assert staff.route("להוסיף הוצאה 21 שח בית הלחם") == "home"
    assert staff.route("תכיני פוסט לאינסטגרם") == "cmo"
    assert staff.route("יצאה דרישת תשלום על ייעוץ") == "cfo"
    assert staff.route("תזכירי לי יום הולדת לאמא") == "personal"
    assert staff.route("מה שלומך") is None


def test_focus_and_roster_name_the_team():
    assert "בתיה" in staff.focus_text("הוצאה 9 שח קנדי בר")
    assert staff.focus_text("שלום") == ""
    roster = staff.roster_text()
    for d in staff.DEPARTMENTS.values():
        assert d["name"] in roster


def test_log_creates_missing_group_then_item(monkeypatch):
    calls = []
    monkeypatch.setattr(tools_monday, "_anycan_boards", lambda: [{"id": "7", "name": "AnyCan Ai", "type": "board"}])

    def query(gql, variables, account="alphaomega"):
        assert account == "anycan"
        calls.append(gql.split("{")[1].split("(")[0].strip())
        if "groups" in gql:
            return {"boards": [{"id": "7", "groups": [{"id": "todo", "title": "ToDo"}]}]}
        if "create_group" in gql:
            return {"create_group": {"id": "gnew"}}
        return {"create_update": {"id": "u1"}}
    monkeypatch.setattr(tools_monday, "_query", query)
    made = []
    monkeypatch.setattr(tools_hub, "_create", lambda b, g, n, v, a: made.append((b, g, n)) or "99")

    out = staff.log_to_department("home", "הוצאה 21₪ – בית הלחם", "09:00")
    assert made == [("7", "gnew", "הוצאה 21₪ – בית הלחם")]
    assert "create_group" in calls and "create_update" in calls
    assert "בתיה" in out

    made.clear()
    staff.log_to_department("admin", "נשלח מייל לקאי")
    assert made == [("7", "todo", "נשלח מייל לקאי")]


def test_unknown_department_is_refused():
    assert "לא מוכרת" in staff.log_to_department("xyz", "x")
