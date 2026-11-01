import tools_weather


class _Resp:
    def __init__(self, data):
        self._d = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._d


def test_forecast_home_7_days(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((url, params))
        return _Resp({"daily": {
            "time": ["2026-11-01", "2026-11-02"],
            "weather_code": [0, 63],
            "temperature_2m_max": [25.4, 21.0], "temperature_2m_min": [17.2, 15.6],
            "precipitation_probability_max": [0, 80], "precipitation_sum": [0, 6.2],
            "wind_speed_10m_max": [14, 30], "wind_gusts_10m_max": [25, 55]}})
    monkeypatch.setattr(tools_weather.requests, "get", fake_get)
    out = tools_weather.get_weather_forecast()
    assert calls[0][1]["forecast_days"] == 7
    assert abs(calls[0][1]["latitude"] - 32.1461) < 0.01
    assert "רמת השרון" in out and "ראשון 1.11" in out and "שני 2.11" in out
    assert "גשם 80%" in out and "6 מ\"מ" in out


def test_forecast_other_city_uses_geocoding(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        if "geocoding" in url:
            return _Resp({"results": [{"name": "אמסטרדם", "country": "הולנד", "latitude": 52.37, "longitude": 4.89}]})
        return _Resp({"daily": {"time": ["2026-11-01"], "weather_code": [3], "temperature_2m_max": [11],
                                "temperature_2m_min": [6], "precipitation_probability_max": [40],
                                "precipitation_sum": [1], "wind_speed_10m_max": [20], "wind_gusts_10m_max": [35]}})
    monkeypatch.setattr(tools_weather.requests, "get", fake_get)
    out = tools_weather.get_weather_forecast(days=1, city="אמסטרדם")
    assert "אמסטרדם, הולנד" in out and "מעונן" in out


def test_days_clamped(monkeypatch):
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen.update(params)
        return _Resp({"daily": {"time": []}})
    monkeypatch.setattr(tools_weather.requests, "get", fake_get)
    tools_weather.get_weather_forecast(days=30)
    assert seen["forecast_days"] == 14
