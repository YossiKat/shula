"""
כלי רשתות חברתיות לשולה — דרך Metricool (מותג "AnyCan Tech").
מחובר שם: Facebook, Instagram (yossikat), LinkedIn, TikTok (yossi.kat), YouTube, Google Business Profile.
משתני סביבה: METRICOOL_TOKEN (חובה), METRICOOL_USER_ID, METRICOOL_BLOG_ID
"""
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

BASE = "https://app.metricool.com/api"
USER_ID = os.environ.get("METRICOOL_USER_ID", "5527140")
BLOG_ID = os.environ.get("METRICOOL_BLOG_ID", "7146223")
TZ_NAME = "Asia/Jerusalem"
TZ = ZoneInfo(TZ_NAME)

NETWORKS = {"facebook", "instagram", "linkedin", "tiktok", "youtube", "gmb"}
HEB = {"פייסבוק": "facebook", "אינסטגרם": "instagram", "לינקדאין": "linkedin",
       "טיקטוק": "tiktok", "יוטיוב": "youtube"}


def _headers():
    token = os.environ.get("METRICOOL_TOKEN")
    if not token:
        raise RuntimeError("הרשתות החברתיות עדיין לא מחוברות (חסר METRICOOL_TOKEN)")
    return {"X-Mc-Auth": token, "Content-Type": "application/json"}


def _params(extra: dict | None = None):
    p = {"userId": USER_ID, "blogId": BLOG_ID}
    if extra:
        p.update(extra)
    return p


def _norm_networks(networks: str) -> list[str]:
    out = []
    for n in networks.replace(",", " ").split():
        n = HEB.get(n, n.lower())
        if n in NETWORKS and n not in out:
            out.append(n)
    return out


def schedule_social_post(text: str, networks: str, publish_at_iso: str, image_url: str = "") -> str:
    """מתזמן פוסט ברשתות החברתיות של יוסי דרך Metricool.
    networks: רשימת רשתות מופרדות ברווח, מתוך: facebook instagram linkedin tiktok youtube.
    publish_at_iso: מועד הפרסום YYYY-MM-DDTHH:MM (שעון ישראל), חייב להיות בעתיד.
    image_url: כתובת ציבורית של תמונה/וידאו (חובה לאינסטגרם ולטיקטוק).
    """
    nets = _norm_networks(networks)
    if not nets:
        return "לא זיהיתי רשת. אפשר: facebook, instagram, linkedin, tiktok, youtube."
    if ("instagram" in nets or "tiktok" in nets) and not image_url:
        return "לאינסטגרם ולטיקטוק חובה תמונה או וידאו — שלח לי קישור ציבורי לקובץ."
    when = datetime.fromisoformat(publish_at_iso)
    if when.replace(tzinfo=TZ) <= datetime.now(TZ):
        return "המועד כבר עבר — תן לי שעה בעתיד."

    info = {
        "text": text,
        "providers": [{"network": n} for n in nets],
        "publicationDate": {"dateTime": when.strftime("%Y-%m-%dT%H:%M:%S"), "timezone": TZ_NAME},
        "media": [image_url] if image_url else [],
        "mediaAltText": [],
        "autoPublish": True,
        "draft": False,
        "shortener": False,
        "hasNotReadNotes": False,
        "descendants": [],
        "firstCommentText": "",
        "smartLinkData": {"ids": []},
    }
    data_keys = {"facebook": ("facebookData", {"type": "POST"}),
                 "instagram": ("instagramData", {"type": "POST"}),
                 "linkedin": ("linkedinData", {"type": "post"}),
                 "tiktok": ("tiktokData", {}),
                 "youtube": ("youtubeData", {"title": text[:90], "type": "video", "privacy": "public", "madeForKids": False}),
                 "gmb": ("gmbData", {"type": "publication"})}
    for n in nets:
        key, val = data_keys[n]
        info[key] = val

    r = requests.post(f"{BASE}/v2/scheduler/posts", headers=_headers(), params=_params(), json=info, timeout=30)
    if r.status_code >= 300:
        return f"Metricool החזיר שגיאה {r.status_code}: {r.text[:300]}"
    return f"תוזמן ל-{when.strftime('%d/%m %H:%M')} ב-{', '.join(nets)} ✅"


def list_scheduled_posts(days_ahead: int = 14) -> str:
    """מחזיר את הפוסטים שכבר מתוזמנים ברשתות החברתיות ב-days_ahead הימים הקרובים."""
    now = datetime.now(TZ)
    params = _params({
        "start": now.strftime("%Y-%m-%dT00:00:00"),
        "end": (now + timedelta(days=days_ahead)).strftime("%Y-%m-%dT23:59:59"),
        "timezone": TZ_NAME,
    })
    r = requests.get(f"{BASE}/v2/scheduler/posts", headers=_headers(), params=params, timeout=30)
    if r.status_code >= 300:
        return f"Metricool החזיר שגיאה {r.status_code}: {r.text[:300]}"
    posts = r.json()
    if isinstance(posts, dict):
        posts = posts.get("data", posts.get("posts", []))
    if not posts:
        return "אין פוסטים מתוזמנים."
    lines = []
    for p in posts[:20]:
        nets = ",".join(pr.get("network", "") for pr in p.get("providers", []))
        when = (p.get("publicationDate") or {}).get("dateTime", "")
        lines.append(f"{when[:16]} [{nets}] {str(p.get('text', ''))[:80]}")
    return "\n".join(lines)


SOCIAL_TOOLS = [schedule_social_post, list_scheduled_posts]
