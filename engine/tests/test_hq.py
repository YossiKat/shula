from datetime import datetime, timedelta
from types import SimpleNamespace as NS

from fastapi.testclient import TestClient

import hq
import tools_calendar


def _client(monkeypatch, events=()):
    monkeypatch.setenv("HQ_SECRET", "test-secret")
    monkeypatch.setattr(hq, "OPEN_UNTIL", 1)
    hq.clear_snapshot()
    store = {e["id"]: e for e in events}

    class Cal:
        def events(self):
            return self
        def list(self, **kw):
            return NS(execute=lambda: {"items": list(store.values())})
        def get(self, calendarId, eventId):
            return NS(execute=lambda: store[eventId])
        def patch(self, calendarId, eventId, body, sendUpdates=None):
            def go():
                store[eventId].update(body)
                return store[eventId]
            return NS(execute=go)
        def insert(self, calendarId, body):
            def go():
                body["id"] = f"n{len(store)}"
                store[body["id"]] = body
                return body
            return NS(execute=go)
    monkeypatch.setattr(tools_calendar, "_svc", lambda: Cal())
    import main
    return TestClient(main.app), store


def _ev(id, title, color, hours=0, days=0):
    t = datetime.now(tools_calendar.TZ).replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=days, hours=hours)
    return {"id": id, "summary": title, "colorId": color, "start": {"dateTime": t.isoformat()}}


def test_no_data_without_login_and_link_logs_in(monkeypatch):
    c, _ = _client(monkeypatch)
    assert "כניסה למטה" in c.get("/hq").text and c.get("/hq/api/today").status_code == 401
    assert c.get("/hq/login?t=bad", follow_redirects=False).status_code == 401
    link = hq.hq_login_link().split("?t=")[1]
    r = c.get(f"/hq/login?t={link}", follow_redirects=False)
    assert r.status_code == 303 and hq.COOKIE in r.cookies
    assert hq.check_token(r.cookies[hq.COOKIE], "session") and not hq.check_token(link, "session")


def test_today_tiles_done_and_add(monkeypatch):
    evs = [_ev("a", "📞 להתקשר לדנה", "11"), _ev("b", "💸 הוצאה 112₪ – צהריים", "6"),
           _ev("c", "💰 הכנסה 400₪ ✅ שולם", "10", days=-1), _ev("d", "🧾 קבלה", "11", days=-2),
           _ev("m", "Medtronic · 🩺 רופאים ומטפלים", None)]
    c, store = _client(monkeypatch, evs)
    c.cookies.set(hq.COOKIE, hq.make_token("session", 60))
    s = c.get("/hq/api/today").json()
    assert s["tiles"] == {"open": 1, "late": 1, "done7": 0, "spent": 112}
    assert s["money"]["income"] >= 400 and all("Medtronic" not in i["title"] for i in s["today"])
    assert c.post("/hq/api/done", json={"id": "a"}).status_code == 403  # בלי הכותרת של האתר
    r = c.post("/hq/api/done", json={"id": "a"}, headers={"x-hq": "1"}).json()
    assert r["ok"] and store["a"]["colorId"] == "7" and store["a"]["summary"].startswith("✅ בוצע:")
    r = c.post("/hq/api/expense", json={"amount": "45", "what": "קפה", "how": "כרטיס"}, headers={"x-hq": "1"}).json()
    assert r["ok"] and r["title"] == "💸 הוצאה 45₪ – קפה (כרטיס)"
    assert not c.post("/hq/api/task", json={"title": "x", "day": "bad", "at": "10:00"}, headers={"x-hq": "1"}).json()["ok"]


def test_departments_and_alerts(monkeypatch):
    evs = [_ev("a", "📣 ג׳סיקה: פוסט לאישור", "11", hours=8), _ev("d", "🧾 קבלה לאלפא אומגה", "11", days=-2)]
    c, _ = _client(monkeypatch, evs)
    c.cookies.set(hq.COOKIE, hq.make_token("session", 60))
    s = c.get("/hq/api/today").json()
    by = {d["key"]: d for d in s["depts"]}
    assert len(s["depts"]) == 7 and by["cmo"]["open"] == 1 and by["cfo"]["late"] == 1
    assert any(a["level"] == "late" and "קבלה" in a["text"] for a in s["alerts"])


def test_book_the_meeting_room(monkeypatch):
    c, store = _client(monkeypatch)
    c.cookies.set(hq.COOKIE, hq.make_token("session", 60))
    r = c.post("/hq/api/room", json={"topic": "ישיבת צוות שבועית", "day": "2026-11-22", "at": "10:00",
                                      "minutes": 60, "depts": ["cmo", "cto"]}, headers={"x-hq": "1"}).json()
    assert r["ok"] and r["title"] == "🏛️ חדר ישיבות – ישיבת צוות שבועית (ג׳סיקה, אמילי)"
    ev = next(iter(store.values()))
    assert ev["colorId"] == "11" and ev["end"]["dateTime"].startswith("2026-11-22T11:00")
    s = c.get("/hq/api/today").json()
    assert "week" in s and "done_week" in s and all("dept" in i for i in s["today"])


def test_snapshot_cache_cleared_by_actions(monkeypatch):
    calls = []
    monkeypatch.setattr(hq, "snapshot", lambda: calls.append(1) or {"n": len(calls)})
    hq.clear_snapshot()
    assert hq.cached_snapshot() == {"n": 1}
    assert hq.cached_snapshot() == {"n": 1}
    hq.clear_snapshot()
    assert hq.cached_snapshot() == {"n": 2}
    hq.clear_snapshot()


def test_money_month_full_month_and_details(monkeypatch):
    now = datetime(2026, 11, 16, 12, 0, tzinfo=tools_calendar.TZ)
    evs = [
        {"id": "a", "summary": "💸 הוצאה 100₪ – קפה", "colorId": "6", "start": {"dateTime": "2026-11-01T08:00:00+02:00"}},
        {"id": "b", "summary": "🚲 שיעור – 💰 הכנסה 400₪ ✅ שולם", "colorId": "10", "start": {"dateTime": "2026-11-13T10:00:00+02:00"}},
        {"id": "c", "summary": "💸 הוצאה 50₪ – אוקטובר", "colorId": "6", "start": {"dateTime": "2026-10-31T20:00:00+02:00"}},
        {"id": "d", "summary": "💸 הוצאה 70₪ – סוף החודש", "colorId": "6", "start": {"dateTime": "2026-11-30T20:00:00+02:00"}},
    ]
    monkeypatch.setattr(hq, "_events", lambda a, b: [e for e in evs if a <= hq._start(e)[0] < b])
    m = hq.money_month("", now)
    assert m["ym"] == "2026-11" and m["label"] == "נובמבר 2026" and m["is_current"]
    assert (m["spent"], m["income"], m["balance"]) == (170, 400, 230)
    assert m["prev"] == "2026-10" and m["next"] == "2026-12"
    o = hq.money_month("2026-10", now)
    assert o["spent"] == 50 and not o["is_current"] and o["items"][0]["kind"] == "out"


def test_learning_from_sheet(monkeypatch):
    csv_text = ("dept,kind,topic,from,link,month,progress,lessons,apply,applyStatus,applyCheck,why,updated\n"
                "cmo,learn,פתיחות לסרטונים,קונור,https://x.example,נובמבר 2026,שבוע 3,א | ב,3 פתיחות,פעיל,,יותר צפיות,15.11.2026\n"
                "cmo,change,3 פתיחות,,,,,,כותבת 3 פתיחות,,,,15.11.2026\n")

    class D:
        def files(self):
            return self
        def export(self, fileId, mimeType):
            return NS(execute=lambda: csv_text.encode())
    import google_auth
    monkeypatch.setattr(google_auth, "service", lambda *a, **k: D())
    monkeypatch.setattr(hq, "_LEARN", {"t": 0.0, "data": {}})
    L = hq.learning()
    assert L["cmo"]["topic"] == "פתיחות לסרטונים" and L["cmo"]["lessons"] == ["א", "ב"]
    assert L["cmo"]["status"] == "פעיל" and L["cmo"]["changes"][0]["name"] == "3 פתיחות"
