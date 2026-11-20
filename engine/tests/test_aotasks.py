import staff
import tools_aotasks
import tools_hub
import tools_monday

HEAD = ["מזהה", "תאריך", "מקור", "איש קשר", "מחלקה", "גם אצל", "משימה", "הצעד הבא ליוסי", "עד מתי", "דחיפות", "קישור מייל", "סטטוס"]
VISITS = ["AO-1", "13.11.2026", "וואטסאפ", "נטלי לביא", "סוזן", "יונתן", "עוד 5 ביקורים", "לענות לנטלי", "27.11.2026", "דחוף",
          "https://mail.google.com/x", "פתוח"]


def _fake(monkeypatch, rows, existing=None, updates=()):
    existing = existing or {}
    made, posted = [], []
    monkeypatch.setattr(tools_aotasks, "_rows", lambda: [HEAD] + rows)
    monkeypatch.setattr(staff, "_board", lambda: {"id": "7", "groups": []})
    monkeypatch.setattr(staff, "_group_id", lambda b, t: t)
    monkeypatch.setattr(staff, "_cols", lambda b: {"🔥 דחיפות": "u", "📅 תאריך יעד": "d", "🧬 מקור": "s"})

    def create(b, g, n, v, a):
        assert a == "anycan"
        made.append((g, n, v))
        return f"i{len(made)}"
    monkeypatch.setattr(tools_hub, "_create", create)

    def query(gql, variables, account="alphaomega"):
        assert account == "anycan"  # אף פעם לא אלפא אומגה
        if "items_page" in gql:
            g = variables["g"][0]
            return {"boards": [{"groups": [{"items_page": {"items": [{"id": "x" + n, "name": n} for n in existing.get(g, [])]}}]}]}
        if "updates(limit" in gql:
            return {"items": [{"updates": [{"text_body": u} for u in updates]}]}
        posted.append(variables)
        return {"create_update": {"id": "u"}}
    monkeypatch.setattr(tools_monday, "_query", query)
    return made, posted


def test_dept_key_maps_staff_names():
    assert tools_aotasks.dept_key("סוזן") == "admin"
    assert tools_aotasks.dept_key("ג'סיקה") == "cmo"
    assert tools_aotasks.dept_key("יונתן") == "cfo"
    assert tools_aotasks.dept_key("שולה") == "shula"
    assert tools_aotasks.dept_key("מישהו") is None


def test_task_goes_to_owner_and_crosses_to_other_department(monkeypatch):
    made, posted = _fake(monkeypatch, [VISITS])
    out = tools_aotasks.import_ao_tasks()
    owner, other = made
    assert owner[0] == staff.DEPARTMENTS["admin"]["group"]
    assert owner[1] == tools_aotasks.task_name("עוד 5 ביקורים", "נטלי לביא")
    assert owner[2] == {"u": {"label": "🔴 דחוף"}, "s": "וואטסאפ · AO-1 · 13.11.2026", "d": {"date": "2026-11-27"}}
    assert other[0] == staff.DEPARTMENTS["cfo"]["group"] and other[1].startswith("↗️")
    assert "לענות לנטלי" in posted[0]["b"] and "🆔 AO-1" in posted[0]["b"]
    assert "נפתחו ב-monday 1" in out


def test_shula_tasks_get_their_own_group(monkeypatch):
    row = ["AO-2", "20.11.2026", "וואטסאפ", "דנה פרח", "שולה", "", "עניין אייל", "", "", "חשוב", "", "פתוח"]
    made, _ = _fake(monkeypatch, [row])
    tools_aotasks.import_ao_tasks()
    assert made[0][0] == tools_aotasks.SHULA_GROUP and "d" not in made[0][2]


def test_task_already_open_is_not_repeated(monkeypatch):
    group = staff.DEPARTMENTS["admin"]["group"]
    made, posted = _fake(monkeypatch, [VISITS], {group: [tools_aotasks.task_name("עוד 5 ביקורים", "נטלי לביא")]})
    out = tools_aotasks.import_ao_tasks()
    assert not made and not posted and out.startswith("כל המשימות")


def test_done_row_marks_the_item_once(monkeypatch):
    group = staff.DEPARTMENTS["admin"]["group"]
    row = VISITS[:-1] + ["בוצע"]
    made, posted = _fake(monkeypatch, [row], {group: [tools_aotasks.task_name("עוד 5 ביקורים", "נטלי לביא")]})
    tools_aotasks.import_ao_tasks()
    assert not made and "✅ #AO-1" in posted[0]["b"]
    made, posted = _fake(monkeypatch, [row], {group: [tools_aotasks.task_name("עוד 5 ביקורים", "נטלי לביא")]},
                         updates=["✅ בוצע\n✅ #AO-1"])
    tools_aotasks.import_ao_tasks()
    assert not posted


def test_unknown_department_is_reported_not_written(monkeypatch):
    row = ["AO-3", "20.11.2026", "וואטסאפ", "x", "מחלקה מוזרה", "", "משהו", "", "", "", "", "פתוח"]
    made, _ = _fake(monkeypatch, [row])
    out = tools_aotasks.import_ao_tasks()
    assert not made and "לא מוכרת" in out
