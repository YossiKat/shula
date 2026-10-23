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
