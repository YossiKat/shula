from datetime import datetime, timedelta

import tools_calendar
import tools_snapshot


def test_board_summary_counts_groups_new_done_and_next7():
    now = datetime(2026, 11, 15, 6, 5, tzinfo=tools_calendar.TZ)
    recent = (now - timedelta(days=2)).isoformat()
    old = (now - timedelta(days=30)).isoformat()
    items = [
        {"name": "פוסט 1", "created_at": recent, "updated_at": recent, "group": {"title": "פוסטים"},
         "column_values": [{"type": "status", "text": "Published"}, {"type": "date", "text": "2026-11-17"}]},
        {"name": "פוסט 2", "created_at": old, "updated_at": old, "group": {"title": "פוסטים"},
         "column_values": [{"type": "status", "text": "Draft"}, {"type": "date", "text": "2026-12-30"}]},
        {"name": "ליד", "created_at": old, "updated_at": recent, "group": {"title": "לידים"}, "column_values": []},
    ]
    s = tools_snapshot.board_summary("Social media schedule", items, now)
    assert (s["n"], s["new7"], s["upd7"], s["done"]) == (3, 1, 2, 1)
    assert s["groups"]["פוסטים"]["n"] == 2
    assert s["next7"] == [{"d": "2026-11-17", "t": "פוסט 1", "g": "פוסטים"}]
