"""
פעולה על משימות המטה ישר מהוואטסאפ — אותה "רצפת ייצור" שיש במטה, רק בהודעה.
יוסי כותב לשולה למשל "סוזן, בוצע: לשלוח לנטלי", "מה באיחור אצל ג׳סיקה?", "להזיז את השיחה עם רובר למחר ב-11",
"הערה על הודעה לעיתונות: לחכות לרזאן", "ג׳סיקה: משימה חדשה – לבדוק את הרילס של דטו ביום שני ב-10".
הכלים עובדים על היומן "יוסי קט": משימה פתוחה = אירוע אדום (colorId 11) בלי ✅/בוצע/❌/בוטל.
שינויים לא שולחים מייל למוזמנים (sendUpdates="none").
"""
from datetime import datetime, timedelta

import tools_calendar

WINDOW_BACK, WINDOW_AHEAD = 14, 8


def _hq():
    import hq
    return hq


def _open_tasks() -> list[dict]:
    hq = _hq()
    now = datetime.now(tools_calendar.TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    evs = hq._events(now - timedelta(days=WINDOW_BACK), now + timedelta(days=WINDOW_AHEAD))
    out = []
    for e in evs:
        if e.get("status") == "cancelled" or not hq._is_open_task(e):
            continue
        when, all_day = hq._start(e)
        out.append({"e": e, "when": when, "all_day": all_day, "title": e.get("summary") or "",
                    "diff": (when.date() - now.date()).days, "dept": hq.dept_of(e.get("summary") or "")})
    out.sort(key=lambda t: t["when"])
    return out


def _dept_key(name: str) -> str:
    """'סוזן' / 'admin' / '🗂️' → מפתח המחלקה. ריק אם לא זוהתה."""
    name = (name or "").strip().strip(":,").replace("'", "׳")
    if not name:
        return ""
    for key, nm, emo, words in _hq().DEPTS:
        if name in (key, nm, emo) or nm in name or any(w and w in name for w in words[:3]):
            return key
    return ""


def _label(t: dict) -> str:
    d = t["when"]
    return f"{d.strftime('%d.%m')}{'' if t['all_day'] else ' ' + d.strftime('%H:%M')} – {t['title']}"


def _find(title_query: str) -> tuple[list[dict], str]:
    words = [w for w in (title_query or "").replace("–", " ").split() if len(w) > 1]
    if not words:
        return [], "כתבי כמה מילים מהשם של המשימה."
    hits = [t for t in _open_tasks() if all(w in t["title"] for w in words)]
    if not hits:  # ניסיון שני: לפחות חצי מהמילים
        need = max(1, len(words) // 2)
        hits = [t for t in _open_tasks() if sum(w in t["title"] for w in words) >= need]
    if not hits:
        return [], f"לא מצאתי משימה פתוחה עם '{title_query}' (בדקתי 14 יום אחורה ושבוע קדימה)."
    if len(hits) > 1:
        return hits, "מצאתי כמה משימות שמתאימות — על איזו מדובר?\n" + "\n".join(f"{i + 1}. {_label(t)}" for i, t in enumerate(hits[:8]))
    return hits, ""


def department_tasks(department: str = "") -> str:
    """תמונת מצב של המשימות הפתוחות לפי מחלקה — כמו רצפת הייצור במטה.
    department ריק = סיכום של כל המחלקות (באיחור / היום / מחר / השבוע).
    department = שם ראש המחלקה או המחלקה (למשל 'סוזן', 'ג׳סיקה', 'admin') = רשימת המשימות של אותה מחלקה, לפי שלב.
    מתאים לשאלות כמו 'מה קורה במטה?', 'מה באיחור אצל סוזן?', 'מה יש לג׳סיקה השבוע?'."""
    hq, tasks = _hq(), _open_tasks()
    stage = lambda t: "late" if t["diff"] < 0 else "today" if t["diff"] == 0 else "tom" if t["diff"] == 1 else "week"
    names = {"late": "🔴 באיחור", "today": "🟠 היום", "tom": "🔵 מחר", "week": "🗓️ השבוע"}
    key = _dept_key(department)
    if department and not key:
        return f"לא זיהיתי מחלקה בשם '{department}'. המחלקות: " + ", ".join(n for _, n, _, _ in hq.DEPTS)
    if key:
        mine = [t for t in tasks if t["dept"] == key]
        nm = next(f"{e} {n}" for k, n, e, _ in hq.DEPTS if k == key)
        if not mine:
            return f"{nm}: אין משימות פתוחות 🎉"
        lines = [f"{nm} – {len(mine)} משימות פתוחות:"]
        for s in ("late", "today", "tom", "week"):
            part = [t for t in mine if stage(t) == s]
            if part:
                lines.append(f"\n{names[s]} ({len(part)}):")
                lines += [f"• {_label(t)}" for t in part[:10]]
        return "\n".join(lines)
    lines = ["🏭 רצפת הייצור – משימות פתוחות לפי מחלקה:"]
    for k, n, e, _ in hq.DEPTS:
        mine = [t for t in tasks if t["dept"] == k]
        if not mine:
            continue
        c = {s: sum(stage(t) == s for t in mine) for s in names}
        light = "🔴" if c["late"] else "🟠" if c["today"] > 3 else "🟢"
        lines.append(f"{light} {e} {n}: באיחור {c['late']} · היום {c['today']} · מחר {c['tom']} · השבוע {c['week']}")
    return "\n".join(lines) if len(lines) > 1 else "אין משימות פתוחות במטה 🎉"


def mark_task_done(title_query: str, result: str = "") -> str:
    """מסמנת משימה פתוחה ביומן כבוצעה: הכותרת מקבלת '✅ בוצע:' והצבע הופך לתכלת. לא נשלח מייל למוזמנים.
    title_query = כמה מילים משם המשימה (למשל 'לשלוח לנטלי'). result = תוצאה קצרה להוסיף בסוגריים (לא חובה).
    אם יש כמה משימות מתאימות — מחזירה רשימה, ואז צריך לשאול את יוסי איזו."""
    hits, msg = _find(title_query)
    if msg:
        return msg
    e = hits[0]["e"]
    title = "✅ בוצע: " + (e.get("summary") or "") + (f" ({result.strip()})" if result.strip() else "")
    tools_calendar._svc().events().patch(calendarId=tools_calendar.CALENDAR_ID, eventId=e["id"], sendUpdates="none",
                                         body={"summary": title, "colorId": "7"}).execute()
    return f"סומן בוצע ✅ {_label(hits[0])}"


def move_task(title_query: str, new_start_iso: str) -> str:
    """מזיזה משימה פתוחה לזמן חדש ושומרת על האורך שלה. new_start_iso בפורמט YYYY-MM-DDTHH:MM (שעון ישראל),
    או רק YYYY-MM-DD כדי להשאיר את אותה שעה ביום אחר. לא נשלח מייל למוזמנים."""
    hits, msg = _find(title_query)
    if msg:
        return msg
    t, e = hits[0], hits[0]["e"]
    tz = tools_calendar.TZ
    if t["all_day"]:
        d = datetime.fromisoformat(new_start_iso[:10]).date()
        body = {"start": {"date": d.isoformat()}, "end": {"date": (d + timedelta(days=1)).isoformat()}}
    else:
        old_end = datetime.fromisoformat((e.get("end") or {}).get("dateTime") or t["when"].isoformat()).astimezone(tz)
        length = max(old_end - t["when"], timedelta(minutes=15))
        if len(new_start_iso) <= 10:
            start = datetime.fromisoformat(new_start_iso).replace(hour=t["when"].hour, minute=t["when"].minute, tzinfo=tz)
        else:
            start = datetime.fromisoformat(new_start_iso).replace(tzinfo=tz)
        body = {"start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
                "end": {"dateTime": (start + length).isoformat(), "timeZone": "Asia/Jerusalem"}}
    ev = tools_calendar._svc().events().patch(calendarId=tools_calendar.CALENDAR_ID, eventId=e["id"],
                                              sendUpdates="none", body=body).execute()
    return f"הוזז ⏭️ {tools_calendar._fmt(ev)}"


def add_task_note(title_query: str, note: str) -> str:
    """מוסיפה הערה של יוסי לתיאור של משימה פתוחה ביומן (בלי למחוק את מה שכבר כתוב). title_query = מילים משם המשימה."""
    if not (note or "").strip():
        return "מה ההערה?"
    hits, msg = _find(title_query)
    if msg:
        return msg
    e = hits[0]["e"]
    stamp = datetime.now(tools_calendar.TZ).strftime("%d.%m %H:%M")
    desc = ((e.get("description") or "") + "\n\n" if e.get("description") else "") + f"📝 הערה של יוסי ({stamp}, מהוואטסאפ): {note.strip()}"
    tools_calendar._svc().events().patch(calendarId=tools_calendar.CALENDAR_ID, eventId=e["id"], sendUpdates="none",
                                         body={"description": desc}).execute()
    return f"ההערה נשמרה 📝 {_label(hits[0])}"


def new_department_task(department: str, task: str, start_iso: str, duration_minutes: int = 15) -> str:
    """יוצרת משימה חדשה ביומן בשם מחלקה (אדום, עם תזכורת 10 דקות לפני), כך שהיא מופיעה בקו של המחלקה במטה.
    department = שם ראש המחלקה או המחלקה ('סוזן', 'ג׳סיקה'...). task = מה צריך לעשות. start_iso = YYYY-MM-DDTHH:MM."""
    hq, key = _hq(), _dept_key(department)
    if not key:
        return f"לא זיהיתי מחלקה בשם '{department}'. המחלקות: " + ", ".join(n for _, n, _, _ in hq.DEPTS)
    if not (task or "").strip():
        return "מה המשימה?"
    nm, emo = next((n, e) for k, n, e, _ in hq.DEPTS if k == key)
    start = datetime.fromisoformat(start_iso).replace(tzinfo=tools_calendar.TZ)
    body = {"summary": f"{emo} {nm}: {task.strip()}",
            "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jerusalem"},
            "end": {"dateTime": (start + timedelta(minutes=max(5, int(duration_minutes or 15)))).isoformat(), "timeZone": "Asia/Jerusalem"},
            "colorId": "11", "description": "נוצר מהוואטסאפ דרך שולה.",
            "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]}}
    ev = tools_calendar._svc().events().insert(calendarId=tools_calendar.CALENDAR_ID, body=body).execute()
    return f"נוצרה משימה ➕ {tools_calendar._fmt(ev)}"


TASK_TOOLS = [department_tasks, mark_task_done, move_task, add_task_note, new_department_task]
