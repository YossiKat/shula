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
