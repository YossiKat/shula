import tools_calendar


class _FakeService:
    def __init__(self, items):
        self.items, self.calls = items, []

    def events(self):
        return self

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return self

    def execute(self):
        return {"items": self.items}


def test_events_for_date_asks_for_that_whole_day(monkeypatch):
    svc = _FakeService([{"summary": "שיעור", "start": {"dateTime": "2026-10-25T17:30:00+02:00"}, "colorId": "10"}])
    monkeypatch.setattr(tools_calendar, "_svc", lambda: svc)
    out = tools_calendar.get_events_for_date("2026-10-25")
    call = svc.calls[0]
    assert call["timeMin"].startswith("2026-10-25T00:00")
    assert call["timeMax"].startswith("2026-10-26T00:00")
    assert "שיעור" in out and "17:30" in out


def test_events_for_date_empty_day(monkeypatch):
    monkeypatch.setattr(tools_calendar, "_svc", lambda: _FakeService([]))
    assert tools_calendar.get_events_for_date("2026-10-25") == "אין אירועים ב-25/10."


class _FakePatchService(_FakeService):
    def __init__(self, items):
        super().__init__(items)
        self.patched = []

    def patch(self, **kwargs):
        self.patched.append(kwargs)
        return self


def _say(monkeypatch, text):
    import shula_agent
    shula_agent._turn.message = text


def test_mark_done_needs_yossi_to_say_done(monkeypatch):
    svc = _FakePatchService([{"id": "a", "summary": "📞 להתקשר לדני", "start": {"dateTime": "2026-11-20T10:00:00+02:00"}}])
    monkeypatch.setattr(tools_calendar, "_svc", lambda: svc)
    _say(monkeypatch, "מה יש לי מחר?")
    out = tools_calendar.mark_event_done("דני")
    assert svc.patched == [] and "לא סומן" in out


def test_mark_done_marks_latest_past_open_task(monkeypatch):
    items = [
        {"id": "old", "summary": "📞 להתקשר לדני", "start": {"dateTime": "2026-11-10T10:00:00+02:00"}},
        {"id": "done", "summary": "✅ בוצע: להתקשר לדני", "start": {"dateTime": "2026-11-12T10:00:00+02:00"}},
        {"id": "new", "summary": "📞 להתקשר לדני שוב", "start": {"dateTime": "2026-11-15T10:00:00+02:00"}},
    ]
    svc = _FakePatchService(items)
    monkeypatch.setattr(tools_calendar, "_svc", lambda: svc)
    _say(monkeypatch, "בוצע להתקשר לדני")
    out = tools_calendar.mark_event_done("דני", "נקבע ביקור")
    p = svc.patched[0]
    assert p["eventId"] == "new" and p["sendUpdates"] == "none"
    assert p["body"]["colorId"] == "7" and p["body"]["summary"] == "✅ בוצע: 📞 להתקשר לדני שוב (נקבע ביקור)"
    assert "עוד 1" in out


class _FakeInsertService(_FakeService):
    def __init__(self):
        super().__init__([])
        self.inserted = []

    def insert(self, calendarId, body):
        self.inserted.append(body)
        self._last = body
        return self

    def execute(self):
        return getattr(self, "_last", {"items": []})


def test_log_meal_with_receipt_adds_expense(monkeypatch):
    svc = _FakeInsertService()
    monkeypatch.setattr(tools_calendar, "_svc", lambda: svc)
    tools_calendar.log_meal("סלט עוף", 520, "green", price_ils=68, place="וולט", when_iso="2026-11-23T13:00")
    meal, exp = svc.inserted
    assert meal["summary"] == "🍽️ ארוחה: סלט עוף, וולט – ~520 קק״ל 🟢" and meal["colorId"] == "8"
    assert exp["summary"] == "💸 הוצאה 68₪ – סלט עוף, וולט" and exp["colorId"] == "6"


def test_log_meal_without_price_only_meal(monkeypatch):
    svc = _FakeInsertService()
    monkeypatch.setattr(tools_calendar, "_svc", lambda: svc)
    tools_calendar.log_meal("פיצה", 900, "red", when_iso="2026-11-23T20:00")
    assert len(svc.inserted) == 1 and svc.inserted[0]["summary"].endswith("🔴")


def test_log_meal_adds_macros_to_title(monkeypatch):
    svc = _FakeInsertService()
    monkeypatch.setattr(tools_calendar, "_svc", lambda: svc)
    tools_calendar.log_meal("שקשוקה", 520, "green", when_iso="2026-11-23T08:30", protein_g=28, carbs_g=40, fat_g=22)
    assert svc.inserted[0]["summary"].endswith("🟢 · ח׳ 28 פ׳ 40 ש׳ 22")
