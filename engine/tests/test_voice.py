import pytest
from fastapi.testclient import TestClient

import main
import voice


@pytest.fixture
def client(monkeypatch):
    main._pending.clear()
    voice._clips.clear()
    monkeypatch.setattr(main, "SYNC_DEADLINE", 2)
    monkeypatch.setattr(main, "ASYNC_MODE", False)
    monkeypatch.setattr(main, "_from_twilio", lambda *a: True)
    monkeypatch.setattr(main, "ALLOWED_SENDERS", {"whatsapp:+972500000000"})
    monkeypatch.setattr(main.shula_agent, "reply", lambda *a, **k: "יש לך פגישה ב-10")
    monkeypatch.setattr(main.media, "prepare", lambda t, m: ("מה יש לי?", [], []))
    with TestClient(main.app) as c:
        yield c


def _voice_note(client):
    return client.post("/whatsapp", data={
        "From": "whatsapp:+972500000000", "NumMedia": "1",
        "MediaUrl0": "https://x/1", "MediaContentType0": "audio/ogg",
    })


def test_without_key_answer_stays_text_only(client, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    r = _voice_note(client)
    assert "יש לך פגישה ב-10" in r.text and "<Media>" not in r.text


def test_voice_note_gets_text_and_playable_clip(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setattr(voice, "synthesize", lambda t: b"mp3-bytes")
    r = _voice_note(client)
    assert "יש לך פגישה ב-10" in r.text
    url = r.text.split("<Media>")[1].split("</Media>")[0]
    clip = client.get(url.replace(main.PUBLIC_URL, ""))
    assert clip.content == b"mp3-bytes" and clip.headers["content-type"] == "audio/mpeg"


def test_typed_message_gets_no_voice(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setattr(voice, "synthesize", lambda t: pytest.fail("should not speak"))
    r = client.post("/whatsapp", data={"From": "whatsapp:+972500000000", "Body": "מה יש לי?"})
    assert "<Media>" not in r.text


def test_voice_failure_still_sends_text(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")

    def boom(t):
        raise RuntimeError("down")

    monkeypatch.setattr(voice, "synthesize", boom)
    r = _voice_note(client)
    assert "יש לך פגישה ב-10" in r.text and "<Media>" not in r.text


def test_long_answer_is_not_spoken(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setattr(voice, "synthesize", lambda t: pytest.fail("should not speak"))
    assert voice.speak("א" * (voice.MAX_CHARS + 1), "https://x").audio_url is None


def test_unknown_clip_is_404(client):
    assert client.get("/voice/nothing.mp3").status_code == 404


def test_clean_for_speech():
    assert voice.clean_for_speech("**שלום** 👋 עולה 620 ₪\n- ראו https://a.co") == "שלום עולה 620 שקלים\nראו"
