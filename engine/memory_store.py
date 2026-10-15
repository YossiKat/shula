"""
זיכרון ארוך טווח לשולה — נשמר כקובץ JSON בתיקיית האפליקציה בדרייב של יוסי (appDataFolder),
כך שהשיחה שורדת גם כשהשרת מתאתחל. אם גוגל לא מחובר — נשמר בזיכרון בלבד.
"""
import io
import json
import logging
import threading

import google_auth

log = logging.getLogger("shula.memory")
FILENAME = "shula_memory.json"
_file_id: str | None = None
_lock = threading.Lock()


def _find_file():
    global _file_id
    if _file_id:
        return _file_id
    drive = google_auth.service("drive", "v3")
    res = drive.files().list(spaces="appDataFolder", q=f"name = '{FILENAME}'", fields="files(id)").execute()
    files = res.get("files", [])
    if files:
        _file_id = files[0]["id"]
    return _file_id


def load() -> dict:
    """מחזיר {sender: [ {role, text}, ... ]} או {} אם אין."""
    if not google_auth.is_connected():
        return {}
    try:
        fid = _find_file()
        if not fid:
            return {}
        data = google_auth.service("drive", "v3").files().get_media(fileId=fid).execute()
        return json.loads(data.decode("utf-8") if isinstance(data, bytes) else data)
    except Exception:
        log.exception("memory load failed")
        return {}


def save(histories: dict) -> None:
    if not google_auth.is_connected():
        return
    from googleapiclient.http import MediaIoBaseUpload
    with _lock:
        try:
            drive = google_auth.service("drive", "v3")
            media = MediaIoBaseUpload(io.BytesIO(json.dumps(histories, ensure_ascii=False).encode("utf-8")),
                                      mimetype="application/json", resumable=False)
            global _file_id
            fid = _find_file()
            if fid:
                drive.files().update(fileId=fid, media_body=media).execute()
            else:
                f = drive.files().create(body={"name": FILENAME, "parents": ["appDataFolder"]},
                                         media_body=media, fields="id").execute()
                _file_id = f["id"]
        except Exception:
            log.exception("memory save failed")
