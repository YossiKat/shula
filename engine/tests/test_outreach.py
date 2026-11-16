import tools_outreach as o


def _it(name, group="Leads", **cols):
    cv = [{"type": t, "text": v, "column": {"title": t}} for t, v in cols.items()]
    return {"id": "1", "name": name, "group": {"title": group}, "column_values": cv}


def test_neurologist_with_email_is_a_clinic_contact():
    c = o.classify("AnyCan Ai", "Parkinson clinics", _it("Dr. Dana Levi", email="dana@hosp.org", text="נוירולוגית, מרפאת פרקינסון"))
    assert c["seg"] == "clinic" and c["email"] == "dana@hosp.org" and "פרקינסון" in c["why"]


def test_association_is_community_and_plain_task_is_skipped():
    assert o.classify("AnyCan Ai", "Partners", _it("עמותת פרקינסון ישראל", phone="03-1234567"))["seg"] == "community"
    assert o.classify("AnyCan Ai", "ToDo", _it("לקנות חלב")) is None


def test_draft_language_follows_the_name_and_makes_no_medical_claims():
    he = o._draft("clinic", "דנה לוי")
    en = o._draft("community", "Vanessa Schmidt")
    assert he.startswith("שלום דנה") and "aCare Home" in he and "יוסי קט" in he
    assert en.startswith("Hi Vanessa") and "Alpha Omega" in en
    for bad in ("מטפל ב", "משפר", "מרפא", "cure", "treat", "improve"):
        assert bad not in he and bad not in en


def test_work_plan_puts_clinicians_first_ten_per_week():
    f = [{"seg": "partner", "score": 9, "email": "a@x", "phone": "", "name": f"P{i}"} for i in range(5)]
    f += [{"seg": "clinic", "score": 5, "email": "", "phone": "1", "name": f"C{i}"} for i in range(8)]
    plan = o.work_plan(f)
    assert [p["seg"] for p in plan[:8]] == ["clinic"] * 8 and plan[9]["week"] == 1 and plan[10]["week"] == 2


def test_tasks_patients_and_competitors_are_not_contacts():
    for n in ("📊 Dashboard לרופאי הפיילוט", "17 | 🏓 PPP World Championship 2028", "Printing Digital Prescription — A5",
              "Pessina — Patient", "Sunset Party — Official Announcement"):
        assert not o.is_contact(n), n
    for n in ("Tel Aviv Medical Center", "Dr. Gary Sharp — Out-Thinking Parkinson's", "עמותת פרקינסון ישראל"):
        assert o.is_contact(n), n
    assert "competitor" in o.SKIP_BOARDS
