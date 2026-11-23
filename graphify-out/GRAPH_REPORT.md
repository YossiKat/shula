# Graph Report - shula  (2026-11-23)

## Corpus Check
- 55 files · ~39,722 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 1 file(s) not represented in the graph (top: (none) 1)

## Summary
- 919 nodes · 1866 edges · 42 communities (35 shown, 7 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 88 edges (avg confidence: 0.85)
- Token cost: 102,233 input · 0 output

## Graph Freshness
- Built from commit: `492d14c0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Python requirements
- tools_mailcols.py
- tools_calendar.py
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
- voice.py
- _query
- claude_brain.py
- re
- FakeCalendar
- _safe_text
- hq.py
- shula_agent.py
- test_voice.py
- _system_prompt
- test_accounts.py
- _start_keep_awake
- whatsapp_webhook
- hq_auth.py
- staff.py
- _push_when_ready
- get
- test_email_gate.py
- os
- BotManager
- _safe
- tools_drive.py

## God Nodes (most connected - your core abstractions)
1. `_query()` - 41 edges
2. `import_facebook_shares()` - 20 edges
3. `_svc()` - 18 edges
4. `_sync()` - 15 edges
5. `whatsapp_webhook()` - 15 edges
6. `apply_mail_changes()` - 14 edges
7. `snapshot()` - 14 edges
8. `auth_action()` - 14 edges
9. `load()` - 14 edges
10. `make_token()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `twilio 9.3.7` --conceptually_related_to--> `whatsapp_webhook()`  [AMBIGUOUS]
  engine/requirements.txt → engine/main.py
- `SUPABASE_KEY` --conceptually_related_to--> `Python requirements`  [AMBIGUOUS]
  README.md → engine/requirements.txt
- `/bots folder` --conceptually_related_to--> `Core Shula system prompt`  [INFERRED]
  README.md → engine/bots/core_shula.txt
- `GEMINI_API_KEY` --conceptually_related_to--> `google-generativeai 0.8.3`  [INFERRED]
  README.md → engine/requirements.txt
- `test_tool_schema_reads_signature_and_docstring()` --indirect_call--> `create_calendar_event()`  [INFERRED]
  engine/tests/test_claude_brain.py → engine/tools_calendar.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Parcel status lookup flow** — engine_bots_core_shula_parcel_rules, engine_bots_core_shula_search_emails, engine_bots_core_shula_read_email, engine_bots_core_shula_parcel_update_email, engine_bots_core_shula_my_parcels_page [EXTRACTED 1.00]
- **Prompt-file bot plugin mechanism** — readme_add_new_bot, readme_bots_folder, readme_github, readme_dashboard, engine_bots_core_shula_core_prompt [INFERRED 0.75]
- **Google Workspace integration stack** — engine_bots_core_shula_calendar, engine_bots_core_shula_gmail, engine_bots_core_shula_drive, engine_requirements_google_api_python_client, engine_requirements_google_auth, engine_requirements_google_auth_oauthlib [INFERRED 0.85]

## Communities (42 total, 7 thin omitted)

### Community 0 - "Python requirements"
Cohesion: 0.07
Nodes (34): AGENTS.md Agent Guidelines, Calendar capability, Calendar color codes, Capabilities list, Conversation memory, Core Shula system prompt, Drive capability, Gmail capability (+26 more)

### Community 1 - "tools_mailcols.py"
Cohesion: 0.13
Nodes (18): _fake(), _item(), test_change_already_in_the_item_is_not_repeated(), test_change_is_applied_and_explained(), test_next_step_column_is_created_once(), test_preview_changes_nothing(), test_unknown_columns_and_old_rows_are_ignored(), test_board_summary_counts_groups_new_done_and_next7() (+10 more)

### Community 2 - "tools_calendar.py"
Cohesion: 0.08
Nodes (21): _FakeInsertService, _FakePatchService, _FakeService, _say(), test_events_for_date_asks_for_that_whole_day(), test_events_for_date_empty_day(), test_log_meal_adds_macros_to_title(), test_log_meal_with_receipt_adds_expense() (+13 more)

### Community 3 - "tools_gmail.py"
Cohesion: 0.18
Nodes (10): split_id(), _body_text(), walk(), create_email_draft(), _gmail(), _header(), _make_raw(), read_email() (+2 more)

### Community 4 - "google_auth.py"
Cohesion: 0.19
Nodes (13): _account(), auth_url(), connected_accounts(), credentials(), _flow(), is_connected(), label(), pick() (+5 more)

### Community 5 - "tools_sync.py"
Cohesion: 0.10
Nodes (29): _item(), _own(), _setup(), test_changed_date_done_status_and_removed_date_are_followed(), test_events_created_from_monday_are_not_logged_back(), test_meeting_about_someone_in_monday_is_logged_on_their_item_once(), test_old_unimportant_events_are_cleared_from_the_calendar(), test_only_important_monday_dates_get_their_own_event_the_rest_go_to_one_summary() (+21 more)

### Community 6 - "requests"
Cohesion: 0.08
Nodes (20): download(), prepare(), show_typing(), transcribe(), _twilio_auth(), test_voice_note_is_transcribed(), _Resp, test_days_clamped() (+12 more)

### Community 7 - "test_whatsapp.py"
Cohesion: 0.17
Nodes (11): client(), _send(), test_after_a_restart_the_first_slow_answer_is_not_silent(), test_answer_is_xml_escaped(), test_empty_message_gets_greeting(), test_fast_answer_comes_back_directly(), test_reset_clears_memory(), test_slow_answer_in_async_mode_sends_no_waiting_message() (+3 more)

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
Cohesion: 0.08
Nodes (20): choose_model(), _block(), _Seq, test_anycan_board_is_found_even_when_it_is_past_the_first_100(), test_anycan_monday_uses_its_own_token_and_finds_board_by_name(), post(), test_complex_requests_use_smart_model(), test_long_web_search_continues_after_pause() (+12 more)

### Community 17 - "voice.py"
Cohesion: 0.19
Nodes (8): _answer(), test_clean_for_speech(), clean_for_speech(), enabled(), speak(), _store(), synthesize(), VoiceAnswer

### Community 18 - "_query"
Cohesion: 0.08
Nodes (40): _cv(), _fake(), query(), _hubitem(), _item(), _row(), test_first_sync_yossi_wins_but_never_clears_alpha_omega(), test_hub_import_stops_at_the_limit() (+32 more)

### Community 19 - "claude_brain.py"
Cohesion: 0.11
Nodes (13): build_tools(), client(), run(), _to_messages(), tool_schema(), _user_content(), _block(), _FakeClient (+5 more)

### Community 20 - "re"
Cohesion: 0.10
Nodes (18): check_email(), gate(), _it(), test_association_is_community_and_plain_task_is_skipped(), test_draft_language_follows_the_name_and_makes_no_medical_claims(), test_neurologist_with_email_is_a_clinic_contact(), test_tasks_patients_and_competitors_are_not_contacts(), test_work_plan_puts_clinicians_first_ten_per_week() (+10 more)

### Community 22 - "_safe_text"
Cohesion: 0.20
Nodes (8): _text_of(), _from_gemini_history(), _safe_text(), _NoText, test_calendar_text_is_marked_as_data(), test_safe_text_empty_when_nothing_returned(), test_safe_text_returns_text(), test_safe_text_survives_cut_off_reply()

### Community 23 - "hq.py"
Cohesion: 0.06
Nodes (50): add_expense(), add_task(), _amount(), api_action(), api_money(), api_today(), _authed(), avatars() (+42 more)

### Community 24 - "shula_agent.py"
Cohesion: 0.10
Nodes (18): _agenda(), consume_approval(), _ensure_loaded(), _facts_text(), forget(), _invalidate_agenda(), _learned_rules(), _log_usage() (+10 more)

### Community 25 - "test_voice.py"
Cohesion: 0.19
Nodes (6): client(), test_long_answer_is_not_spoken(), test_voice_failure_still_sends_text(), test_voice_note_gets_text_and_playable_clip(), test_without_key_answer_stays_text_only(), _voice_note()

### Community 26 - "_system_prompt"
Cohesion: 0.25
Nodes (6): forget_fact(), remember_fact(), _system_prompt(), test_self_check_is_in_prompt(), test_email_content_is_marked_as_data(), test_remember_and_forget_facts()

### Community 27 - "test_accounts.py"
Cohesion: 0.21
Nodes (4): _connect_both(), _Mail, test_email_search_covers_both_accounts(), test_reply_goes_out_from_the_account_it_came_to()

### Community 28 - "_start_keep_awake"
Cohesion: 0.25
Nodes (4): _keep_awake_loop(), _start_keep_awake(), test_keep_awake_does_not_start_outside_render(), test_keep_awake_starts_on_render()

### Community 29 - "whatsapp_webhook"
Cohesion: 0.16
Nodes (6): _can_push(), _collect(), _from_twilio(), _silent(), _twiml(), whatsapp_webhook()

### Community 31 - "hq_auth.py"
Cohesion: 0.09
Nodes (29): auth_action(), _b64(), check_backup_code(), _drive(), _find_file(), _hash(), load(), locked() (+21 more)

### Community 36 - "staff.py"
Cohesion: 0.09
Nodes (28): _board(), claude_action_name(), _cols(), dept_of_action(), focus_text(), _group_id(), import_claude_actions(), import_intel_actions() (+20 more)

### Community 37 - "_push_when_ready"
Cohesion: 0.33
Nodes (4): _push_when_ready(), run(), _send_whatsapp(), test_push_blocked_keeps_answer_for_nudge()

### Community 38 - "get"
Cohesion: 0.11
Nodes (12): enabled(), exchange_code(), ask_shula(), google_auth_callback(), google_auth_start(), _key_ok(), _page(), root() (+4 more)

### Community 40 - "test_email_gate.py"
Cohesion: 0.21
Nodes (8): _Gmail, _setup(), test_email_is_not_sent_without_yossis_ok(), test_email_is_sent_after_yossi_says_yes(), test_one_yes_sends_only_one_email(), test_ordinary_words_that_contain_yes_are_not_approval(), test_short_approvals_still_work(), send_email()

### Community 41 - "os"
Cohesion: 0.25
Nodes (3): get_claude_actions(), _rows(), _rows()

### Community 46 - "tools_drive.py"
Cohesion: 0.16
Nodes (6): tag_id(), test_drive_file_id_from_anycan_is_read_from_anycan(), test_ids_from_the_second_account_carry_its_name(), _drive(), read_drive_file(), search_drive()

## Ambiguous Edges - Review These
- `whatsapp_webhook()` → `twilio 9.3.7`  [AMBIGUOUS]
  engine/requirements.txt · relation: conceptually_related_to
- `SUPABASE_KEY` → `Python requirements`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to

## Knowledge Gaps
- **6 isolated node(s):** `Conversation memory`, `Yossi Kat (user)`, `requests 2.32.3`, `Shulamit OS - Strategic Command Center`, `Supported Versions table` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 304 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `whatsapp_webhook()` connect `whatsapp_webhook` to `Python requirements`, `_push_when_ready`, `get`, `requests`, `voice.py`, `shula_agent.py`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **What connects `Conversation memory`, `Yossi Kat (user)`, `requests 2.32.3` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Python requirements` be split into smaller, more focused modules?**
  _Cohesion score 0.07435897435897436 - nodes in this community are weakly interconnected._
- **Why does `twilio 9.3.7` connect `Python requirements` to `whatsapp_webhook`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Should `tools_mailcols.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12873563218390804 - nodes in this community are weakly interconnected._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `whatsapp_webhook()` and `twilio 9.3.7`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `SUPABASE_KEY` and `Python requirements`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._