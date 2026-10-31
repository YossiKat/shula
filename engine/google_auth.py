"""
חיבור לחשבונות הגוגל של יוסי (OAuth) — יומן, ג'ימייל, דרייב.
משתני סביבה: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
GOOGLE_REFRESH_TOKEN (yossi.kat@gmail.com), GOOGLE_REFRESH_TOKEN_ANYCAN (Yossi@anycan.ai)
"""
import os
import secrets

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.appdata",
]
TOKEN_URI = "https://oauth2.googleapis.com/token"

# החשבון הראשי הוא gmail: היומן "יוסי קט", הזיכרון של שולה ושליחת מיילים כברירת מחדל
ACCOUNTS = {
    "gmail": {"email": "yossi.kat@gmail.com", "env": "GOOGLE_REFRESH_TOKEN", "label": "Gmail"},
    "anycan": {"email": "Yossi@anycan.ai", "env": "GOOGLE_REFRESH_TOKEN_ANYCAN", "label": "AnyCan"},
}
MAIN = "gmail"

_pending_states: dict[str, str] = {}
_services: dict[str, object] = {}


def _account(account: str) -> str:
    key = (account or MAIN).strip().lower()
    if key not in ACCOUNTS:
        raise RuntimeError(f"אין חשבון בשם '{account}'. יש: {', '.join(ACCOUNTS)}")
    return key


def is_connected(account: str = MAIN) -> bool:
    env = ACCOUNTS[_account(account)]["env"]
    return all(os.environ.get(k) for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", env))


def connected_accounts() -> list[str]:
    """החשבונות שמחוברים עכשיו, הראשי ראשון."""
    return [a for a in ACCOUNTS if is_connected(a)]


def label(account: str) -> str:
    return ACCOUNTS[_account(account)]["label"]


def tag_id(account: str, item_id: str) -> str:
    """מזהה של מייל/קובץ מהחשבון הנוסף מקבל קידומת, למשל anycan:18c2…, כדי שנדע מאיפה לקרוא אותו."""
    return item_id if account == MAIN else f"{account}:{item_id}"


def split_id(item_id: str) -> tuple[str, str]:
    acct, sep, rest = (item_id or "").partition(":")
    if sep and acct.lower() in ACCOUNTS:
        return acct.lower(), rest
    return MAIN, item_id


def pick(account: str) -> list[str]:
    """account='all' (או ריק) = כל החשבונות המחוברים; אחרת רק החשבון שביקשו."""
    if (account or "all").strip().lower() in ("all", "הכל", "כולם"):
        return connected_accounts() or [MAIN]
    return [_account(account)]


def credentials(account: str = MAIN):
    from google.oauth2.credentials import Credentials
    account = _account(account)
    if not is_connected(account):
        raise RuntimeError(f"החשבון {ACCOUNTS[account]['email']} עדיין לא מחובר לשולה")
    return Credentials(
        token=None,
        refresh_token=os.environ[ACCOUNTS[account]["env"]],
        token_uri=TOKEN_URI,
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )


def service(name: str, version: str, account: str = MAIN):
    account = _account(account)
    key = f"{account}:{name}:{version}"
    if key not in _services:
        from googleapiclient.discovery import build
        _services[key] = build(name, version, credentials=credentials(account), cache_discovery=False)
    return _services[key]


# ---------- OAuth flow (one-time, in the browser) ----------

def _flow(redirect_uri: str):
    from google_auth_oauthlib.flow import Flow
    client_config = {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": TOKEN_URI,
            "redirect_uris": [redirect_uri],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)


def auth_url(redirect_uri: str, account: str = MAIN) -> str:
    account = _account(account)
    state = secrets.token_urlsafe(16)
    _pending_states[state] = account
    url, _ = _flow(redirect_uri).authorization_url(
        access_type="offline", prompt="consent select_account", include_granted_scopes="true", state=state,
        login_hint=ACCOUNTS[account]["email"],
    )
    return url


def exchange_code(redirect_uri: str, code: str, state: str) -> tuple[str, str]:
    """מחזיר (refresh_token, account)."""
    account = _pending_states.pop(state, None)
    if not account:
        raise RuntimeError("state לא תקין — התחל שוב מ-/google/auth")
    flow = _flow(redirect_uri)
    flow.fetch_token(code=code)
    token = flow.credentials.refresh_token
    if not token:
        raise RuntimeError("גוגל לא החזיר refresh token — נסה שוב (prompt=consent)")
    return token, account
