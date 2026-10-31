"""
המוח של שולה על Claude (Anthropic).
נבחר אוטומטית כשמוגדר ANTHROPIC_API_KEY ב-Render. בלי המפתח — שולה ממשיכה עם Gemini.

מה כאן:
- הופך את פונקציות הכלים (יומן, ג'ימייל, דרייב, רשתות) להגדרות כלים ש-Claude מבין.
- לולאת כלים: Claude מבקש כלי → מריצים → מחזירים לו תוצאה → עד שיש תשובה.
- Prompt caching: ההוראות הקבועות והכלים נשמרים בקאש של Anthropic, כך שכל הודעה מהירה וזולה יותר.
"""
import inspect
import logging
import os
import re
import typing

log = logging.getLogger("shula.claude")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_TOOL_ROUNDS = 8
# הערכת מחיר לדוח השימוש בלבד (דולר למיליון טוקנים) — אפשר לעדכן ב-Render בלי לשנות קוד
PRICE_IN = float(os.environ.get("CLAUDE_PRICE_IN", "3")) / 1_000_000
PRICE_OUT = float(os.environ.get("CLAUDE_PRICE_OUT", "15")) / 1_000_000
PRICE_CACHE_READ = PRICE_IN * 0.1

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}
_client = None


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def client():
    global _client
    if _client is None:
        import anthropic
        # תשובה שלא נכנסת ב-12 השניות של וואטסאפ ממשיכה ברקע ונמסרת ב"המשך" — לכן מותר לחכות יותר
        _client = anthropic.Anthropic(timeout=float(os.environ.get("CLAUDE_TIMEOUT", "30")), max_retries=1)
    return _client


def tool_schema(fn) -> dict:
    """בונה הגדרת כלי ל-Claude מתוך החתימה וה-docstring של הפונקציה."""
    target = inspect.unwrap(fn)
    sig = inspect.signature(target)
    hints = typing.get_type_hints(target)
    props, required = {}, []
    doc = inspect.getdoc(target) or target.__name__
    for name, p in sig.parameters.items():
        t = _JSON_TYPES.get(hints.get(name, str), "string")
        prop = {"type": t}
        # אם ה-docstring מסביר את הפרמטר ("name: ..." או "name = ...") — מצרפים את ההסבר
        m = re.search(rf"\b{re.escape(name)}\s*[:=]\s*([^\n]+)", doc)
        if m:
            prop["description"] = m.group(1).strip()[:300]
        if p.default is inspect.Parameter.empty:
            required.append(name)
        else:
            prop["default"] = p.default
        props[name] = prop
    return {
        "name": target.__name__,
        "description": doc[:1000],
        "input_schema": {"type": "object", "properties": props, "required": required},
    }


def build_tools(fns) -> tuple[list[dict], dict]:
    schemas = [tool_schema(f) for f in fns]
    if schemas:
        schemas[-1]["cache_control"] = {"type": "ephemeral"}  # הכלים קבועים — נשמרים בקאש
    by_name = {inspect.unwrap(f).__name__: f for f in fns}
    return schemas, by_name


def _text_of(content) -> str:
    return "".join(getattr(b, "text", "") or "" for b in content if getattr(b, "type", "") == "text").strip()


def run(static_system: str, dynamic_system: str, history: list[dict], user_message: str,
        fns) -> dict:
    """
    history: [{"role": "user"|"model", "text": ...}] — השיחה הקודמת (טקסט בלבד).
    מחזיר {"text", "tools", "usage": {"in","out","cache_read","usd"}}.
    """
    schemas, by_name = build_tools(fns)
    system = [
        {"type": "text", "text": static_system, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": dynamic_system},
    ]
    messages = _to_messages(history) + [{"role": "user", "content": user_message}]
    tools_used: list[str] = []
    usage = {"in": 0, "out": 0, "cache_read": 0}
    text = ""

    for _ in range(MAX_TOOL_ROUNDS):
        resp = client().messages.create(
            model=CLAUDE_MODEL, max_tokens=1500, system=system, tools=schemas, messages=messages,
        )
        u = resp.usage
        usage["in"] += (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
        usage["out"] += u.output_tokens or 0
        text = _text_of(resp.content) or text

        calls = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
        if resp.stop_reason != "tool_use" or not calls:
            break
        messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in resp.content]})
        results = []
        for call in calls:
            tools_used.append(call.name)
            fn = by_name.get(call.name)
            out = fn(**(call.input or {})) if fn else f"אין כלי בשם {call.name}"
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": str(out)[:20000]})
        messages.append({"role": "user", "content": results})

    usage["usd"] = round(usage["in"] * PRICE_IN + usage["out"] * PRICE_OUT + usage["cache_read"] * PRICE_CACHE_READ, 5)
    return {"text": text, "tools": tools_used, "usage": usage}


def _to_messages(history: list[dict]) -> list[dict]:
    """ממיר את הזיכרון לפורמט של Claude: user/assistant לסירוגין, מתחיל ב-user."""
    out: list[dict] = []
    for m in history:
        t = (m.get("text") or "").strip()
        if not t:
            continue
        role = "assistant" if m.get("role") in ("model", "assistant") else "user"
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n\n" + t  # שתי הודעות רצופות מאותו צד מתאחדות
        else:
            out.append({"role": role, "content": t})
    while out and out[0]["role"] != "user":
        out.pop(0)
    if out and out[-1]["role"] == "user":
        # תשובה שלא נשמרה — כדי שההודעה החדשה לא תתמזג עם הישנה
        out.append({"role": "assistant", "content": "(לא נשמרה תשובה)"})
    return out
