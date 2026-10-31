"""כלי ג'ימייל לשולה — חיפוש, קריאה, טיוטה ושליחה, בשני החשבונות של יוסי (Gmail ו-AnyCan)."""
import base64
import html
import re
from email.mime.text import MIMEText
from email.utils import parseaddr

import google_auth


def _gmail(account: str = google_auth.MAIN):
    return google_auth.service("gmail", "v1", account)


def _header(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _body_text(payload: dict) -> str:
    """מוציא טקסט קריא מהמייל (מעדיף text/plain, אחרת מנקה HTML)."""
    def walk(part):
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and mime in ("text/plain", "text/html"):
            txt = base64.urlsafe_b64decode(data + "===").decode("utf-8", errors="replace")
            if mime == "text/html":
                txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", txt, flags=re.S | re.I)
                txt = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", txt, flags=re.I)
                txt = html.unescape(re.sub(r"<[^>]+>", " ", txt))
            return (mime, txt)
        for sub in part.get("parts", []) or []:
            r = walk(sub)
            if r:
                return r
        return None

    found = walk(payload)
    if not found:
        return ""
    txt = re.sub(r"[ \t]+", " ", found[1])
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt.strip()


def search_emails(query: str = "is:unread", max_results: int = 10, account: str = "all") -> str:
    """מחפש מיילים של יוסי. query בתחביר של Gmail, למשל: 'is:unread', 'from:shahar', 'newer_than:2d', 'subject:חשבונית'.
    account: 'all' = בשני החשבונות (ברירת מחדל), 'gmail' = yossi.kat@gmail.com, 'anycan' = Yossi@anycan.ai.
    מחזיר רשימה עם מזהה (id) לכל מייל, ואיזה חשבון."""
    accounts = google_auth.pick(account)
    lines = []
    for acct in accounts:
        gm = _gmail(acct)
        res = gm.users().messages().list(userId="me", q=query, maxResults=min(max_results, 20)).execute()
        for mid in [m["id"] for m in res.get("messages", [])]:
            m = gm.users().messages().get(
                userId="me", id=mid, format="metadata", metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            sender = parseaddr(_header(m, "From"))
            who = sender[0] or sender[1]
            tag = f"({google_auth.label(acct)}) " if len(accounts) > 1 else ""
            lines.append(f"[{google_auth.tag_id(acct, mid)}] {tag}{who} — {_header(m, 'Subject') or '(ללא נושא)'} — {m.get('snippet', '')[:80]}")
    return "\n".join(lines) if lines else "לא נמצאו מיילים."


def read_email(email_id: str) -> str:
    """קורא מייל מלא לפי המזהה (id) שהתקבל מ-search_emails (כולל הקידומת anycan: אם יש)."""
    acct, mid = google_auth.split_id(email_id)
    m = _gmail(acct).users().messages().get(userId="me", id=mid, format="full").execute()
    body = _body_text(m.get("payload", {}))[:4000]
    return (f"<email_data>\nחשבון: {google_auth.ACCOUNTS[acct]['email']}\nמאת: {_header(m, 'From')}\nאל: {_header(m, 'To')}\nתאריך: {_header(m, 'Date')}\n"
            f"נושא: {_header(m, 'Subject')}\n\n{body}\n</email_data>")


def _make_raw(to: str, subject: str, body: str, reply_to_id: str = "", account: str = google_auth.MAIN) -> dict:
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to_id:
        orig = _gmail(account).users().messages().get(
            userId="me", id=reply_to_id, format="metadata", metadataHeaders=["Message-ID"]
        ).execute()
        mid = _header(orig, "Message-ID")
        if mid:
            msg["In-Reply-To"] = mid
            msg["References"] = mid
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if reply_to_id:
        payload["threadId"] = _gmail(account).users().messages().get(userId="me", id=reply_to_id, format="minimal").execute().get("threadId")
    return payload


def _sender(from_account: str, reply_to_email_id: str) -> tuple[str, str]:
    """מאיזה חשבון יוצא המייל: תשובה יוצאת מהחשבון של המייל המקורי; אחרת from_account (ברירת מחדל gmail)."""
    if reply_to_email_id:
        return google_auth.split_id(reply_to_email_id)
    return google_auth._account(from_account), ""


def create_email_draft(to: str, subject: str, body: str, from_account: str = "gmail") -> str:
    """יוצר טיוטת מייל (לא שולח). to = כתובת הנמען. from_account: 'gmail' (yossi.kat@gmail.com) או 'anycan' (Yossi@anycan.ai)."""
    acct, _ = _sender(from_account, "")
    d = _gmail(acct).users().drafts().create(userId="me", body={"message": _make_raw(to, subject, body, account=acct)}).execute()
    return f"טיוטה נוצרה ב-{google_auth.ACCOUNTS[acct]['email']} (id {d.get('id')}) אל {to}: {subject}"


def send_email(to: str, subject: str, body: str, reply_to_email_id: str = "", from_account: str = "gmail") -> str:
    """שולח מייל מהחשבון של יוסי. חובה לקבל אישור מפורש מיוסי לפני השליחה.
    reply_to_email_id = מזהה מייל כדי לענות באותו שרשור (התשובה יוצאת מאותו חשבון).
    from_account: 'gmail' (yossi.kat@gmail.com, ברירת מחדל) או 'anycan' (Yossi@anycan.ai). כשיש ספק מאיזה חשבון — לשאול את יוסי."""
    import shula_agent
    if not shula_agent.user_approved():
        return ("עוד לא נשלח. קודם הראי ליוסי את הנוסח המלא (נמען, נושא, תוכן) "
                "ובקשי שיענה 'כן, שלחי'. רק אחרי התשובה שלו אפשר לשלוח.")
    acct, reply_id = _sender(from_account, reply_to_email_id)
    _gmail(acct).users().messages().send(userId="me", body=_make_raw(to, subject, body, reply_id, acct)).execute()
    return f"נשלח מ-{google_auth.ACCOUNTS[acct]['email']} אל {to}: {subject} ✅"


GMAIL_TOOLS = [search_emails, read_email, create_email_draft, send_email]
