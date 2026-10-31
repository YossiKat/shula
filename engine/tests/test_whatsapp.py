import time

import pytest
from fastapi.testclient import TestClient

import main

_REAL_TWILIO_CHECK = main._from_twilio


@pytest.fixture
def client(monkeypatch):
    main._pending.clear()
    monkeypatch.setattr(main, "SYNC_DEADLINE", 0.3)
    monkeypatch.setattr(main, "ASYNC_MODE", False)
    monkeypatch.setattr(main, "TWILIO_TOKEN", None)
    monkeypatch.setattr(main, "_from_twilio", lambda *a: True)  # בבדיקות אין Twilio אמיתי
    monkeypatch.setattr(main, "ALLOWED_SENDERS", {"whatsapp:+972500000000", "whatsapp:+972511111111"})
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


def test_stranger_is_ignored(client, monkeypatch):
    called = []
    monkeypatch.setattr(main.shula_agent, "reply", lambda *a: called.append(a) or "סוד")
    xml = _send(client, "מה במייל של יוסי?", sender="whatsapp:+15550001111")
    assert "סוד" not in xml and called == []


def test_forged_twilio_request_is_rejected(client, monkeypatch):
    monkeypatch.setattr(main, "_from_twilio", _REAL_TWILIO_CHECK)
    monkeypatch.setattr(main, "TWILIO_TOKEN", "secret-token")
    monkeypatch.setattr(main.shula_agent, "reply", lambda *a: "סוד")
    r = client.post("/whatsapp", data={"Body": "היי", "From": "whatsapp:+972500000000"},
                    headers={"X-Twilio-Signature": "fake"})
    assert r.status_code == 403


def test_real_twilio_signature_is_accepted(client, monkeypatch):
    monkeypatch.setattr(main, "_from_twilio", _REAL_TWILIO_CHECK)
    from twilio.request_validator import RequestValidator
    monkeypatch.setattr(main, "TWILIO_TOKEN", "secret-token")
    monkeypatch.setattr(main.shula_agent, "reply", lambda *a: "שלום יוסי")
    data = {"Body": "היי", "From": "whatsapp:+972500000000"}
    sig = RequestValidator("secret-token").compute_signature(f"{main.PUBLIC_URL}/whatsapp", data)
    r = client.post("/whatsapp", data=data, headers={"X-Twilio-Signature": sig})
    assert r.status_code == 200 and "שלום יוסי" in r.text


def test_ask_needs_key(client, monkeypatch):
    monkeypatch.setattr(main.shula_agent, "reply", lambda *a: "סוד")
    monkeypatch.delenv("ASK_KEY", raising=False)
    assert client.post("/ask", params={"user_input": "x"}).status_code == 403
    monkeypatch.setenv("ASK_KEY", "k")
    assert client.post("/ask", params={"user_input": "x"}, headers={"X-Shula-Key": "wrong"}).status_code == 403
    r = client.post("/ask", params={"user_input": "x"}, headers={"X-Shula-Key": "k"})
    assert r.json()["response"] == "סוד"
    r = client.post("/ask", params={"user_input": "x", "bot_name": "../tests/x"}, headers={"X-Shula-Key": "k"})
    assert r.status_code == 404


def test_without_twilio_token_nobody_gets_in(monkeypatch):
    # אם הטוקן נמחק ב-Render בטעות — שולה לא נפתחת לכולם, היא נסגרת
    monkeypatch.setattr(main, "TWILIO_TOKEN", None)
    c = TestClient(main.app)
    r = c.post("/whatsapp", data={"Body": "תקראי לי את המיילים", "From": "whatsapp:+972547599993"})
    assert r.status_code == 403


def test_keep_awake_does_not_start_outside_render(monkeypatch):
    started = []
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setattr(main.threading, "Thread", lambda *a, **k: started.append(1))
    main._start_keep_awake()
    assert started == []


def test_keep_awake_starts_on_render(monkeypatch):
    class T:
        def __init__(self, *a, **k): pass
        def start(self): started.append(1)
    started = []
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setattr(main.threading, "Thread", T)
    main._start_keep_awake()
    assert started == [1]


def test_slow_answer_in_async_mode_sends_no_waiting_message(client, monkeypatch):
    # יוסי לא רוצה לקבל "רגע, בודקת… שלח לי המשך" — התשובה תגיע לבד
    pushed = []
    monkeypatch.setattr(main, "ASYNC_MODE", True)
    monkeypatch.setattr(main, "_push_blocked", False)
    monkeypatch.setattr(main, "_send_whatsapp", lambda to, text: pushed.append(text))
    monkeypatch.setattr(main.shula_agent, "reply", lambda *a: (time.sleep(0.6), "התשובה המלאה")[1])
    xml = _send(client, "שאלה קשה")
    assert "בודקת" not in xml and "המשך" not in xml
    for _ in range(40):
        if pushed:
            break
        time.sleep(0.05)
    assert pushed == ["התשובה המלאה"]


def test_waiting_message_stays_when_push_is_blocked(client, monkeypatch):
    monkeypatch.setattr(main, "ASYNC_MODE", True)
    monkeypatch.setattr(main, "_push_blocked", True)
    monkeypatch.setattr(main.shula_agent, "reply", lambda *a: (time.sleep(0.6), "x")[1])
    assert "המשך" in _send(client, "שאלה קשה")
