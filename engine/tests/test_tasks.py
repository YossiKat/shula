from datetime import datetime, timedelta
from types import SimpleNamespace as NS

import tools_calendar
import tools_tasks


def _cal(monkeypatch, events):
    store = {e["id"]: e for e in events}
    calls = []

    class Cal:
        def events(self):
            return self

        def list(self, **kw):
            return NS(execute=lambda: {"items": list(store.values())})

        def patch(self, calendarId, eventId, body, sendUpdates=None):
            calls.append(("patch", eventId, sendUpdates))

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
    return store, calls


def _ev(id, title, days=0, hour=10, color="11"):
    d = datetime.now(tools_calendar.TZ).replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days)
    return {"id": id, "summary": title, "colorId": color,
            "start": {"dateTime": d.isoformat()}, "end": {"dateTime": (d + timedelta(minutes=30)).isoformat()}}


def test_department_summary_counts_stages(monkeypatch):
    _cal(monkeypatch, [_ev("a", "🗂️ סוזן: לסדר תיק", -2), _ev("b", "🗂️ סוזן: הזמנה", 0), _ev("c", "📣 ג׳סיקה: פוסט", 3),
                       _ev("d", "✅ בוצע: 🗂️ סוזן: ישן", -1)])
    out = tools_tasks.department_tasks()
    assert "סוזן: באיחור 1 · היום 1" in out
    assert "ג׳סיקה: באיחור 0 · היום 0 · מחר 0 · השבוע 1" in out


def test_department_detail_lists_tasks(monkeypatch):
    _cal(monkeypatch, [_ev("a", "📣 ג׳סיקה: הודעה לעיתונות", 1)])
    out = tools_tasks.department_tasks("ג׳סיקה")
    assert "🔵 מחר" in out and "הודעה לעיתונות" in out


def test_mark_done_patches_title_and_color_without_mail(monkeypatch):
    store, calls = _cal(monkeypatch, [_ev("a", "לשלוח לנטלי – הערות לרילס", 0)])
    out = tools_tasks.mark_task_done("לשלוח לנטלי", "נשלח")
    assert store["a"]["summary"].startswith("✅ בוצע: לשלוח לנטלי") and store["a"]["summary"].endswith("(נשלח)")
    assert store["a"]["colorId"] == "7" and calls[0][2] == "none"
    assert "סומן בוצע" in out


def test_mark_done_asks_when_ambiguous(monkeypatch):
    store, _ = _cal(monkeypatch, [_ev("a", "שיחה עם רובר", 0), _ev("b", "מעקב: רובר – לקבוע", 1)])
    out = tools_tasks.mark_task_done("רובר")
    assert "על איזו" in out and store["a"]["colorId"] == "11" and store["b"]["colorId"] == "11"


def test_move_task_keeps_length(monkeypatch):
    store, _ = _cal(monkeypatch, [_ev("a", "שיחה עם רובר", 0, hour=10)])
    tomorrow = (datetime.now(tools_calendar.TZ) + timedelta(days=1)).date().isoformat()
    tools_tasks.move_task("שיחה עם רובר", tomorrow + "T11:00")
    s = datetime.fromisoformat(store["a"]["start"]["dateTime"])
    e = datetime.fromisoformat(store["a"]["end"]["dateTime"])
    assert s.hour == 11 and (e - s) == timedelta(minutes=30)


def test_add_note_appends(monkeypatch):
    ev = _ev("a", "הודעה לעיתונות aCare", 0)
    ev["description"] = "קיים"
    store, _ = _cal(monkeypatch, [ev])
    tools_tasks.add_task_note("הודעה לעיתונות", "לחכות לרזאן")
    assert store["a"]["description"].startswith("קיים") and "לחכות לרזאן" in store["a"]["description"]


def test_new_department_task(monkeypatch):
    store, _ = _cal(monkeypatch, [])
    tomorrow = (datetime.now(tools_calendar.TZ) + timedelta(days=1)).date().isoformat()
    out = tools_tasks.new_department_task("ג׳סיקה", "לבדוק את הרילס של דטו", tomorrow + "T10:00")
    ev = next(iter(store.values()))
    assert ev["summary"] == "📣 ג׳סיקה: לבדוק את הרילס של דטו" and ev["colorId"] == "11"
    assert "נוצרה משימה" in out
    assert "לא זיהיתי" in tools_tasks.new_department_task("מישהו", "x", tomorrow + "T10:00")
