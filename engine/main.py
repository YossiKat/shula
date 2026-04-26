from fastapi import FastAPI
from bot_manager import BotManager
import google.generativeai as genai

app = FastAPI()
manager = BotManager()

@app.post("/ask")
async def ask_shula(user_input: str, bot_name: str = "core_shula"):
    # 1. טעינת ה"מוח" המתאים
    system_prompt = manager.get_bot_prompt(bot_name)
    
    # 2. פנייה ל-Gemini
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(f"{system_prompt}\n\nUser: {user_input}")
    
    return {"response": response.text, "bot_used": bot_name}
