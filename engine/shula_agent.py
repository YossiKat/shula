"""
המוח של שולה: Gemini + זיכרון שיחה לכל מספר + כלים (יומן, רשתות).
"""
import functools
import logging
import os
import threading
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

import google.generativeai as genai

from bot_manager import BotManager
from tools_calendar import CALENDAR_TOOLS
from tools_social import SOCIAL_TOOLS

TZ = ZoneInfo("Asia/Jerusalem")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
MAX_HISTORY = 30  # הודעות (כולל קריאות לכלים) שנשמרות לכל מספר

manager = BotManager(bots_dir=os.path.join(os.path.dirname(__file__), "bots"))

if os.environ.get("GEMINI_API_KEY"):
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

log = logging.getLogger("shula.agent")


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


TOOLS = [_safe(t) for t in CALENDAR_TOOLS + SOCIAL_TOOLS]

_histories: dict[str, list] = defaultdict(list)
_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)

DAYS_HE = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]


def _system_prompt(bot_name: str) -> str:
    base = manager.get_bot_prompt(bot_name) or ""
    now = datetime.now(TZ)
    status = []
    status.append("יומן גוגל: " + ("מחובר ✅" if os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") else "עדיין לא מחובר"))
    status.append("רשתות חברתיות (Metricool): " + ("מחובר ✅" if os.environ.get("METRICOOL_TOKEN") else "עדיין לא מחובר"))
    return (
        f"{base}\n\n"
        f"עכשיו: יום {DAYS_HE[now.weekday()]}, {now.strftime('%d/%m/%Y %H:%M')} (שעון ישראל).\n"
        f"מצב חיבורים: {' | '.join(status)}\n"
        "כשיוסי שואל על היומן או מבקש לקבוע משהו — השתמשי בכלים, אל תנחשי. "
        "כשכלי לא מחובר — אמרי לו בקצרה שזה עדיין לא מחובר.\n"
        "תשובות בוואטסאפ: קצרות, בלי Markdown (בלי כוכביות, בלי כותרות)."
    )


def reply(sender: str, user_message: str, bot_name: str = "core_shula") -> str:
    """מייצר תשובה עם זיכרון שיחה וכלים. sender = מזהה (מספר הוואטסאפ)."""
    with _locks[sender]:
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=_system_prompt(bot_name),
            tools=TOOLS,
            generation_config={"max_output_tokens": 600, "temperature": 0.6},
        )
        chat = model.start_chat(
            history=list(_histories[sender]),
            enable_automatic_function_calling=True,
        )
        response = chat.send_message(user_message, request_options={"timeout": 40})
        _histories[sender] = list(chat.history)[-MAX_HISTORY:]
        text = (response.text or "").strip()
        return text or "לא הצלחתי לנסח תשובה, נסה שוב."


def forget(sender: str) -> None:
    _histories.pop(sender, None)
