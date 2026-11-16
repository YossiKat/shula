"""
כניסה למטה בלי שולה: Face ID / טביעת אצבע (passkey) או קוד גיבוי.

- את ה-Face ID מגדירים פעם אחת, מתוך המטה, אחרי כניסה רגילה בקישור משולה.
- קוד הגיבוי נוצר מתוך המטה ומוצג פעם אחת בלבד. נשמר רק "טביעה" שלו (hash), לא הקוד עצמו.
- 5 טעויות בקוד ברבע שעה — הקוד ננעל לרבע שעה.
הכול נשמר בקובץ JSON בתיקיית האפליקציה בדרייב של יוסי (appDataFolder), ובזיכרון אם גוגל לא מחובר.
"""
import base64
import hashlib
import hmac
import io
import json
import logging
import os
import secrets
import threading
import time
from urllib.parse import urlparse

import webauthn
from webauthn.helpers.structs import (AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
                                      ResidentKeyRequirement, UserVerificationRequirement)

import google_auth

log = logging.getLogger("shula.hq_auth")
FILENAME = "hq_auth.json"
MAX_FAILS = 5
LOCK_SECONDS = 15 * 60
CHALLENGE_TTL = 5 * 60

_lock = threading.Lock()
_cache: dict | None = None
_file_id: str | None = None
_challenges: dict[str, tuple[bytes, float, str]] = {}  # id -> (challenge, expiry, kind)
_fails: list[float] = []


# ---------- שמירה ----------

def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _drive():
    return google_auth.service("drive", "v3")


def _find_file():
    global _file_id
    if not _file_id:
        res = _drive().files().list(spaces="appDataFolder", q=f"name = '{FILENAME}'", fields="files(id)").execute()
        files = res.get("files", [])
        _file_id = files[0]["id"] if files else None
    return _file_id


def load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    data = {}
    if google_auth.is_connected():
        try:
            fid = _find_file()
            if fid:
                raw = _drive().files().get_media(fileId=fid).execute()
                data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        except Exception:
            log.exception("hq auth load failed")
    data.setdefault("passkeys", [])
    _cache = data
    return data


def save(data: dict) -> None:
    global _cache, _file_id
    _cache = data
    if not google_auth.is_connected():
        return
    from googleapiclient.http import MediaIoBaseUpload
    try:
        media = MediaIoBaseUpload(io.BytesIO(json.dumps(data).encode()), mimetype="application/json", resumable=False)
        fid = _find_file()
        if fid:
            _drive().files().update(fileId=fid, media_body=media).execute()
        else:
            f = _drive().files().create(body={"name": FILENAME, "parents": ["appDataFolder"]},
                                        media_body=media, fields="id").execute()
            _file_id = f["id"]
    except Exception:
        log.exception("hq auth save failed")


def status() -> dict:
    d = load()
    return {"passkeys": len(d["passkeys"]), "backup": bool(d.get("backup")),
            "names": [p.get("name", "") for p in d["passkeys"]]}


# ---------- כתובת האתר ----------

def _origin() -> str:
    return os.environ.get("PUBLIC_URL", "https://shula-x5mr.onrender.com").rstrip("/")


def _rp_id() -> str:
    return urlparse(_origin()).hostname or "localhost"


# ---------- אתגרים (challenge) חד-פעמיים ----------

def _new_challenge(kind: str) -> tuple[str, bytes]:
    now = time.time()
    for k in [k for k, v in _challenges.items() if v[1] < now]:
        _challenges.pop(k, None)
    cid, ch = secrets.token_urlsafe(16), secrets.token_bytes(32)
    _challenges[cid] = (ch, now + CHALLENGE_TTL, kind)
    return cid, ch


def _take_challenge(cid: str, kind: str) -> bytes | None:
    item = _challenges.pop(cid or "", None)
    if not item or item[1] < time.time() or item[2] != kind:
        return None
    return item[0]


# ---------- Face ID / passkey ----------

def register_options() -> dict:
    d = load()
    cid, ch = _new_challenge("reg")
    opts = webauthn.generate_registration_options(
        rp_id=_rp_id(), rp_name="המטה של שולה", user_name="yossi", user_display_name="יוסי",
        user_id=hashlib.sha256(b"hq-yossi").digest()[:16], challenge=ch,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED, user_verification=UserVerificationRequirement.REQUIRED),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=_unb64(p["id"])) for p in d["passkeys"]])
    return {"cid": cid, "options": json.loads(webauthn.options_to_json(opts))}


def register_verify(cid: str, credential: dict, name: str = "") -> dict:
    ch = _take_challenge(cid, "reg")
    if not ch:
        return {"ok": False, "msg": "עבר יותר מדי זמן. נסה שוב."}
    try:
        v = webauthn.verify_registration_response(credential=credential, expected_challenge=ch,
                                                  expected_rp_id=_rp_id(), expected_origin=_origin(),
                                                  require_user_verification=True)
    except Exception as e:
        log.warning("passkey registration failed: %s", e)
        return {"ok": False, "msg": "ההגדרה לא הצליחה. נסה שוב."}
    with _lock:
        d = load()
        d["passkeys"].append({"id": _b64(v.credential_id), "pk": _b64(v.credential_public_key),
                              "count": v.sign_count, "name": (name or "מכשיר")[:40],
                              "added": time.strftime("%d.%m.%Y")})
        save(d)
    return {"ok": True, "msg": "✅ Face ID הוגדר. מעכשיו אפשר להיכנס בלי שולה."}


def login_options() -> dict:
    d = load()
    if not d["passkeys"]:
        return {"ok": False, "msg": "עוד לא הוגדר Face ID. בפעם הראשונה נכנסים בקישור משולה."}
    cid, ch = _new_challenge("auth")
    opts = webauthn.generate_authentication_options(
        rp_id=_rp_id(), challenge=ch, user_verification=UserVerificationRequirement.REQUIRED,
        allow_credentials=[PublicKeyCredentialDescriptor(id=_unb64(p["id"])) for p in d["passkeys"]])
    return {"ok": True, "cid": cid, "options": json.loads(webauthn.options_to_json(opts))}


def login_verify(cid: str, credential: dict) -> bool:
    ch = _take_challenge(cid, "auth")
    if not ch or not isinstance(credential, dict):
        return False
    with _lock:
        d = load()
        key = next((p for p in d["passkeys"] if p["id"] == credential.get("rawId") or p["id"] == credential.get("id")), None)
        if not key:
            return False
        try:
            v = webauthn.verify_authentication_response(
                credential=credential, expected_challenge=ch, expected_rp_id=_rp_id(), expected_origin=_origin(),
                credential_public_key=_unb64(key["pk"]), credential_current_sign_count=key.get("count", 0),
                require_user_verification=True)
        except Exception as e:
            log.warning("passkey login failed: %s", e)
            return False
        key["count"] = v.new_sign_count
        key["last"] = time.strftime("%d.%m.%Y %H:%M")
        save(d)
    return True


def remove_passkeys() -> dict:
    with _lock:
        d = load()
        d["passkeys"] = []
        save(d)
    return {"ok": True, "msg": "כל ה-Face ID נמחקו. אפשר להגדיר מחדש."}


# ---------- קוד גיבוי ----------

def _hash(code: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", code.encode(), salt, 200_000).hex()


def _norm(code: str) -> str:
    return "".join(ch for ch in str(code or "") if ch.isdigit())


def new_backup_code() -> dict:
    digits = "".join(secrets.choice("0123456789") for _ in range(12))
    salt = secrets.token_bytes(16)
    with _lock:
        d = load()
        d["backup"] = {"salt": salt.hex(), "hash": _hash(digits, salt), "added": time.strftime("%d.%m.%Y")}
        save(d)
    shown = "-".join(digits[i:i + 4] for i in range(0, 12, 4))
    return {"ok": True, "code": shown, "msg": "שמור את הקוד במקום בטוח. הוא מוצג רק עכשיו."}


def locked() -> bool:
    now = time.time()
    _fails[:] = [t for t in _fails if t > now - LOCK_SECONDS]
    return len(_fails) >= MAX_FAILS


def check_backup_code(code: str) -> str:
    """'ok' / 'bad' / 'locked' / 'none'"""
    if locked():
        return "locked"
    b = load().get("backup")
    if not b:
        return "none"
    if hmac.compare_digest(_hash(_norm(code), bytes.fromhex(b["salt"])), b["hash"]):
        _fails.clear()
        return "ok"
    _fails.append(time.time())
    return "locked" if locked() else "bad"
