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


def test_correction_is_flagged_with_previous_answer():
    subject, body = conversation_log.format_entry(
        "לא, התכוונתי ליום שני הבא", "העברתי ליום שני 2.11", [], 2.0,
        previous_answer="רשמתי ליום ראשון 1.11")
    assert conversation_log.CORRECTION_MARK in subject
    assert "רשמתי ליום ראשון 1.11" in body


def test_normal_message_not_flagged():
    assert not conversation_log.is_correction("מה יש לי מחר?")
    assert not conversation_log.is_correction("לא דחוף, תזכירי לי מחר")
    assert conversation_log.is_correction("טעית בתאריך")
    subject, body = conversation_log.format_entry("מה יש לי מחר?", "כלום", [], 1.0, previous_answer="משהו")
    assert conversation_log.CORRECTION_MARK not in subject
    assert "משהו" not in body


def test_learned_rules_enter_prompt(tmp_path, monkeypatch):
    import shula_agent
    rules = tmp_path / "learned_rules.txt"
    rules.write_text("# הערה\n- הוצאה בלי אמצעי תשלום: לשאול בכרטיס או מזומן (אושר 01.11.2026)\n", encoding="utf-8")
    monkeypatch.setattr(shula_agent, "LEARNED_RULES_FILE", str(rules))
    monkeypatch.setattr(shula_agent, "_agenda", lambda: "")
    prompt = shula_agent._system_prompt("core_shula")
    assert "כללים שלמדתי מהתיקונים של יוסי" in prompt
    assert "לשאול בכרטיס או מזומן" in prompt
    assert "# הערה" not in prompt


def test_values_section_in_prompt():
    import shula_agent
    prompt = shula_agent.manager.get_bot_prompt("core_shula")
    assert "ערכים ואופי" in prompt and "אני לא בטוחה" in prompt
