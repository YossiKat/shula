"""
הקול של שולה: כשיוסי שולח הודעה קולית, היא עונה גם בהקלטה בקול אנושי (ElevenLabs).

- בלי ELEVENLABS_API_KEY הכול כבוי ושולה עונה בטקסט בלבד, כמו תמיד.
- כל תקלה בקול לא מפילה את התשובה: הטקסט תמיד נשלח.
- ההקלטה נשמרת בזיכרון לזמן קצר, בכתובת אקראית שאי אפשר לנחש, כדי ש-Twilio יוכל להוריד אותה.
"""
import logging
import os
import re
import secrets
import threading
import time

import requests

log = logging.getLogger("shula.voice")

DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # קול נשי מוכן של ElevenLabs. אפשר להחליף ב-ELEVENLABS_VOICE_ID
MODELS = ("eleven_v4", "eleven_v3")  # שניהם תומכים בעברית; הראשון הכי אנושי, השני גיבוי
MAX_CHARS = 1000  # תשובה ארוכה יותר נשארת טקסט: פחות נעים לשמוע, ויקר יותר
KEEP_SECONDS = 3600
MAX_CLIPS = 20

_clips: dict[str, tuple[float, bytes]] = {}
_lock = threading.Lock()

_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


class VoiceAnswer(str):
    """טקסט רגיל של תשובה, שאפשר לצרף אליו קישור להקלטה."""
    audio_url: str | None = None


def enabled() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def clean_for_speech(text: str) -> str:
    """מסיר מהטקסט מה שנשמע רע בקול: קישורים, סימני עיצוב ואימוג'י."""
    text = re.sub(r"https?://\S+", "", text)
    text = _EMOJI.sub("", text)
    text = text.replace("₪", " שקלים ")
    text = re.sub(r"[*_#`>|~]", "", text)
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.M)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return re.sub(r"\n{2,}", "\n", text).strip()


def synthesize(text: str) -> bytes:
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    wanted = os.environ.get("ELEVENLABS_MODEL")
    last_error = "no model tried"
    for model in ((wanted,) if wanted else MODELS):
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
            json={"text": text, "model_id": model, "language_code": "he"},
            timeout=25,
        )
        if r.status_code == 200 and r.content:
            return r.content
        last_error = f"{model}: {r.status_code} {r.text[:200]}"
        log.warning("voice failed on %s", last_error)
    raise RuntimeError(last_error)


def _store(audio: bytes) -> str:
    token = secrets.token_urlsafe(24)
    now = time.time()
    with _lock:
        for old in [k for k, (t, _) in _clips.items() if now - t > KEEP_SECONDS]:
            del _clips[old]
        while len(_clips) >= MAX_CLIPS:
            del _clips[min(_clips, key=lambda k: _clips[k][0])]
        _clips[token] = (now, audio)
    return token


def get_clip(token: str) -> bytes | None:
    with _lock:
        item = _clips.get(token)
    if not item or time.time() - item[0] > KEEP_SECONDS:
        return None
    return item[1]


def speak(answer: str, public_url: str) -> VoiceAnswer:
    """מחזיר את התשובה, ואם אפשר — עם קישור להקלטה שלה. אף פעם לא זורק שגיאה."""
    result = VoiceAnswer(answer)
    if not enabled():
        return result
    spoken = clean_for_speech(answer)
    if not spoken or len(spoken) > MAX_CHARS:
        return result
    try:
        result.audio_url = f"{public_url}/voice/{_store(synthesize(spoken))}.mp3"
    except Exception as e:
        log.warning("voice skipped, sending text only: %s", str(e)[:200])
    return result
