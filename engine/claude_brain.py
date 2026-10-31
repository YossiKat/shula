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

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5")  # הזול והמהיר; לשדרוג: CLAUDE_MODEL=claude-sonnet-5-5
MAX_TOOL_ROUNDS = 8
# הערכת מחיר לדוח השימוש בלבד (דולר למיליון טוקנים) — אפשר לעדכן ב-Render בלי לשנות קוד
# מוח כפול: שאלות מורכבות עוברות לגרסה החכמה
SMART_MODEL = os.environ.get("CLAUDE_SMART_MODEL", "claude-sonnet-5-5")
PRICES = {  # הערכה בלבד, לדוח השימוש (דולר למיליון טוקנים: קלט, פלט)
    CLAUDE_MODEL: (float(os.environ.get("CLAUDE_PRICE_IN", "0.10")), float(os.environ.get("CLAUDE_PRICE_OUT", "0.50"))),
    SMART_MODEL: (float(os.environ.get("CLAUDE_SMART_PRICE_IN", "3")), float(os.environ.get("CLAUDE_SMART_PRICE_OUT", "15"))),
}
# חיפוש באינטרנט (כלי של Anthropic). אם החשבון לא מאפשר — נכבה לבד ושולה ממשיכה בלעדיו.
WEB_SEARCH = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3,
              "user_location": {"type": "approximate", "city": "Ramat HaSharon", "country": "IL",
                                "timezone": "Asia/Jerusalem"}}
_web_search_on = os.environ.get("SHULA_WEB_SEARCH", "1") == "1"

# בקשות שבהן כדאי לחשוב יותר (ניסוח, תכנון, סיכום, ניתוח)
_SMART_HINTS = (
    "נסח", "ניסוח", "כתבי", "תכתבי", "מכתב", "פוסט", "סכמי", "תסכמי", "סיכום", "תכנני", "תכנון", "תתכנני",
    "השווי", "תשווי", "השוואה", "תמליצי", "המלצה", "תייעצי", "עצה", "למה", "איך כדאי", "מה דעתך", "נתחי",
    "ניתוח", "רעיון", "רעיונות", "אסטרטגיה", "הצעת מחיר", "תשובה ל", "תעני ל", "תחשבי", "תבדקי לעומק",
    "monday", "מאנדיי", "מנדיי",
)


def choose_model(message: str, has_images: bool = False, correction: bool = False) -> str:
    """הגרסה הזולה לשאלות פשוטות; החכמה לבקשות מורכבות, לתמונות ולתיקונים."""
    m = (message or "").strip()
    if has_images or correction or len(m) > 160 or any(h in m for h in _SMART_HINTS):
        return SMART_MODEL
    return CLAUDE_MODEL

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


def _user_content(user_message: str, images) -> list | str:
    if not images:
        return user_message
    blocks = [{"type": "document" if mt == "application/pdf" else "image",
               "source": {"type": "base64", "media_type": mt, "data": data}} for mt, data in images]
    blocks.append({"type": "text", "text": user_message or "מה יש בתמונה? אם זו קבלה — הציעי לרשום אותה כהוצאה ביומן."})
    return blocks


def run(static_system: str, dynamic_system: str, history: list[dict], user_message: str,
        fns, images=None, model: str | None = None) -> dict:
    """
    history: [{"role": "user"|"model", "text": ...}] — השיחה הקודמת (טקסט בלבד).
    images: [(media_type, base64)] — תמונות שיוסי שלח.
    מחזיר {"text", "tools", "model", "usage": {"in","out","cache_read","usd"}}.
    """
    global _web_search_on
    model = model or CLAUDE_MODEL
    schemas, by_name = build_tools(fns)
    system = [
        {"type": "text", "text": static_system, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": dynamic_system},
    ]
    messages = _to_messages(history) + [{"role": "user", "content": _user_content(user_message, images)}]
    tools_used: list[str] = []
    usage = {"in": 0, "out": 0, "cache_read": 0}
    text = ""

    for _ in range(MAX_TOOL_ROUNDS):
        tools = schemas + ([WEB_SEARCH] if _web_search_on else [])
        try:
            resp = client().messages.create(
                model=model, max_tokens=2000, system=system, tools=tools, messages=messages,
            )
        except Exception as e:
            if _web_search_on and "web_search" in str(e):
                log.warning("web search not available, turning it off: %s", str(e)[:200])
                _web_search_on = False
                continue
            raise
        u = resp.usage
        usage["in"] += (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
        usage["out"] += u.output_tokens or 0
        text = _text_of(resp.content) or text

        tools_used += ["web_search" for b in resp.content if getattr(b, "type", "") == "server_tool_use"]
        if resp.stop_reason == "pause_turn":  # חיפוש ארוך באינטרנט — ממשיכים מאותה נקודה
            messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in resp.content]})
            continue
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

    p_in, p_out = PRICES.get(model, PRICES[CLAUDE_MODEL])
    usage["usd"] = round((usage["in"] * p_in + usage["out"] * p_out + usage["cache_read"] * p_in * 0.1) / 1_000_000, 5)
    return {"text": text, "tools": tools_used, "usage": usage, "model": model}


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
