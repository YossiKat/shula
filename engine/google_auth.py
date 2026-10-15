"""
חיבור לחשבון גוגל של יוסי (OAuth) — יומן, ג'ימייל, דרייב.
משתני סביבה: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
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

_pending_states: set[str] = set()
_services: dict[str, object] = {}


def is_connected() -> bool:
    return all(os.environ.get(k) for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"))


def credentials():
    from google.oauth2.credentials import Credentials
    if not is_connected():
        raise RuntimeError("חשבון גוגל עדיין לא מחובר לשולה")
    return Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri=TOKEN_URI,
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )


def service(name: str, version: str):
    key = f"{name}:{version}"
    if key not in _services:
        from googleapiclient.discovery import build
        _services[key] = build(name, version, credentials=credentials(), cache_discovery=False)
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


def auth_url(redirect_uri: str) -> str:
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)
    url, _ = _flow(redirect_uri).authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true", state=state
    )
    return url


def exchange_code(redirect_uri: str, code: str, state: str) -> str:
    if state not in _pending_states:
        raise RuntimeError("state לא תקין — התחל שוב מ-/google/auth")
    _pending_states.discard(state)
    flow = _flow(redirect_uri)
    flow.fetch_token(code=code)
    token = flow.credentials.refresh_token
    if not token:
        raise RuntimeError("גוגל לא החזיר refresh token — נסה שוב (prompt=consent)")
    return token
