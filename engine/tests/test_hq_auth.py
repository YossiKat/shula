import json

import pytest
from fastapi.testclient import TestClient

import google_auth
import hq
import hq_auth

H = {"x-hq": "1"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HQ_SECRET", "test-secret")
    monkeypatch.setenv("PUBLIC_URL", "https://shula.example.com")
    monkeypatch.setattr(google_auth, "is_connected", lambda: False)
    monkeypatch.setattr(hq_auth, "_cache", None)
    monkeypatch.setattr(hq, "OPEN_UNTIL", 1)
    hq_auth._fails.clear()
    hq_auth._challenges.clear()
    import main
    return TestClient(main.app, base_url="https://testserver")


def _login(c):
    r = c.get("/hq/login", params={"t": hq.make_token("link", 60)}, follow_redirects=False)
    assert r.status_code == 303


def test_login_page_offers_face_id(client):
    html = client.get("/hq").text
    assert "Face ID" in html and "קוד גיבוי" in html and "כניסה למטה" in html


def test_settings_need_login(client):
    for a in ("status", "register-options", "backup", "remove-passkeys"):
        assert client.post(f"/hq/auth/{a}", headers=H, json={}).status_code == 401


def test_header_required(client):
    assert client.post("/hq/auth/code", json={"code": "1"}).status_code == 403


def test_backup_code_flow(client):
    _login(client)
    code = client.post("/hq/auth/backup", headers=H, json={}).json()["code"]
    assert len(code) == 14 and code.count("-") == 2
    assert "hash" in hq_auth.load()["backup"] and code.replace("-", "") not in json.dumps(hq_auth.load())
    fresh = TestClient(client.app, base_url="https://testserver")
    assert fresh.get("/hq/api/today").status_code == 401
    assert fresh.post("/hq/auth/code", headers=H, json={"code": "000000000000"}).status_code == 401
    r = fresh.post("/hq/auth/code", headers=H, json={"code": code})
    assert r.status_code == 200 and "hq_session" in r.cookies


def test_backup_code_locks_after_five(client):
    _login(client)
    code = client.post("/hq/auth/backup", headers=H, json={}).json()["code"]
    fresh = TestClient(client.app, base_url="https://testserver")
    for _ in range(5):
        fresh.post("/hq/auth/code", headers=H, json={"code": "1111-1111-1111"})
    r = fresh.post("/hq/auth/code", headers=H, json={"code": code})
    assert r.status_code == 401 and "רבע שעה" in r.json()["msg"]


def test_no_code_yet(client):
    r = client.post("/hq/auth/code", headers=H, json={"code": "123"})
    assert r.json()["msg"] == "עוד לא נוצר קוד גיבוי."


def test_face_id_options(client):
    assert client.post("/hq/auth/login-options", headers=H, json={}).json()["ok"] is False
    _login(client)
    o = client.post("/hq/auth/register-options", headers=H, json={}).json()
    assert o["options"]["rp"]["id"] == "shula.example.com"
    assert o["options"]["authenticatorSelection"]["userVerification"] == "required"
    # a challenge works once only
    assert hq_auth._take_challenge(o["cid"], "reg") is not None
    assert hq_auth._take_challenge(o["cid"], "reg") is None


def test_bad_passkey_login_rejected(client):
    hq_auth.load()["passkeys"].append({"id": "AAAA", "pk": "AAAA", "count": 0, "name": "x"})
    o = client.post("/hq/auth/login-options", headers=H, json={}).json()
    assert o["ok"] and o["options"]["allowCredentials"][0]["id"] == "AAAA"
    r = client.post("/hq/auth/login", headers=H, json={"cid": o["cid"], "credential": {"id": "AAAA", "rawId": "AAAA"}})
    assert r.status_code == 401 and "hq_session" not in r.cookies


def test_app_refreshes_on_open(client):
    _login(client)
    html = client.get("/hq").text
    assert "visibilitychange" in html and "עודכן" in html and 'id="sec"' in html


def test_test_mode_opens_but_not_settings(client, monkeypatch):
    monkeypatch.setattr(hq, "OPEN_UNTIL", 4102444800)
    monkeypatch.setattr(hq, "snapshot", lambda: {})
    assert client.get("/hq/api/today").status_code == 200
    assert "מצב בדיקה" in client.get("/hq").text
    assert client.post("/hq/auth/register-options", headers=H, json={}).status_code == 401
    assert client.post("/hq/auth/backup", headers=H, json={}).status_code == 401


def test_test_mode_ends(client, monkeypatch):
    monkeypatch.setattr(hq, "OPEN_UNTIL", 1)
    assert client.get("/hq/api/today").status_code == 401
