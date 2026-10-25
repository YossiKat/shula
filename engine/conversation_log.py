"""
יומן שיחות לבדיקה השבועית: כל שאלה ותשובה של שולה נשמרת כמייל בתווית "שולה/יומן שיחות"
בג'ימייל של יוסי — לא בתיבת הדואר הנכנס, בלי התראה, ומסומן כנקרא.
כך הבדיקה השבועית יכולה לעבור על השיחות בלי גישה לשרת.
"""
import base64
import logging
import threading
from datetime import datetime
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import google_auth

log = logging.getLogger("shula.convlog")
LABEL = "שולה/יומן שיחות"
TZ = ZoneInfo("Asia/Jerusalem")
_label_id: str | None = None


def _gmail():
    return google_auth.service("gmail", "v1")


def _get_label_id() -> str:
    global _label_id
    if _label_id:
        return _label_id
    labels = _gmail().users().labels().list(userId="me").execute().get("labels", [])
    for lab in labels:
        if lab.get("name") == LABEL:
            _label_id = lab["id"]
            return _label_id
    created = _gmail().users().labels().create(userId="me", body={
        "name": LABEL, "labelListVisibility": "labelShow", "messageListVisibility": "hide",
    }).execute()
    _label_id = created["id"]
    return _label_id


def format_entry(question: str, answer: str, tools: list[str], seconds: float) -> tuple[str, str]:
    """מחזיר (נושא, גוף) לרשומה אחת."""
    now = datetime.now(TZ)
    slow = " ⏳" if seconds > 12 else ""
    subject = f"שולה | {now:%d.%m %H:%M}{slow} | {question[:60]}"
    body = (
        f"זמן: {now:%d.%m.%Y %H:%M}\n"
        f"זמן תגובה: {seconds:.1f} שניות" + (" (יוסי קיבל 'רגע, בודקת' וחיכה)" if seconds > 12 else "") + "\n"
        f"כלים שהופעלו: {', '.join(tools) if tools else 'אין'}\n\n"
        f"יוסי כתב:\n{question}\n\n"
        f"שולה ענתה:\n{answer}\n"
    )
    return subject, body


def _insert(subject: str, body: str) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = "yossi.kat@gmail.com"
    msg["From"] = "Shula log <yossi.kat@gmail.com>"
    msg["Subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    _gmail().users().messages().insert(
        userId="me", internalDateSource="receivedTime",
        body={"raw": raw, "labelIds": [_get_label_id()]},
    ).execute()


def log_exchange(question: str, answer: str, tools: list[str], seconds: float) -> None:
    """שומר ברקע. אף פעם לא מפיל את התשובה ליוסי."""
    if not google_auth.is_connected():
        return
    subject, body = format_entry(question, answer, tools, seconds)

    def run():
        try:
            _insert(subject, body)
        except Exception:
            log.exception("conversation log failed")

    threading.Thread(target=run, daemon=True).start()
