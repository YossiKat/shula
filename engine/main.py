from fastapi import FastAPI, Form, Header, Request
from fastapi.responses import PlainTextResponse, HTMLResponse, Response
from html import escape
import asyncio
import hmac
import logging
import os
import threading

import google_auth
import media
import shula_agent
import voice

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("shula")

app = FastAPI()

# Twilio — אם יש פרטי חשבון, שולה עונה "ברקע" בלי מגבלת 15 השניות של Twilio
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
# שליחה יזומה דרך Twilio REST דורשת אישור KYC ב-Trust Hub. עד אז — עונים בתוך חלון ה-webhook.
ASYNC_MODE = bool(TWILIO_SID and TWILIO_TOKEN and os.environ.get("TWILIO_ASYNC") == "1")
SYNC_DEADLINE = 12  # שניות — מתחת ל-15 של Twilio

# תשובות שלא הספיקו בזמן — נמסרות בהודעה הבאה של אותו שולח
_pending: dict[str, asyncio.Future] = {}
NUDGES = {"המשך", "נו", "?", "??", "...", "ok", "אוקיי", "טוב"}

# רק המספרים האלה מדברים עם שולה (מופרדים בפסיק). ברירת מחדל: יוסי.
ALLOWED_SENDERS = {
    s.strip() for s in os.environ.get("ALLOWED_SENDERS", "whatsapp:+972547599993").split(",") if s.strip()
}


def _from_twilio(request: Request, form: dict, signature: str) -> bool:
    """בודק שההודעה באמת הגיעה מ-Twilio (חתימה עם ה-Auth Token), ולא ממישהו שמתחזה."""
    if not TWILIO_TOKEN:
        # בלי הטוקן אי אפשר לוודא שההודעה באמת מ-Twilio, ומספר שולח קל לזייף — לכן חוסמים.
        log.error("TWILIO_AUTH_TOKEN missing — refusing /whatsapp (set it in Render)")
        return False
    from twilio.request_validator import RequestValidator
    url = f"{PUBLIC_URL}{request.url.path}"
    if request.url.query:
        url += f"?{request.url.query}"
    return RequestValidator(TWILIO_TOKEN).validate(url, form, signature or "")


def _twiml(text: str) -> PlainTextResponse:
    # תשובה עם הקלטה: קודם הטקסט, ואחריו הודעה נפרדת עם הקול
    audio_url = getattr(text, "audio_url", None)
    clip = f'\n    <Message><Media>{escape(audio_url)}</Media></Message>' if audio_url else ""
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n    <Message>{escape(text)}</Message>{clip}\n</Response>'
    return PlainTextResponse(content=xml, media_type="application/xml")


def _silent() -> PlainTextResponse:
    """תשובה ריקה ל-Twilio — לא נשלחת שום הודעה ליוסי."""
    return PlainTextResponse('<?xml version="1.0" encoding="UTF-8"?><Response/>', media_type="application/xml")


def _send_whatsapp(to: str, text: str) -> None:
    from twilio.rest import Client
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    # וואטסאפ מגביל ל-1600 תווים להודעה
    chunks = [text[i:i + 1500] for i in range(0, len(text), 1500)] or [text]
    for chunk in chunks:
        client.messages.create(from_=TWILIO_FROM, to=to, body=chunk)
    audio_url = getattr(text, "audio_url", None)
    if audio_url:
        client.messages.create(from_=TWILIO_FROM, to=to, media_url=[audio_url])


_push_blocked = False  # נדלק אם Twilio חוסם שליחה יזומה (KYC לא אושר)


def _push_when_ready(sender: str, fut) -> None:
    """כשהתשובה מוכנה — מנסה לשלוח אותה לבד. אם Twilio חוסם, היא נשארת ממתינה ל'המשך'."""
    if fut.cancelled() or fut.exception() is not None:
        return

    def run():
        global _push_blocked
        try:
            _send_whatsapp(sender, fut.result())
            if _pending.get(sender) is fut:
                _pending.pop(sender, None)
        except Exception as e:
            if "compliance" in str(e).lower() or "KYC" in str(e):
                _push_blocked = True
            log.warning("push failed, answer waits for next message: %s", str(e)[:200])

    threading.Thread(target=run, daemon=True).start()


PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://shula-x5mr.onrender.com")


def _keep_awake_loop(interval: int = 600) -> None:
    """Render בחינם נרדם אחרי 15 דקות בלי פניות, וההתעוררות לוקחת כחצי דקה — ואז יוסי מחכה.
    התזמון של גיטהאב לא אמין (רץ כל כמה שעות), לכן שולה פונה לעצמה כל 10 דקות וכך לא נרדמת."""
    import time
    import requests
    while True:
        time.sleep(interval)
        try:
            requests.get(f"{PUBLIC_URL}/", timeout=30)
        except Exception as e:
            log.warning("self keep-awake ping failed: %s", str(e)[:120])


@app.on_event("startup")
def _start_keep_awake() -> None:
    # רק בשרת האמיתי ב-Render (שם RENDER=true), לא בבדיקות; אפשר לכבות עם SHULA_SELF_PING=0
    if os.environ.get("RENDER") and os.environ.get("SHULA_SELF_PING", "1") == "1":
        threading.Thread(target=_keep_awake_loop, daemon=True).start()
        log.info("keep-awake pinger started")


@app.get("/")
def root():
    return {
        "status": "שולה פעילה ✅",
        "model": shula_agent.model_name(),
        "async_mode": ASYNC_MODE,
        "google": google_auth.is_connected(),
        "google_accounts": google_auth.connected_accounts(),
        "social": bool(os.environ.get("METRICOOL_TOKEN")),
    }


def _key_ok(given: str, env_name: str) -> bool:
    """השוואת מפתח סודי בזמן קבוע (כדי שאי אפשר יהיה לנחש אותו אות אחרי אות)."""
    expected = os.environ.get(env_name, "")
    return bool(expected) and hmac.compare_digest((given or "").encode(), expected.encode())


@app.get("/voice/{token}.mp3")
def voice_clip(token: str):
    """מכאן Twilio מוריד את ההקלטה של שולה. הכתובת אקראית ותקפה לשעה."""
    audio = voice.get_clip(token)
    if audio is None:
        return PlainTextResponse("not found", status_code=404)
    return Response(content=audio, media_type="audio/mpeg")


@app.get("/usage")
def usage(days: int = 1, key: str = "", x_report_key: str = Header("")):
    """סיכום שימוש דרך שולה — לדוח השבועי. מוגן במפתח REPORT_KEY (עדיף בכותרת X-Report-Key)."""
    if not _key_ok(x_report_key or key, "REPORT_KEY"):
        return PlainTextResponse("forbidden", status_code=403)
    return shula_agent.usage_report(max(1, min(days, 90)))


# ---------- חיבור חד-פעמי לחשבון גוגל של יוסי ----------

def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{font-family:-apple-system,Arial,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;line-height:1.6}}
code{{display:block;background:#f3f3f3;padding:12px;border-radius:8px;word-break:break-all;direction:ltr;text-align:left}}
a.btn{{display:inline-block;background:#1a73e8;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-size:18px}}</style>
</head><body><h2>{title}</h2>{body}</body></html>""")


@app.get("/google/auth")
def google_auth_start(account: str = "gmail"):
    if not (os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")):
        return _page("חסר מפתח", "<p>עדיין לא הוגדרו GOOGLE_CLIENT_ID ו-GOOGLE_CLIENT_SECRET ב-Render.</p>")
    if account not in google_auth.ACCOUNTS:
        return _page("חשבון לא מוכר", f"<p>אפשר: {', '.join(google_auth.ACCOUNTS)}</p>")
    email = google_auth.ACCOUNTS[account]["email"]
    url = google_auth.auth_url(f"{PUBLIC_URL}/google/callback", account)
    return _page("חיבור שולה לחשבון גוגל", f'<p>לחץ על הכפתור, בחר את החשבון <b>{escape(email)}</b> ואשר.</p><p><a class="btn" href="{url}">התחבר עם גוגל</a></p>')


@app.get("/google/callback")
def google_auth_callback(code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return _page("לא אושר", f"<p>גוגל החזיר: {escape(error or 'אין קוד')}. <a href='/google/auth'>נסה שוב</a></p>")
    try:
        token, account = google_auth.exchange_code(f"{PUBLIC_URL}/google/callback", code, state)
    except Exception as e:
        return _page("שגיאה", f"<p>{escape(str(e)[:300])}</p><p><a href='/google/auth'>נסה שוב</a></p>")
    return _page("כמעט סיימנו ✅", f"""
<p>גוגל אישר. עכשיו צעד אחרון: העתק את הקוד הזה (לחץ עליו כדי להעתיק):</p>
<code id="t" onclick="navigator.clipboard.writeText(this.textContent).then(()=>{{document.getElementById('m').textContent='הועתק ✅'}})">{escape(token)}</code>
<p id="m"></p>
<p>והדבק אותו ב-Render כמשתנה סביבה בשם <b>{google_auth.ACCOUNTS[account]['env']}</b>, ואז Save Changes.</p>
<p><a class="btn" href="https://dashboard.render.com/web/srv-db8a9me89jmc73cqfca0/env">פתח את Render</a></p>
""")


@app.post("/ask")
async def ask_shula(user_input: str, bot_name: str = "core_shula", sender: str = "api",
                    x_shula_key: str = Header("")):
    # לשולה יש גישה למייל וליומן — בלי מפתח סודי, אף אחד לא נכנס מכאן
    if not _key_ok(x_shula_key, "ASK_KEY"):
        return PlainTextResponse("forbidden", status_code=403)
    if bot_name not in shula_agent.manager.list_available_bots():
        return PlainTextResponse("unknown bot", status_code=404)
    try:
        text = await asyncio.to_thread(shula_agent.reply, sender, user_input, bot_name)
    except Exception as e:
        log.exception("Shula failed")
        text = f"שולה נתקלה בבעיה טכנית: {str(e)[:300]}"
    return {"response": text, "bot_used": bot_name}


@app.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(""),
    From: str = Form(""),
    NumMedia: str = Form("0"),
    MessageSid: str = Form(""),
    x_twilio_signature: str = Header(""),
):
    """Twilio WhatsApp Webhook"""
    form = {k: v for k, v in (await request.form()).items()}
    if not _from_twilio(request, form, x_twilio_signature):
        log.warning("rejected /whatsapp: bad Twilio signature")
        return PlainTextResponse("forbidden", status_code=403)
    if From not in ALLOWED_SENDERS:
        log.warning("ignored message from unknown sender …%s", From[-4:])
        return PlainTextResponse('<?xml version="1.0" encoding="UTF-8"?><Response/>', media_type="application/xml")

    user_message = Body.strip()
    attached = []
    try:
        attached = [(form.get(f"MediaUrl{i}", ""), form.get(f"MediaContentType{i}", ""))
                    for i in range(min(int(NumMedia or 0), 5))]
    except ValueError:
        pass
    attached = [(u, t) for u, t in attached if u]

    if not user_message and not attached:
        return _twiml("היי, זו שולה 👋 כתוב לי מה צריך.")

    media.show_typing(MessageSid)  # שלוש הנקודות: "שולה מקלידה..."

    if user_message.lower() in ("reset", "איפוס", "שכחי הכל"):
        shula_agent.forget(From)
        return _twiml("איפסתי את השיחה. מתחילים מחדש 🙂")

    # יש תשובה שממתינה מההודעה הקודמת? נמסור אותה קודם.
    pending = _pending.pop(From, None)
    if pending is not None:
        text = await _collect(pending, SYNC_DEADLINE)
        if text is None:  # עדיין לא מוכנה
            if user_message in NUDGES:
                _pending[From] = pending
            else:
                # הודעה חדשה בזמן המתנה — נשרשר: קודם התשובה הקודמת, אחריה החדשה
                async def chain(first_fut=pending, msg=user_message):
                    first = await first_fut
                    second = await asyncio.to_thread(shula_agent.reply, From, msg)
                    return f"{first}\n\n{second}"
                _pending[From] = asyncio.ensure_future(chain())
                if ASYNC_MODE and not _push_blocked:
                    _pending[From].add_done_callback(lambda f, s=From: _push_when_ready(s, f))
            if ASYNC_MODE and not _push_blocked:
                return _silent()  # התשובה בדרך ותישלח לבד
            return _twiml("עוד רגע, אני עדיין בודקת… שלח לי 'המשך' בעוד כמה שניות.")
        if user_message in NUDGES:
            return _twiml(text)
        # הודעה חדשה אמיתית — נענה על הקודמת, והחדשה תטופל ברקע
        _pending[From] = asyncio.ensure_future(asyncio.to_thread(_answer, From, user_message, attached))
        return _twiml(text + "\n\n(על ההודעה החדשה אענה בהודעה הבאה — שלח 'המשך')")

    # הודעה רגילה — מנסים לענות בתוך הדדליין
    fut = asyncio.ensure_future(asyncio.to_thread(_answer, From, user_message, attached))
    text = await _collect(fut, SYNC_DEADLINE)
    if text is None:
        _pending[From] = fut
        if ASYNC_MODE and not _push_blocked:
            # התשובה תישלח לבד כשתהיה מוכנה (יוסי רואה "מקלידה...") — בלי הודעת "שלח המשך"
            fut.add_done_callback(lambda f, s=From: _push_when_ready(s, f))
            return _silent()
        return _twiml("רגע, בודקת… 🔎 שלח לי 'המשך' בעוד כמה שניות ואמסור את התשובה.")
    return _twiml(text)


def _answer(sender: str, text: str, attached: list) -> str:
    """מכין קבצים (תמלול הודעה קולית, תמונות, PDF) ואז מבקש תשובה משולה."""
    notes = []
    attachments = []
    if attached:
        text, attachments, notes = media.prepare(text, attached)
    if not text and not attachments:
        return "קיבלתי את הקובץ, אבל " + ("; ".join(notes) or "לא הצלחתי להבין אותו") + ". תכתוב לי מה צריך?"
    answer = (shula_agent.reply(sender, text, attachments=attachments) if attachments
              else shula_agent.reply(sender, text))
    full = answer + (f"\n\n({'; '.join(notes)})" if notes else "")
    # יוסי דיבר? שולה עונה גם בקול (רק את התשובה עצמה, בלי ההערות הטכניות)
    if any((t or "").startswith("audio/") for _, t in attached):
        spoken = voice.speak(answer, PUBLIC_URL)
        out = voice.VoiceAnswer(full)
        out.audio_url = spoken.audio_url
        return out
    return full


async def _collect(fut: asyncio.Future, timeout: float):
    """מחכה לתשובה עד timeout. מחזיר טקסט, או None אם עדיין לא מוכנה."""
    try:
        return await asyncio.wait_for(asyncio.shield(fut), timeout=timeout)
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        log.exception("Shula failed")
        return f"שולה נתקלה בבעיה טכנית: {str(e)[:300]}"
