import google_auth
import shula_agent
import tools_drive
import tools_gmail


def _connect_both(monkeypatch):
    for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "GOOGLE_REFRESH_TOKEN_ANYCAN"):
        monkeypatch.setenv(k, "x")


class _Mail:
    """ג'ימייל מזויף לחשבון אחד: מייל אחד עם מזהה ידוע."""
    def __init__(self, mid, sent):
        self.mid, self.sent = mid, sent
    def users(self): return self
    def messages(self): return self
    def list(self, **kw):
        self._r = {"messages": [{"id": self.mid}]}
        return self
    def get(self, **kw):
        self._r = {"snippet": "שלום", "threadId": "t", "payload": {"headers": [
            {"name": "From", "value": f"{self.mid} <a@b.c>"}, {"name": "Subject", "value": "נושא"}]}}
        return self
    def send(self, **kw):
        self.sent.append(self.mid)
        self._r = {}
        return self
    def execute(self): return self._r


def test_ids_from_the_second_account_carry_its_name():
    assert google_auth.tag_id("anycan", "abc") == "anycan:abc"
    assert google_auth.tag_id("gmail", "abc") == "abc"
    assert google_auth.split_id("anycan:abc") == ("anycan", "abc")
    assert google_auth.split_id("abc") == ("gmail", "abc")


def test_only_connected_accounts_are_searched(monkeypatch):
    monkeypatch.delenv("GOOGLE_REFRESH_TOKEN_ANYCAN", raising=False)
    for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"):
        monkeypatch.setenv(k, "x")
    assert google_auth.pick("all") == ["gmail"]


def test_email_search_covers_both_accounts(monkeypatch):
    _connect_both(monkeypatch)
    sent = []
    monkeypatch.setattr(tools_gmail, "_gmail", lambda acct="gmail": _Mail("m-" + acct, sent))
    out = tools_gmail.search_emails("is:unread")
    assert "[m-gmail]" in out and "[anycan:m-anycan]" in out and "(AnyCan)" in out


def test_reply_goes_out_from_the_account_it_came_to(monkeypatch):
    _connect_both(monkeypatch)
    sent = []
    monkeypatch.setattr(tools_gmail, "_gmail", lambda acct="gmail": _Mail("m-" + acct, sent))
    shula_agent._turn.message = "כן, שלחי"
    out = tools_gmail.send_email("a@b.c", "Re", "תודה", reply_to_email_id="anycan:m-anycan")
    assert sent == ["m-anycan"] and "Yossi@anycan.ai" in out


def test_drive_file_id_from_anycan_is_read_from_anycan(monkeypatch):
    seen = []

    class _D:
        def files(self): return self
        def get(self, **kw):
            seen.append(kw["fileId"])
            return self
        def execute(self): return {"name": "f", "mimeType": "image/png"}

    monkeypatch.setattr(tools_drive, "_drive", lambda acct="gmail": seen.append(acct) or _D())
    tools_drive.read_drive_file("anycan:F1")
    assert seen == ["anycan", "F1"]
