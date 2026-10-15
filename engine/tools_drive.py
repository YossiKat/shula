"""כלי גוגל דרייב לשולה — חיפוש וקריאת קבצים (דרך חשבון גוגל של יוסי)."""
import io

import google_auth

EXPORT = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def _drive():
    return google_auth.service("drive", "v3")


def search_drive(query: str, max_results: int = 10) -> str:
    """מחפש קבצים בדרייב של יוסי לפי מילים מהשם או מהתוכן. מחזיר שם, סוג, תאריך עדכון, מזהה (id) וקישור."""
    q = f"fullText contains '{query.replace(chr(39), ' ')}' and trashed = false"
    res = _drive().files().list(
        q=q, pageSize=min(max_results, 20), orderBy="modifiedTime desc",
        fields="files(id,name,mimeType,modifiedTime,webViewLink)",
    ).execute()
    files = res.get("files", [])
    if not files:
        return "לא נמצאו קבצים."
    return "\n".join(
        f"[{f['id']}] {f['name']} ({f['mimeType'].split('/')[-1].replace('vnd.google-apps.', '')}, {f['modifiedTime'][:10]}) {f.get('webViewLink', '')}"
        for f in files
    )


def read_drive_file(file_id: str) -> str:
    """קורא את תוכן הקובץ (Google Docs / Sheets / Slides / טקסט) לפי המזהה (id) מ-search_drive."""
    from googleapiclient.http import MediaIoBaseDownload
    meta = _drive().files().get(fileId=file_id, fields="name,mimeType").execute()
    mime = meta["mimeType"]
    if mime in EXPORT:
        req = _drive().files().export_media(fileId=file_id, mimeType=EXPORT[mime])
    elif mime.startswith("text/") or mime in ("application/json",):
        req = _drive().files().get_media(fileId=file_id)
    else:
        return f"הקובץ '{meta['name']}' הוא מסוג {mime} — אני יודעת לקרוא רק מסמכים, גיליונות, מצגות וטקסט."
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    text = buf.getvalue().decode("utf-8", errors="replace")
    return f"{meta['name']}:\n{text[:6000]}"


DRIVE_TOOLS = [search_drive, read_drive_file]
