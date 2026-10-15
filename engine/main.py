from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse
from bot_manager import BotManager
import google.generativeai as genai
import os

app = FastAPI()
manager = BotManager(bots_dir=os.path.join(os.path.dirname(__file__), "bots"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


@app.get("/")
def root():
    return {"status": "שולה פעילה ✅"}


@app.post("/ask")
async def ask_shula(user_input: str, bot_name: str = "core_shula"):
    system_prompt = manager.get_bot_prompt(bot_name)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(f"{system_prompt}\n\nUser: {user_input}")
    return {"response": response.text, "bot_used": bot_name}


@app.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    Body: str = Form(""),
    From: str = Form(""),
):
    """Twilio WhatsApp Webhook"""
    user_message = Body.strip()

    try:
        system_prompt = manager.get_bot_prompt("core_shula")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"{system_prompt}\n\nUser: {user_message}")
        reply = response.text.strip()
    except Exception as e:
        reply = f"שולה נתקלה בבעיה טכנית: {str(e)}"

    # TwiML response
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{reply}</Message>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")
