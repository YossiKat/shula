from datetime import datetime, timedelta
from types import SimpleNamespace as NS

import tools_calendar
import tools_monday
import tools_sync

TODAY = datetime.now(tools_sync.TZ).date()
SOON = (TODAY + timedelta(days=3)).isoformat()


class FakeCalendar:
    """יומן מדומה: שומר אירועים בזיכרון ומתעד כל פעולה."""
    def __init__(self, events=()):
        self.store = {e["id"]: e for e in events}
        self.calls = []

    def events(self):
        return self

    def _run(self, fn):
        return NS(execute=fn)

    def list(self, calendarId, pageToken=None, maxResults=250, **kw):
        def go():
            items = list(self.store.values())
            if "privateExtendedProperty" in kw:
                k, v = kw["privateExtendedProperty"].split("=")
                items = [e for e in items if e.get("extendedProperties", {}).get("private", {}).get(k) == v]
            return {"items": items}
        return self._run(go)

    def insert(self, calendarId, body):
        def go():
            body["id"] = f"new{len(self.store)}"
            self.store[body["id"]] = body
            self.calls.append(("insert", body["summary"]))
        return self._run(go)

    def patch(self, calendarId, eventId, body):
        def go():
            ev = self.store[eventId]
            private = {**ev.get("extendedProperties", {}).get("private", {}),
                       **body.get("extendedProperties", {}).get("private", {})}
            ev.update(body)
            ev["extendedProperties"] = {"private": private}
            self.calls.append(("patch", eventId))
        return self._run(go)

    def delete(self, calendarId, eventId):
        def go():
            del self.store[eventId]
            self.calls.append(("delete", eventId))
        return self._run(go)


def _item(id, name, date=None, status="", email=""):
    cols = [{"id": "status", "type": "status", "text": status, "value": None, "column": {"title": "Status"}},
            {"id": "email", "type": "email", "text": email, "value": None, "column": {"title": "Email"}},
            {"id": "date4", "type": "date", "text": date or "", "column": {"title": "Follow up"},
             "value": ('{"date":"%s"}' % date) if date else None}]
    return {"id": id, "name": name, "group": {"title": "Wave 1"}, "column_values": cols}


def _setup(monkeypatch, items, events=()):
    cal = FakeCalendar(events)
    updates = []
    monkeypatch.setattr(tools_calendar, "_svc", lambda: cal)
    monkeypatch.setattr(tools_sync, "_board_items",
                        lambda: ({"id": "77", "name": "AnyCan Ai", "slug": "anycan-team"}, items))

    def query(gql, variables, account="alphaomega"):
        assert account == "anycan" and "create_update" in gql
        updates.append((variables["item"], variables["body"]))
        return {}
    monkeypatch.setattr(tools_monday, "_query", query)
    return cal, updates


def _own(cal):
    return {k: e for k, e in cal.store.items() if tools_sync.SUMMARY not in e.get("extendedProperties", {}).get("private", {})}


def test_only_important_monday_dates_get_their_own_event_the_rest_go_to_one_summary(monkeypatch):
    items = [_item("1", "Mayo Clinic", SOON, status="דחוף"), _item("2", "No Date Org"),
             _item("3", "Old One", (TODAY - timedelta(days=60)).isoformat()), _item("4", "Quiet Org", SOON)]
    cal, _ = _setup(monkeypatch, items)
    out = tools_sync.sync_monday_and_calendar()
    assert "1 חדשים" in out and ("insert", "📋 Mayo Clinic · Follow up") in cal.calls
    (ev,) = _own(cal).values()
    assert ev["start"] == {"date": SOON} and "boards/77/pulses/1" in ev["description"] and ev["colorId"] == "2"
    (summ,) = [e for e in cal.store.values() if e not in _own(cal).values()]
    assert summ["summary"].startswith("📋 monday – סיכום היום: 2 מתוכננים") and "Quiet Org" in summ["description"]
    assert "❗" in summ["description"] and summ["transparency"] == "transparent"
    cal.calls.clear()
    assert "0 חדשים, 0 עודכנו, 0 הוסרו" in tools_sync.sync_monday_and_calendar()
    assert [c[0] for c in cal.calls] == ["patch"] and len(cal.store) == 2  # רק הסיכום של היום מתעדכן, לא נוסף שני


def test_old_unimportant_events_are_cleared_from_the_calendar(monkeypatch):
    old = {"id": "o1", "summary": "📋 Quiet Org · Follow up", "start": {"date": SOON},
           "extendedProperties": {"private": {"shula_monday": "4:date4", "shula_monday_on": "1"}}}
    cal, _ = _setup(monkeypatch, [_item("4", "Quiet Org", SOON)], [old])
    assert "1 הוסרו" in tools_sync.sync_monday_and_calendar() and "o1" not in cal.store


def test_changed_date_done_status_and_removed_date_are_followed(monkeypatch):
    items = [_item("1", "Mayo Clinic", SOON, status="Urgent"), _item("2", "Cleveland Clinic", SOON, status="Stuck")]
    cal, _ = _setup(monkeypatch, items)
    tools_sync.sync_monday_and_calendar()
    later = (TODAY + timedelta(days=9)).isoformat()
    items[0].update(_item("1", "Mayo Clinic", later, status="Urgent"))
    items[1].update(_item("2", "Cleveland Clinic", SOON, status="Done"))
    out = tools_sync.sync_monday_and_calendar()
    assert "0 חדשים, 1 עודכנו, 1 הוסרו" in out  # מה שבוצע יורד מהיומן
    (ev,) = _own(cal).values()
    assert ev["start"] == {"date": later} and ev["colorId"] == "2"


def test_meeting_about_someone_in_monday_is_logged_on_their_item_once(monkeypatch):
    meeting = {"id": "m1", "summary": "זום עם Mayo Clinic", "start": {"dateTime": f"{SOON}T10:00:00+02:00"},
               "attendees": [{"email": "dana@cleveland.org"}]}
    lunch = {"id": "m2", "summary": "ארוחת צהריים עם אמא", "start": {"date": SOON}}
    items = [_item("1", "Mayo Clinic"), _item("2", "Cleveland Clinic", email="Dana@cleveland.org"), _item("3", "אמא")]
    cal, updates = _setup(monkeypatch, items, [meeting, lunch])
    out = tools_sync.sync_monday_and_calendar()
    assert [u[0] for u in updates] == ["1", "2"] and "נקבעה ביומן של יוסי" in updates[0][1] and "10:00" in updates[0][1]
    assert "2 עדכונים נרשמו" in out
    updates.clear()
    tools_sync.sync_monday_and_calendar()
    assert updates == []
    meeting["start"] = {"dateTime": f"{SOON}T12:00:00+02:00"}
    tools_sync.sync_monday_and_calendar()
    assert len(updates) == 2 and "עודכנה" in updates[0][1] and "12:00" in updates[0][1]


def test_events_created_from_monday_are_not_logged_back(monkeypatch):
    cal, updates = _setup(monkeypatch, [_item("1", "Mayo Clinic", SOON, status="חשוב")])
    tools_sync.sync_monday_and_calendar()
    tools_sync.sync_monday_and_calendar()
    assert updates == []


def test_preview_shows_what_would_happen_and_writes_nothing(monkeypatch):
    meeting = {"id": "m1", "summary": "זום עם Mayo Clinic", "start": {"date": SOON}}
    cal, updates = _setup(monkeypatch, [_item("1", "Mayo Clinic", SOON, status="דחוף")], [meeting])
    out = tools_sync.sync_monday_and_calendar(preview=True)
    assert "לא נכתב כלום" in out and "📋 Mayo Clinic · Follow up" in out and "יירשם ב-monday על Mayo Clinic" in out
    assert cal.calls == [] and updates == []


def test_only_shula_made_mirrors_are_cleaned_from_the_calendar(monkeypatch):
    soon = f"{SOON}T08:30:00+02:00"
    evs = [{"id": "a", "summary": "Medtronic · 🩺 רופאים ומטפלים", "start": {"dateTime": soon}},
           {"id": "b", "summary": "🤖 15.11.2026 21:10 · הכנסה 400₪", "start": {"dateTime": soon}},
           {"id": "c", "summary": "📞 לבדוק עם דנה", "start": {"dateTime": soon}},
           {"id": "d", "summary": "Medtronic · 🩺 רופאים ומטפלים", "colorId": "11", "start": {"dateTime": soon}}]
    cal, _ = _setup(monkeypatch, [], evs)
    assert "2 העתקות" in tools_sync.clean_monday_mirror() and set(cal.store) == {"c", "d"}
