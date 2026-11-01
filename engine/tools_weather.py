"""
כלי מזג אוויר לשולה — תחזית עד 14 ימים דרך Open-Meteo (חינמי, בלי מפתח).
ברירת מחדל: רמת השרון. אפשר גם עיר אחרת (בארץ או בחו"ל).
"""
from datetime import date

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
HOME = ("רמת השרון", 32.1461, 34.8394)
HOME_NAMES = {"", "רמת השרון", "רמה\"ש", "רמה״ש", "בית", "הבית", "ramat hasharon"}
DAYS_HE = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]

# קודי מזג אוויר של WMO → עברית פשוטה
WMO = {
    0: "☀️ בהיר", 1: "🌤️ בהיר ברובו", 2: "⛅ מעונן חלקית", 3: "☁️ מעונן",
    45: "🌫️ ערפל", 48: "🌫️ ערפל",
    51: "🌦️ טפטוף קל", 53: "🌦️ טפטוף", 55: "🌦️ טפטוף חזק",
    61: "🌧️ גשם קל", 63: "🌧️ גשם", 65: "🌧️ גשם חזק",
    66: "🌧️ גשם קר", 67: "🌧️ גשם קר חזק",
    71: "🌨️ שלג קל", 73: "🌨️ שלג", 75: "🌨️ שלג כבד", 77: "🌨️ שלג",
    80: "🌦️ ממטרים קלים", 81: "🌦️ ממטרים", 82: "⛈️ ממטרים חזקים",
    85: "🌨️ ממטרי שלג", 86: "🌨️ ממטרי שלג חזקים",
    95: "⛈️ סופת רעמים", 96: "⛈️ סופת רעמים עם ברד", 99: "⛈️ סופת רעמים עם ברד",
}


def _place(city: str):
    name = (city or "").strip()
    if name.lower() in HOME_NAMES:
        return HOME
    r = requests.get(GEOCODE_URL, params={"name": name, "count": 1, "language": "he"}, timeout=10)
    r.raise_for_status()
    res = (r.json() or {}).get("results") or []
    if not res:
        raise ValueError(f"לא מצאתי מקום בשם '{name}'")
    p = res[0]
    label = p.get("name", name) + (f", {p['country']}" if p.get("country") else "")
    return label, p["latitude"], p["longitude"]


def get_weather_forecast(days: int = 7, city: str = "רמת השרון") -> str:
    """תחזית מזג אוויר יומית: מצב, טמפרטורה מינימום/מקסימום, סיכוי לגשם, כמות גשם ורוח. days = כמה ימים (1–14, ברירת מחדל 7). city = עיר (ברירת מחדל רמת השרון; אפשר גם עיר בחו"ל, למשל 'אמסטרדם'). זה הכלי הנכון לכל שאלה על מזג אוויר, גשם, רוח או 'מה ללבוש'."""
    days = max(1, min(int(days or 7), 14))
    label, lat, lon = _place(city)
    r = requests.get(FORECAST_URL, params={
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": days,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
                 "precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max",
        "wind_speed_unit": "kmh",
    }, timeout=10)
    r.raise_for_status()
    d = (r.json() or {}).get("daily") or {}
    lines = [f"תחזית ל{label} ({days} ימים, מקור: Open-Meteo):"]
    for i, day in enumerate(d.get("time", [])):
        dt = date.fromisoformat(day)
        cond = WMO.get(d["weather_code"][i], "—")
        tmin, tmax = round(d["temperature_2m_min"][i]), round(d["temperature_2m_max"][i])
        rain_p = d.get("precipitation_probability_max", [None] * 99)[i]
        rain_mm = d.get("precipitation_sum", [0] * 99)[i] or 0
        wind = round(d.get("wind_speed_10m_max", [0] * 99)[i] or 0)
        gust = round(d.get("wind_gusts_10m_max", [0] * 99)[i] or 0)
        rain = f"גשם {rain_p}%" if rain_p is not None else ""
        if rain_mm >= 0.5:
            rain += f" ({rain_mm:.0f} מ\"מ)"
        lines.append(f"• {DAYS_HE[dt.weekday()]} {dt.day}.{dt.month}: {cond}, {tmin}°–{tmax}°, {rain}, רוח עד {wind} קמ\"ש (משבים {gust})")
    return "\n".join(lines)


WEATHER_TOOLS = [get_weather_forecast]
