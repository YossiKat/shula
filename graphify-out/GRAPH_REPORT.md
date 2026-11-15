# Graph Report - shula  (2026-11-15)

## Corpus Check
- 43 files · ~27,260 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 1 file(s) not represented in the graph (top: (none) 1)

## Summary
- 702 nodes · 1323 edges · 32 communities (25 shown, 7 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 79 edges (avg confidence: 0.85)
- Token cost: 102,233 input · 0 output

## Graph Freshness
- Built from commit: `06b7b4f0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Python requirements
- shula_agent.py
- whatsapp_webhook
- tools_gmail.py
- google_auth.py
- tools_sync.py
- requests
- test_whatsapp.py
- conversation_log.py
- steps
- steps
- keepalive.yml
- services
- Security Policy
- CLAUDE.md
- tools_posts.py
- test_new_skills.py
- media.py
- _query
- test_hub.py
- voice.py
- FakeCalendar
- _safe_text
- main.py
- os
- reply
- _system_prompt
- _system_parts
- _push_when_ready
- voice_clip
- _safe

## God Nodes (most connected - your core abstractions)
1. `_query()` - 34 edges
2. `import_facebook_shares()` - 20 edges
3. `whatsapp_webhook()` - 15 edges
4. `_sync()` - 15 edges
5. `import_claude_actions()` - 11 edges
6. `import_content_hub()` - 11 edges
7. `sync_monday_and_calendar()` - 11 edges
8. `_Mail` - 11 edges
9. `run()` - 11 edges
10. `send_email()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `twilio 9.3.7` --conceptually_related_to--> `whatsapp_webhook()`  [AMBIGUOUS]
  engine/requirements.txt → engine/main.py
- `SUPABASE_KEY` --conceptually_related_to--> `Python requirements`  [AMBIGUOUS]
  README.md → engine/requirements.txt
- `/bots folder` --conceptually_related_to--> `Core Shula system prompt`  [INFERRED]
  README.md → engine/bots/core_shula.txt
- `GEMINI_API_KEY` --conceptually_related_to--> `google-generativeai 0.8.3`  [INFERRED]
  README.md → engine/requirements.txt
- `test_query_refuses_any_mutation_on_alpha_omega()` --calls--> `_query()`  [EXTRACTED]
  engine/tests/test_hub.py → engine/tools_monday.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Parcel status lookup flow** — engine_bots_core_shula_parcel_rules, engine_bots_core_shula_search_emails, engine_bots_core_shula_read_email, engine_bots_core_shula_parcel_update_email, engine_bots_core_shula_my_parcels_page [EXTRACTED 1.00]
- **Prompt-file bot plugin mechanism** — readme_add_new_bot, readme_bots_folder, readme_github, readme_dashboard, engine_bots_core_shula_core_prompt [INFERRED 0.75]
- **Google Workspace integration stack** — engine_bots_core_shula_calendar, engine_bots_core_shula_gmail, engine_bots_core_shula_drive, engine_requirements_google_api_python_client, engine_requirements_google_auth, engine_requirements_google_auth_oauthlib [INFERRED 0.85]

## Communities (32 total, 7 thin omitted)

### Community 0 - "Python requirements"
Cohesion: 0.07
Nodes (34): AGENTS.md Agent Guidelines, Calendar capability, Calendar color codes, Capabilities list, Conversation memory, Core Shula system prompt, Drive capability, Gmail capability (+26 more)

### Community 1 - "shula_agent.py"
Cohesion: 0.17
Nodes (8): consume_approval(), _log_usage(), _record_usage(), _reply_claude(), _reply_gemini(), _to_gemini_history(), _tools_in_turn(), user_approved()

### Community 2 - "whatsapp_webhook"
Cohesion: 0.16
Nodes (6): _can_push(), _collect(), _from_twilio(), _silent(), _twiml(), whatsapp_webhook()

### Community 3 - "tools_gmail.py"
Cohesion: 0.10
Nodes (16): _Gmail, _setup(), test_email_is_not_sent_without_yossis_ok(), test_email_is_sent_after_yossi_says_yes(), test_one_yes_sends_only_one_email(), test_ordinary_words_that_contain_yes_are_not_approval(), test_short_approvals_still_work(), _body_text() (+8 more)

### Community 4 - "google_auth.py"
Cohesion: 0.05
Nodes (34): _account(), auth_url(), connected_accounts(), credentials(), exchange_code(), _flow(), is_connected(), label() (+26 more)

### Community 5 - "tools_sync.py"
Cohesion: 0.07
Nodes (31): _FakeService, test_events_for_date_asks_for_that_whole_day(), test_events_for_date_empty_day(), _item(), _setup(), test_changed_date_done_status_and_removed_date_are_followed(), test_events_created_from_monday_are_not_logged_back(), test_meeting_about_someone_in_monday_is_logged_on_their_item_once() (+23 more)

### Community 6 - "requests"
Cohesion: 0.13
Nodes (14): _Resp, test_days_clamped(), fake_get(), test_forecast_home_7_days(), fake_get(), test_forecast_other_city_uses_geocoding(), fake_get(), _headers() (+6 more)

### Community 7 - "test_whatsapp.py"
Cohesion: 0.07
Nodes (21): _keep_awake_loop(), _start_keep_awake(), client(), test_long_answer_is_not_spoken(), test_voice_failure_still_sends_text(), test_voice_note_gets_text_and_playable_clip(), test_without_key_answer_stays_text_only(), _voice_note() (+13 more)

### Community 8 - "conversation_log.py"
Cohesion: 0.13
Nodes (12): format_entry(), _get_label_id(), _gmail(), _insert(), is_correction(), log_exchange(), run(), test_correction_is_flagged_with_previous_answer() (+4 more)

### Community 9 - "steps"
Cohesion: 0.13
Nodes (14): jobs, pytest, name, branches, runs-on, steps, run, uses (+6 more)

### Community 10 - "steps"
Cohesion: 0.17
Nodes (11): runs-on, steps, jobs, build-and-deploy, name, branches, name, run (+3 more)

### Community 11 - "keepalive.yml"
Cohesion: 0.17
Nodes (11): jobs, ping, name, runs-on, steps, cron, name, run (+3 more)

### Community 12 - "services"
Cohesion: 0.18
Nodes (10): key, sync, services, buildCommand, envVars, name, rootDir, runtime (+2 more)

### Community 13 - "Security Policy"
Cohesion: 0.67
Nodes (3): Security Policy, Supported Versions table, Reporting a Vulnerability

### Community 15 - "tools_posts.py"
Cohesion: 0.06
Nodes (35): _Cal, go(), _fake(), query(), test_each_share_round_is_one_light_green_event_at_the_share_time(), test_facebook_shares_are_grouped_under_their_post_and_never_twice(), test_first_measurement_and_posts_without_view_counts(), test_import_prepares_missing_columns_first() (+27 more)

### Community 16 - "test_new_skills.py"
Cohesion: 0.06
Nodes (30): build_tools(), choose_model(), client(), run(), _text_of(), _to_messages(), tool_schema(), _user_content() (+22 more)

### Community 17 - "media.py"
Cohesion: 0.21
Nodes (6): download(), prepare(), show_typing(), transcribe(), _twilio_auth(), test_voice_note_is_transcribed()

### Community 18 - "_query"
Cohesion: 0.05
Nodes (52): _board(), claude_action_name(), _cols(), dept_of_action(), focus_text(), _group_id(), import_claude_actions(), import_intel_actions() (+44 more)

### Community 19 - "test_hub.py"
Cohesion: 0.17
Nodes (19): _cv(), _fake(), query(), _hubitem(), _item(), _row(), test_first_sync_yossi_wins_but_never_clears_alpha_omega(), test_hub_import_stops_at_the_limit() (+11 more)

### Community 20 - "voice.py"
Cohesion: 0.18
Nodes (8): _answer(), test_clean_for_speech(), clean_for_speech(), enabled(), speak(), _store(), synthesize(), VoiceAnswer

### Community 22 - "_safe_text"
Cohesion: 0.24
Nodes (6): _from_gemini_history(), _safe_text(), _NoText, test_safe_text_empty_when_nothing_returned(), test_safe_text_returns_text(), test_safe_text_survives_cut_off_reply()

### Community 25 - "reply"
Cohesion: 0.20
Nodes (8): enabled(), _ensure_loaded(), forget(), _invalidate_agenda(), model_name(), reply(), usage_report(), test_falls_back_to_gemini_when_claude_fails()

### Community 26 - "_system_prompt"
Cohesion: 0.22
Nodes (7): forget_fact(), remember_fact(), _system_prompt(), test_calendar_text_is_marked_as_data(), test_self_check_is_in_prompt(), test_email_content_is_marked_as_data(), test_remember_and_forget_facts()

### Community 27 - "_system_parts"
Cohesion: 0.29
Nodes (4): _agenda(), _facts_text(), _learned_rules(), _system_parts()

### Community 28 - "_push_when_ready"
Cohesion: 0.33
Nodes (4): _push_when_ready(), run(), _send_whatsapp(), test_push_blocked_keeps_answer_for_nudge()

## Ambiguous Edges - Review These
- `whatsapp_webhook()` → `twilio 9.3.7`  [AMBIGUOUS]
  engine/requirements.txt · relation: conceptually_related_to
- `SUPABASE_KEY` → `Python requirements`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to

## Knowledge Gaps
- **6 isolated node(s):** `Conversation memory`, `Yossi Kat (user)`, `requests 2.32.3`, `Shulamit OS - Strategic Command Center`, `Supported Versions table` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 246 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `whatsapp_webhook()` connect `whatsapp_webhook` to `Python requirements`, `media.py`, `voice.py`, `main.py`, `reply`, `_push_when_ready`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **What connects `Conversation memory`, `Yossi Kat (user)`, `requests 2.32.3` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Python requirements` be split into smaller, more focused modules?**
  _Cohesion score 0.07435897435897436 - nodes in this community are weakly interconnected._
- **Why does `twilio 9.3.7` connect `Python requirements` to `whatsapp_webhook`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Should `tools_gmail.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10227272727272728 - nodes in this community are weakly interconnected._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `whatsapp_webhook()` and `twilio 9.3.7`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `SUPABASE_KEY` and `Python requirements`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._