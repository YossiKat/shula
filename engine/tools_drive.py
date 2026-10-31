"""כלי גוגל דרייב לשולה — חיפוש וקריאת קבצים בשני החשבונות של יוסי (Gmail ו-AnyCan)."""
import io

import google_auth

EXPORT = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def _drive(account: str = google_auth.MAIN):
    return google_auth.service("drive", "v3", account)


def search_drive(query: str, max_results: int = 10, account: str = "all") -> str:
    """מחפש קבצים בדרייב של יוסי לפי מילים מהשם או מהתוכן.
    account: 'all' = בשני החשבונות (ברירת מחדל), 'gmail' = yossi.kat@gmail.com, 'anycan' = Yossi@anycan.ai.
    מחזיר שם, סוג, תאריך עדכון, מזהה (id) וקישור."""
    q = f"fullText contains '{query.replace(chr(39), ' ')}' and trashed = false"
    accounts = google_auth.pick(account)
    lines = []
    for acct in accounts:
        res = _drive(acct).files().list(
            q=q, pageSize=min(max_results, 20), orderBy="modifiedTime desc",
            fields="files(id,name,mimeType,modifiedTime,webViewLink)",
        ).execute()
        tag = f"({google_auth.label(acct)}) " if len(accounts) > 1 else ""
        lines += [
            f"[{google_auth.tag_id(acct, f['id'])}] {tag}{f['name']} ({f['mimeType'].split('/')[-1].replace('vnd.google-apps.', '')}, {f['modifiedTime'][:10]}) {f.get('webViewLink', '')}"
            for f in res.get("files", [])
        ]
    return "\n".join(lines) if lines else "לא נמצאו קבצים."


def read_drive_file(file_id: str) -> str:
    """קורא את תוכן הקובץ (Google Docs / Sheets / Slides / טקסט) לפי המזהה (id) מ-search_drive (כולל הקידומת anycan: אם יש)."""
    from googleapiclient.http import MediaIoBaseDownload
    acct, file_id = google_auth.split_id(file_id)
    drive = _drive(acct)
    meta = drive.files().get(fileId=file_id, fields="name,mimeType").execute()
    mime = meta["mimeType"]
    if mime in EXPORT:
        req = drive.files().export_media(fileId=file_id, mimeType=EXPORT[mime])
    elif mime.startswith("text/") or mime in ("application/json",):
        req = drive.files().get_media(fileId=file_id)
    else:
        return f"הקובץ '{meta['name']}' הוא מסוג {mime} — אני יודעת לקרוא רק מסמכים, גיליונות, מצגות וטקסט."
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    text = buf.getvalue().decode("utf-8", errors="replace")
    return f"<drive_data>\n{meta['name']}:\n{text[:6000]}\n</drive_data>"


DRIVE_TOOLS = [search_drive, read_drive_file]
