import time

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(monkeypatch):
    main._pending.clear()
    monkeypatch.setattr(main, "SYNC_DEADLINE", 0.3)
    monkeypatch.setattr(main, "ASYNC_MODE", False)
    # לולאת אירועים אחת לכל הבדיקה — כמו בשרת, כדי שתשובה ממתינה תשרוד בין הודעות
    with TestClient(main.app) as c:
        yield c


def _send(client, body, sender="whatsapp:+972500000000"):
    r = client.post("/whatsapp", data={"Body": body, "From": sender})
    assert r.status_code == 200
    return r.text


def test_fast_answer_comes_back_directly(client, monkeypatch):
    monkeypatch.setattr(main.shula_agent, "reply", lambda s, m, *a: "יש לך 3 פגישות")
    assert "יש לך 3 פגישות" in _send(client, "מה יש לי מחר?")


def test_answer_is_xml_escaped(client, monkeypatch):
    monkeypatch.setattr(main.shula_agent, "reply", lambda s, m, *a: "<b>&</b>")
    xml = _send(client, "בדיקה")
    assert "&lt;b&gt;&amp;&lt;/b&gt;" in xml


def test_slow_answer_is_delivered_on_nudge(client, monkeypatch):
    def slow(sender, msg, *a):
        time.sleep(0.6)
        return "התשובה המלאה"

    monkeypatch.setattr(main.shula_agent, "reply", slow)
    assert "בודקת" in _send(client, "שאלה קשה")
    time.sleep(0.5)
    assert "התשובה המלאה" in _send(client, "המשך")


def test_reset_clears_memory(client, monkeypatch):
    forgotten = []
    monkeypatch.setattr(main.shula_agent, "forget", forgotten.append)
    assert "איפסתי" in _send(client, "איפוס", sender="whatsapp:+972511111111")
    assert forgotten == ["whatsapp:+972511111111"]


def test_empty_message_gets_greeting(client):
    assert "שולה" in _send(client, "   ")


def test_push_blocked_keeps_answer_for_nudge(monkeypatch):
    """Twilio חוסם שליחה יזומה (KYC) — התשובה נשארת ממתינה, ושולחים לא מנסים שוב."""
    import concurrent.futures

    monkeypatch.setattr(main, "_push_blocked", False)
    monkeypatch.setattr(main, "_send_whatsapp", lambda to, text: (_ for _ in ()).throw(
        RuntimeError("Primary compliance profile is not approved")))
    fut = concurrent.futures.Future()
    fut.set_result("תשובה")
    main._pending["x"] = fut
    main._push_when_ready("x", fut)
    time.sleep(0.2)
    assert main._push_blocked is True
    assert main._pending.get("x") is fut
    main._pending.clear()
