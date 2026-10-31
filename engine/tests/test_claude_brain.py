from types import SimpleNamespace as NS

import claude_brain
import shula_agent


def _block(**kw):
    b = NS(**kw)
    b.model_dump = lambda exclude_none=True: kw
    return b


class _FakeClient:
    """Claude מזויף: בפעם הראשונה מבקש את הכלי, בפעם השנייה עונה."""

    def __init__(self):
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        usage = NS(input_tokens=100, output_tokens=20, cache_read_input_tokens=50, cache_creation_input_tokens=0)
        if len(self.calls) == 1:
            return NS(stop_reason="tool_use", usage=usage, content=[
                _block(type="tool_use", id="t1", name="get_events_for_date", input={"date_iso": "2026-11-01"})])
        return NS(stop_reason="end_turn", usage=usage, content=[_block(type="text", text="מחר יש לך זום ב-10:00")])


def test_tool_schema_reads_signature_and_docstring():
    from tools_calendar import create_calendar_event
    s = claude_brain.tool_schema(create_calendar_event)
    assert s["name"] == "create_calendar_event"
    assert s["input_schema"]["required"] == ["title", "start_iso"]
    assert s["input_schema"]["properties"]["duration_minutes"]["type"] == "integer"
    assert "YYYY-MM-DD" in s["input_schema"]["properties"]["start_iso"]["description"]


def test_all_shula_tools_have_valid_schemas():
    schemas, by_name = claude_brain.build_tools(shula_agent.TOOLS)
    assert len(schemas) == len(shula_agent.TOOLS) == len(by_name)
    assert "cache_control" in schemas[-1]


def test_tool_loop_runs_tool_and_returns_answer(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(claude_brain, "_client", fake)
    seen = []

    def get_events_for_date(date_iso: str) -> str:
        """אירועים בתאריך. date_iso = YYYY-MM-DD"""
        seen.append(date_iso)
        return "10:00 זום"

    out = claude_brain.run("קבוע", "משתנה", [], "מה יש לי מחר?", [get_events_for_date])
    assert out["text"] == "מחר יש לך זום ב-10:00"
    assert out["tools"] == ["get_events_for_date"] and seen == ["2026-11-01"]
    tool_result = fake.calls[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["content"] == "10:00 זום"
    assert fake.calls[0]["system"][0]["cache_control"]["type"] == "ephemeral"
    assert out["usage"]["in"] == 200 and out["usage"]["cache_read"] == 100


def test_history_alternates_and_starts_with_user():
    msgs = claude_brain._to_messages([
        {"role": "model", "text": "שלום"},
        {"role": "user", "text": "א"}, {"role": "user", "text": "ב"},
        {"role": "model", "text": "ג"}, {"role": "user", "text": "ד"},
    ])
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert msgs[0]["content"] == "א\n\nב"


def test_falls_back_to_gemini_when_claude_fails(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(shula_agent, "_reply_claude", lambda *a: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(shula_agent, "_reply_gemini", lambda *a: ("תשובה מגמיני", []))
    monkeypatch.setattr(shula_agent.conversation_log, "log_exchange", lambda *a, **k: None)
    monkeypatch.setattr(shula_agent.memory_store, "save", lambda *a: None)
    assert shula_agent.reply("test-fallback", "היי") == "תשובה מגמיני"


def test_self_check_is_in_prompt(monkeypatch):
    monkeypatch.setattr(shula_agent.google_auth, "is_connected", lambda: False)
    assert "בקרה עצמית" in shula_agent._system_prompt("core_shula")
