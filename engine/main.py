from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from bot_manager import BotManager
import google.generativeai as genai
from html import escape
import asyncio
import os

app = FastAPI()
manager = BotManager(bots_dir=os.path.join(os.path.dirname(__file__), "bots"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Twilio מחכה לתשובה עד 15 שניות — חייבים להישאר מתחת לזה
GEMINI_TIMEOUT_SECONDS = 12


def ask_gemini(bot_name: str, user_message: str) -> str:
    system_prompt = manager.get_bot_prompt(bot_name) or ""
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=system_prompt)
    response = model.generate_content(
        user_message,
        request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
    )
    return response.text.strip()


@app.get("/")
def root():
    return {"status": "שולה פעילה ✅", "model": GEMINI_MODEL}


@app.post("/ask")
async def ask_shula(user_input: str, bot_name: str = "core_shula"):
    return {"response": ask_gemini(bot_name, user_input), "bot_used": bot_name}


@app.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    Body: str = Form(""),
    From: str = Form(""),
):
    """Twilio WhatsApp Webhook"""
    user_message = Body.strip()

    if not user_message:
        reply = "היי, זו שולה 👋 כתוב לי מה צריך."
    else:
        try:
            # דדליין קשיח — אחרת Twilio מוותר ולא נשלחת תשובה בכלל
            reply = await asyncio.wait_for(
                asyncio.to_thread(ask_gemini, "core_shula", user_message),
                timeout=GEMINI_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            reply = "לקח לי יותר מדי זמן לחשוב 😅 שלח שוב בבקשה."
        except Exception as e:
            reply = f"שולה נתקלה בבעיה טכנית: {str(e)[:300]}"

    # TwiML — חובה לברוח תווים מיוחדים כדי שה-XML לא יישבר
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{escape(reply)}</Message>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")
