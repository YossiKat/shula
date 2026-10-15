from fastapi import FastAPI, Form, BackgroundTasks
from fastapi.responses import PlainTextResponse
from html import escape
import asyncio
import logging
import os

import shula_agent

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("shula")

app = FastAPI()

# Twilio — אם יש פרטי חשבון, שולה עונה "ברקע" בלי מגבלת 15 השניות של Twilio
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
ASYNC_MODE = bool(TWILIO_SID and TWILIO_TOKEN)
SYNC_DEADLINE = 12  # שניות — מתחת ל-15 של Twilio

EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


def _twiml(text: str) -> PlainTextResponse:
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n    <Message>{escape(text)}</Message>\n</Response>'
    return PlainTextResponse(content=xml, media_type="application/xml")


def _send_whatsapp(to: str, text: str) -> None:
    from twilio.rest import Client
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    # וואטסאפ מגביל ל-1600 תווים להודעה
    chunks = [text[i:i + 1500] for i in range(0, len(text), 1500)] or [text]
    for chunk in chunks:
        client.messages.create(from_=TWILIO_FROM, to=to, body=chunk)


def _answer_in_background(sender: str, user_message: str) -> None:
    try:
        text = shula_agent.reply(sender, user_message)
    except Exception as e:
        log.exception("Shula failed")
        text = f"שולה נתקלה בבעיה טכנית: {str(e)[:300]}"
    try:
        _send_whatsapp(sender, text)
    except Exception:
        log.exception("Twilio send failed")


@app.get("/")
def root():
    return {
        "status": "שולה פעילה ✅",
        "model": shula_agent.GEMINI_MODEL,
        "async_mode": ASYNC_MODE,
        "calendar": bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")),
        "social": bool(os.environ.get("METRICOOL_TOKEN")),
    }


@app.post("/ask")
async def ask_shula(user_input: str, bot_name: str = "core_shula", sender: str = "api"):
    return {"response": shula_agent.reply(sender, user_input, bot_name), "bot_used": bot_name}


@app.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    background: BackgroundTasks,
    Body: str = Form(""),
    From: str = Form(""),
    NumMedia: str = Form("0"),
):
    """Twilio WhatsApp Webhook"""
    user_message = Body.strip()
    if NumMedia not in ("", "0"):
        user_message = (user_message + "\n[יוסי צירף קובץ/תמונה — עדיין אין לי יכולת לראות תמונות, בקשי ממנו לכתוב מה יש שם]").strip()

    if not user_message:
        return _twiml("היי, זו שולה 👋 כתוב לי מה צריך.")

    if user_message.lower() in ("reset", "איפוס", "שכחי הכל"):
        shula_agent.forget(From)
        return _twiml("איפסתי את השיחה. מתחילים מחדש 🙂")

    if ASYNC_MODE:
        background.add_task(_answer_in_background, From, user_message)
        return PlainTextResponse(content=EMPTY_TWIML, media_type="application/xml")

    # מצב סינכרוני (בלי פרטי Twilio) — דדליין קשיח
    try:
        text = await asyncio.wait_for(
            asyncio.to_thread(shula_agent.reply, From, user_message), timeout=SYNC_DEADLINE
        )
    except asyncio.TimeoutError:
        text = "לקח לי יותר מדי זמן לחשוב 😅 שלח שוב בבקשה."
    except Exception as e:
        log.exception("Shula failed")
        text = f"שולה נתקלה בבעיה טכנית: {str(e)[:300]}"
    return _twiml(text)
