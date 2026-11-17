import quality


def test_clean_email_passes():
    assert quality.check_email("פגישה ביום שני", "שלום דנה,\nנשמח להיפגש ביום שני ב-10:00.\nתודה,\nיוסי") == []


def test_leftovers_and_ai_signs_are_caught():
    p = quality.check_email("", "הנה טיוטה: **שלום** [שם], נדבר — TODO את את זה")
    text = " ".join(p)
    for bit in ("אין נושא", "[שם", "todo", "הנה טיוטה", "**", "קו ארוך", "מילה כפולה"):
        assert bit in text


def test_draft_is_blocked_before_gmail(monkeypatch):
    import tools_gmail
    monkeypatch.setattr(tools_gmail, "_gmail", lambda *a: (_ for _ in ()).throw(AssertionError("should not reach gmail")))
    out = tools_gmail.create_email_draft("a@b.com", "נושא", "שלום [לבדוק: תאריך]")
    assert "קלייר" in out
