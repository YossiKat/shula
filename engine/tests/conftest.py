import os
import sys

# הבדיקות רצות מתוך engine/ — כדי ש-import main / shula_agent יעבדו כמו בשרת
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
