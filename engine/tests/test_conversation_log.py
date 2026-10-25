import conversation_log


def test_entry_has_question_answer_and_tools():
    subject, body = conversation_log.format_entry("מה יש לי מחר?", "שתי פגישות", ["get_events_for_date"], 3.2)
    assert "מה יש לי מחר?" in subject
    assert "יוסי כתב:\nמה יש לי מחר?" in body
    assert "שולה ענתה:\nשתי פגישות" in body
    assert "get_events_for_date" in body
    assert "⏳" not in subject


def test_slow_answer_is_flagged():
    subject, body = conversation_log.format_entry("שאלה", "תשובה", [], 20.0)
    assert "⏳" in subject
    assert "רגע, בודקת" in body


def test_log_never_breaks_reply(monkeypatch):
    monkeypatch.setattr(conversation_log.google_auth, "is_connected", lambda: True)
    def boom(*a):
        raise RuntimeError("gmail down")
    monkeypatch.setattr(conversation_log, "_insert", boom)
    conversation_log.log_exchange("שאלה", "תשובה", [], 1.0)  # לא זורק


def test_values_section_in_prompt():
    import shula_agent
    prompt = shula_agent.manager.get_bot_prompt("core_shula")
    assert "ערכים ואופי" in prompt and "אני לא בטוחה" in prompt
