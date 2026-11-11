from types import SimpleNamespace as NS

import claude_brain
import main
import media
import shula_agent
import tools_monday
from fastapi.testclient import TestClient


def _block(**kw):
    b = NS(**kw)
    b.model_dump = lambda exclude_none=True: kw
    return b


def _usage():
    return NS(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0)


# ---------- מוח כפול ----------
def test_simple_question_uses_cheap_model():
    assert claude_brain.choose_model("מה יש לי מחר?") == claude_brain.CLAUDE_MODEL


def test_complex_requests_use_smart_model():
    for msg in ("תנסחי מייל ליפעת על הפגישה", "תסכמי לי את השבוע", "מה דעתך על ההצעה?"):
        assert claude_brain.choose_model(msg) == claude_brain.SMART_MODEL
    assert claude_brain.choose_model("מה זה?", has_images=True) == claude_brain.SMART_MODEL
    assert claude_brain.choose_model("לא, טעית", correction=True) == claude_brain.SMART_MODEL


# ---------- תמונות ו-PDF ----------
def test_image_and_pdf_go_to_claude_as_blocks():
    blocks = claude_brain._user_content("קבלה", [("image/jpeg", "AAA"), ("application/pdf", "BBB")])
    assert [b["type"] for b in blocks] == ["image", "document", "text"]


# ---------- חיפוש באינטרנט ----------
class _Seq:
    def __init__(self, *steps):
        self.steps, self.calls, self.messages = list(steps), [], self

    def create(self, **kw):
        self.calls.append(kw)
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def test_web_search_turns_itself_off_if_account_does_not_allow(monkeypatch):
    monkeypatch.setattr(claude_brain, "_web_search_on", True)
    fake = _Seq(RuntimeError("web_search tool is not enabled"),
                NS(stop_reason="end_turn", usage=_usage(), content=[_block(type="text", text="שלום")]))
    monkeypatch.setattr(claude_brain, "_client", fake)
    out = claude_brain.run("s", "d", [], "היי", [])
    assert out["text"] == "שלום"
    assert any(t.get("name") == "web_search" for t in fake.calls[0]["tools"])
    assert not any(t.get("name") == "web_search" for t in fake.calls[1]["tools"])


def test_long_web_search_continues_after_pause(monkeypatch):
    monkeypatch.setattr(claude_brain, "_web_search_on", True)
    fake = _Seq(
        NS(stop_reason="pause_turn", usage=_usage(), content=[_block(type="server_tool_use", id="s1", name="web_search", input={})]),
        NS(stop_reason="end_turn", usage=_usage(), content=[_block(type="text", text="מחר 24 מעלות")]),
    )
    monkeypatch.setattr(claude_brain, "_client", fake)
    out = claude_brain.run("s", "d", [], "מה מזג האוויר מחר?", [])
    assert out["text"] == "מחר 24 מעלות" and out["tools"] == ["web_search"]
    assert fake.calls[1]["messages"][-1]["role"] == "assistant"


# ---------- זיכרון קבוע ----------
def test_remember_and_forget_facts(monkeypatch):
    monkeypatch.setattr(shula_agent.memory_store, "save", lambda *a: None)
    shula_agent._histories.pop("__facts__", None)
    assert "נשמר" in shula_agent.remember_fact("יואב גר באמסטרדם")
    assert shula_agent.remember_fact("יואב גר באמסטרדם") == "כבר זכור."
    monkeypatch.setattr(shula_agent.google_auth, "is_connected", lambda: False)
    assert "יואב גר באמסטרדם" in shula_agent._system_prompt("core_shula")
    assert "נמחקו 1" in shula_agent.forget_fact("אמסטרדם")
    assert "אמסטרדם" not in shula_agent._system_prompt("core_shula")


# ---------- monday ----------
def test_monday_items_are_read_and_filtered(monkeypatch):
    monkeypatch.setenv("MONDAY_API_TOKEN", "x")
    data = {"data": {"boards": [{"name": "AlphaCare", "items_page": {"items": [
        {"id": "1", "name": "פוסט לפייסבוק", "updated_at": "2026-10-30T10:00:00Z", "group": {"title": "חדש"},
         "column_values": [{"column": {"title": "Status"}, "text": "Working on it"}]},
        {"id": "2", "name": "ניוזלטר", "updated_at": "2026-10-29T10:00:00Z", "group": {"title": "חדש"},
         "column_values": []},
    ]}}]}}
    monkeypatch.setattr(tools_monday.requests, "post",
                        lambda *a, **k: NS(raise_for_status=lambda: None, json=lambda: data))
    out = tools_monday.get_monday_items("פייסבוק")
    assert "<monday_data>" in out and "פוסט לפייסבוק" in out and "ניוזלטר" not in out


def test_monday_without_token_explains():
    import os
    os.environ.pop("MONDAY_API_TOKEN", None)
    out = [t for t in shula_agent.TOOLS if t.__name__ == "get_monday_items"][0]()
    assert "MONDAY_API_TOKEN" in out


def test_anycan_monday_uses_its_own_token_and_finds_board_by_name(monkeypatch):
    monkeypatch.setenv("MONDAY_API_TOKEN", "ao")
    monkeypatch.setenv("MONDAY_ANYCAN_API_TOKEN", "anycan")
    seen = []

    def post(url, json, headers, timeout):
        seen.append(headers["Authorization"])
        if "items_page" in json["query"]:
            assert json["variables"]["ids"] == ["77"]
            data = {"boards": [{"name": "AnyCan Ai", "items_page": {"items": [
                {"id": "1", "name": "Mayo Clinic", "updated_at": "2026-11-10T10:00:00Z",
                 "group": {"title": "University / Hospital"}, "column_values": []},
                {"id": "2", "name": "ספק אריזות", "updated_at": "2026-11-09T10:00:00Z",
                 "group": {"title": "Suppliers"}, "column_values": []}]}}]}
        else:
            data = {"boards": [{"id": "77", "name": "AnyCan Ai", "type": "board"},
                               {"id": "78", "name": "AnyCan - Inventory", "type": "board"}]}
        return NS(raise_for_status=lambda: None, json=lambda: {"data": data})

    monkeypatch.setattr(tools_monday.requests, "post", post)
    out = tools_monday.get_anycan_monday_items("mayo")
    assert "Mayo Clinic" in out and "ספק אריזות" not in out
    assert set(seen) == {"anycan"}
    assert "Inventory" in tools_monday.get_anycan_monday_items(board="list")


def test_anycan_monday_without_token_names_the_missing_key(monkeypatch):
    monkeypatch.setenv("MONDAY_API_TOKEN", "ao")
    monkeypatch.delenv("MONDAY_ANYCAN_API_TOKEN", raising=False)
    out = [t for t in shula_agent.TOOLS if t.__name__ == "get_monday_updates"][0]()
    assert "MONDAY_ANYCAN_API_TOKEN" in out


def test_monday_updates_show_who_wrote_what(monkeypatch):
    monkeypatch.setenv("MONDAY_ANYCAN_API_TOKEN", "anycan")
    data = {"data": {"updates": [
        {"id": "1", "text_body": "דיברתי עם  המרפאה,\nמחכים לתשובה", "created_at": "2026-11-11T08:00:00Z",
         "creator": {"name": "Yossi Kat"}, "item": {"name": "Mayo Clinic", "board": {"name": "AnyCan Ai"}},
         "replies": [{"text_body": "מעולה", "creator": {"name": "Dana"}}]},
        {"id": "2", "text_body": "הזמנה יצאה", "created_at": "2026-11-10T08:00:00Z",
         "creator": None, "item": None, "replies": []}]}}
    monkeypatch.setattr(tools_monday.requests, "post",
                        lambda *a, **k: NS(raise_for_status=lambda: None, json=lambda: data))
    out = tools_monday.get_monday_updates()
    assert "2026-11-11 | Yossi Kat | Mayo Clinic (לוח AnyCan Ai): דיברתי עם המרפאה, מחכים לתשובה" in out
    assert "↳ Dana: מעולה" in out and "פריט שנמחק" in out
    assert "הזמנה" not in tools_monday.get_monday_updates(search="mayo")


# ---------- יומן הפעולות של Claude ----------
def test_claude_action_log_is_read_newest_first(monkeypatch):
    import tools_claude_log
    csv_text = ("תאריך,שעה,איפה,מה נעשה,פרטים\n"
                "10.11.2026,09:00,מנדיי AnyCan,נוספו 12 מרפאות,בקבוצת University\n"
                "11.11.2026,21:30,יומן,נקבעה פגישה,\n")
    monkeypatch.setattr(tools_claude_log, "_rows", lambda: [r.split(",") for r in csv_text.strip().split("\n")])
    out = tools_claude_log.get_claude_actions()
    assert "<claude_log_data>" in out and out.index("נקבעה פגישה") < out.index("נוספו 12 מרפאות")
    assert "נקבעה פגישה" not in tools_claude_log.get_claude_actions("מנדיי")
    assert "get_claude_actions" in [t.__name__ for t in shula_agent.TOOLS]


# ---------- הודעות קוליות ותמונות בוואטסאפ ----------
def test_voice_note_is_transcribed(monkeypatch):
    monkeypatch.setattr(media, "download", lambda url: (b"ogg", "audio/ogg"))
    monkeypatch.setattr(media, "transcribe", lambda data, mime: "מה יש לי מחר")
    text, files, notes = media.prepare("", [("https://x/1", "audio/ogg")])
    assert "מה יש לי מחר" in text and files == [] and notes == []


def test_whatsapp_photo_reaches_shula_and_shows_typing(monkeypatch):
    monkeypatch.setattr(main, "TWILIO_TOKEN", None)
    monkeypatch.setattr(main, "_from_twilio", lambda *a: True)  # בבדיקות אין Twilio אמיתי
    monkeypatch.setattr(main, "ALLOWED_SENDERS", {"whatsapp:+972500000000"})
    typed, got = [], {}
    monkeypatch.setattr(main.media, "show_typing", typed.append)
    monkeypatch.setattr(main.media, "download", lambda url: (b"jpg", "image/jpeg"))

    def fake_reply(sender, text, attachments=None):
        got["files"] = attachments
        return "רשמתי הוצאה"
    monkeypatch.setattr(main.shula_agent, "reply", fake_reply)
    r = TestClient(main.app).post("/whatsapp", data={
        "Body": "", "From": "whatsapp:+972500000000", "NumMedia": "1", "MessageSid": "SM123",
        "MediaUrl0": "https://api.twilio.com/m/1", "MediaContentType0": "image/jpeg"})
    assert "רשמתי הוצאה" in r.text
    assert typed == ["SM123"] and got["files"][0][0] == "image/jpeg"
