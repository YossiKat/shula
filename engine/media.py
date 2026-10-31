"""
קבצים שיוסי שולח בוואטסאפ: תמונות, PDF והודעות קוליות — ו"שלוש הנקודות" (מקלידה...).

- תמונות ו-PDF עוברים ל-Claude כמו שהם (הוא רואה אותם).
- הודעה קולית מתומללת ל-Gemini (חינם על המפתח הקיים) — והטקסט עובר ל-Claude.
- מקלידה...: Twilio מציג ליוסי את שלוש הנקודות עד שהתשובה מגיעה (עד 25 שניות), ומסמן את ההודעה כנקראה.
"""
import base64
import logging
import os
import threading

import requests

log = logging.getLogger("shula.media")

MAX_BYTES = 15 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
DOC_TYPES = {"application/pdf"}


def _twilio_auth():
    key, secret = os.environ.get("TWILIO_API_KEY"), os.environ.get("TWILIO_API_SECRET")
    if key and secret:
        return (key, secret)
    sid, token = os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN")
    return (sid, token) if sid and token else None


def show_typing(message_sid: str) -> None:
    """מציג ליוסי 'מקלידה...' בוואטסאפ. ברקע, ואם לא עובד — פשוט ממשיכים בלי."""
    auth = _twilio_auth()
    if not (message_sid and auth):
        return

    def run():
        try:
            r = requests.post("https://messaging.twilio.com/v3/Indicators/Typing.json", auth=auth, timeout=5,
                              json={"messageId": message_sid, "channel": "whatsapp"})
            if r.status_code >= 300:
                log.info("typing indicator not shown: %s %s", r.status_code, r.text[:200])
        except Exception as e:
            log.info("typing indicator failed: %s", str(e)[:200])

    threading.Thread(target=run, daemon=True).start()


def download(url: str) -> tuple[bytes, str]:
    r = requests.get(url, auth=_twilio_auth(), timeout=20)
    r.raise_for_status()
    if len(r.content) > MAX_BYTES:
        raise ValueError("הקובץ גדול מדי")
    return r.content, (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()


def transcribe(audio: bytes, mime: str) -> str:
    """מתמלל הודעה קולית בעזרת Gemini (עברית או אנגלית)."""
    import google.generativeai as genai
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("אין מפתח Gemini לתמלול")
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(os.environ.get("TRANSCRIBE_MODEL", os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")))
    resp = model.generate_content(
        [{"mime_type": mime or "audio/ogg", "data": audio},
         "תמללי את ההקלטה מילה במילה, בשפה שבה דיברו. החזירי רק את הטקסט, בלי הקדמה."],
        request_options={"timeout": 30},
    )
    return (resp.text or "").strip()


def prepare(text: str, media: list[tuple[str, str]]) -> tuple[str, list[tuple[str, str]], list[str]]:
    """
    media: [(url, content_type)] מ-Twilio.
    מחזיר (טקסט, קבצים ל-Claude [(media_type, base64)], הערות).
    הודעה קולית הופכת לטקסט; תמונה/PDF נשארים קבצים; כל השאר — הערה.
    """
    attachments, notes = [], []
    for url, ctype in media:
        try:
            data, real_type = download(url)
            ctype = (ctype or real_type or "").lower()
            if ctype.startswith("audio/"):
                said = transcribe(data, ctype)
                text = (f"[הודעה קולית מיוסי]: {said}\n{text}").strip() if said else text
                if not said:
                    notes.append("לא הצלחתי להבין את ההקלטה")
            elif ctype in IMAGE_TYPES or ctype in DOC_TYPES:
                attachments.append((ctype, base64.b64encode(data).decode()))
            else:
                notes.append(f"קובץ מסוג {ctype or 'לא ידוע'} — עדיין לא יודעת לקרוא אותו")
        except Exception as e:
            log.exception("media failed")
            notes.append(f"לא הצלחתי לפתוח קובץ: {str(e)[:120]}")
    return text, attachments, notes
