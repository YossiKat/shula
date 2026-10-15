"""
המוח של שולה: Gemini + זיכרון שיחה לכל מספר + כלים (יומן, ג'ימייל, דרייב, רשתות).
"""
import functools
import logging
import os
import threading
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

import google.generativeai as genai

import google_auth
import memory_store
from bot_manager import BotManager
from tools_calendar import CALENDAR_TOOLS
from tools_drive import DRIVE_TOOLS
from tools_gmail import GMAIL_TOOLS
from tools_social import SOCIAL_TOOLS

TZ = ZoneInfo("Asia/Jerusalem")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
MAX_HISTORY = 40  # הודעות שנשמרות לכל מספר

log = logging.getLogger("shula.agent")
manager = BotManager(bots_dir=os.path.join(os.path.dirname(__file__), "bots"))

if os.environ.get("GEMINI_API_KEY"):
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])


def _safe(fn):
    """כלי שנכשל מחזיר הודעת שגיאה כטקסט — כדי ששולה תסביר ליוסי במקום לקרוס."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            log.exception("tool %s failed", fn.__name__)
            return f"שגיאה בכלי {fn.__name__}: {str(e)[:300]}"
    return wrapper


TOOLS = [_safe(t) for t in CALENDAR_TOOLS + GMAIL_TOOLS + DRIVE_TOOLS + SOCIAL_TOOLS]

# זיכרון: {sender: [{"role": "user"|"model", "text": "..."}]}
_histories: dict[str, list] = defaultdict(list)
_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
_loaded = False

DAYS_HE = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]


def _ensure_loaded():
    global _loaded
    if not _loaded:
        _loaded = True
        for sender, msgs in memory_store.load().items():
            _histories[sender] = msgs[-MAX_HISTORY:]
        if _histories:
            log.info("memory loaded for %d senders", len(_histories))


def _system_prompt(bot_name: str) -> str:
    base = manager.get_bot_prompt(bot_name) or ""
    now = datetime.now(TZ)
    google_ok = google_auth.is_connected() or bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"))
    status = [
        "גוגל (יומן, ג'ימייל, דרייב): " + ("מחובר ✅" if google_ok else "עדיין לא מחובר"),
        "רשתות חברתיות: " + ("מחובר ✅" if os.environ.get("METRICOOL_TOKEN") else "לא מחובר — אם יוסי מבקש פוסט, נסחי לו את הטקסט מוכן להעתקה"),
    ]
    return (
        f"{base}\n\n"
        f"עכשיו: יום {DAYS_HE[now.weekday()]}, {now.strftime('%d/%m/%Y %H:%M')} (שעון ישראל).\n"
        f"מצב חיבורים: {' | '.join(status)}\n"
        "כשיוסי שואל על היומן, מיילים או קבצים — השתמשי בכלים, אל תנחשי. "
        "לפני שליחת מייל — תמיד הציגי ליוסי את הנוסח ובקשי אישור; שלחי רק אחרי 'כן'/'שלחי'.\n"
        "תשובות בוואטסאפ: קצרות, בלי Markdown (בלי כוכביות, בלי כותרות)."
    )


def _to_gemini_history(msgs: list) -> list:
    return [{"role": m["role"], "parts": [m["text"]]} for m in msgs if m.get("text")]


def _from_gemini_history(history) -> list:
    out = []
    for content in history:
        text = "".join(getattr(p, "text", "") or "" for p in content.parts).strip()
        if text and content.role in ("user", "model"):
            out.append({"role": content.role, "text": text})
    return out


def reply(sender: str, user_message: str, bot_name: str = "core_shula") -> str:
    """מייצר תשובה עם זיכרון שיחה וכלים. sender = מזהה (מספר הוואטסאפ)."""
    _ensure_loaded()
    with _locks[sender]:
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=_system_prompt(bot_name),
            tools=TOOLS,
            generation_config={"max_output_tokens": 800, "temperature": 0.6},
        )
        chat = model.start_chat(
            history=_to_gemini_history(_histories[sender]),
            enable_automatic_function_calling=True,
        )
        response = chat.send_message(user_message, request_options={"timeout": 60})
        _histories[sender] = _from_gemini_history(chat.history)[-MAX_HISTORY:]
        text = (response.text or "").strip()
    threading.Thread(target=memory_store.save, args=(dict(_histories),), daemon=True).start()
    return text or "לא הצלחתי לנסח תשובה, נסה שוב."


def forget(sender: str) -> None:
    _ensure_loaded()
    _histories.pop(sender, None)
    memory_store.save(dict(_histories))
