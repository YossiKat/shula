import os

class BotManager:
    def __init__(self, bots_dir="./bots"):
        self.bots_dir = bots_dir

    def get_bot_prompt(self, bot_name):
        """טוען את ההנחיות של הבוט מתוך קובץ בתיקיית הבוטים"""
        file_path = os.path.join(self.bots_dir, f"{bot_name}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def list_available_bots(self):
        """מחזיר רשימה של כל הבוטים המותקנים במערכת"""
        return [f.replace(".txt", "") for f in os.listdir(self.bots_dir) if f.endswith(".txt")]
