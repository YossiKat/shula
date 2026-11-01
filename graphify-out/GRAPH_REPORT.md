# Graph Report - shula  (2026-11-01)

## Corpus Check
- 32 files · ~11,957 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 1 file(s) not represented in the graph (top: (none) 1)

## Summary
- 454 nodes · 762 edges · 19 communities (18 shown, 1 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 51 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d6b2b352`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Shula Persona & Rules
- shula_agent.py
- WhatsApp Webhook Server
- Gmail Tools & Email Gate
- Google OAuth Connection
- Calendar Tools & Tests
- tools_social.py
- WhatsApp Tests
- Weekly Conversation Log
- CI Test Workflow
- Deploy Workflow
- Keepalive Ping
- Render Deployment Config
- Security Policy Template
- CLAUDE.md
- test_accounts.py
- claude_brain.py
- media.py
- test_new_skills.py

## God Nodes (most connected - your core abstractions)
1. `whatsapp_webhook()` - 14 edges
2. `run()` - 11 edges
3. `_Mail` - 11 edges
4. `send_email()` - 11 edges
5. `reply()` - 10 edges
6. `Python requirements` - 10 edges
7. `is_connected()` - 9 edges
8. `service()` - 9 edges
9. `_send()` - 9 edges
10. `format_entry()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `twilio 9.3.7` --conceptually_related_to--> `whatsapp_webhook()`  [AMBIGUOUS]
  engine/requirements.txt → engine/main.py
- `SUPABASE_KEY` --conceptually_related_to--> `Python requirements`  [AMBIGUOUS]
  README.md → engine/requirements.txt
- `/bots folder` --conceptually_related_to--> `Core Shula system prompt`  [INFERRED]
  README.md → engine/bots/core_shula.txt
- `GEMINI_API_KEY` --conceptually_related_to--> `google-generativeai 0.8.3`  [INFERRED]
  README.md → engine/requirements.txt
- `test_falls_back_to_gemini_when_claude_fails()` --calls--> `reply()`  [EXTRACTED]
  engine/tests/test_claude_brain.py → engine/shula_agent.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Parcel status lookup flow** — engine_bots_core_shula_parcel_rules, engine_bots_core_shula_search_emails, engine_bots_core_shula_read_email, engine_bots_core_shula_parcel_update_email, engine_bots_core_shula_my_parcels_page [EXTRACTED 1.00]
- **Prompt-file bot plugin mechanism** — readme_add_new_bot, readme_bots_folder, readme_github, readme_dashboard, engine_bots_core_shula_core_prompt [INFERRED 0.75]
- **Google Workspace integration stack** — engine_bots_core_shula_calendar, engine_bots_core_shula_gmail, engine_bots_core_shula_drive, engine_requirements_google_api_python_client, engine_requirements_google_auth, engine_requirements_google_auth_oauthlib [INFERRED 0.85]

## Communities (19 total, 1 thin omitted)

### Community 0 - "Shula Persona & Rules"
Cohesion: 0.07
Nodes (34): AGENTS.md Agent Guidelines, Calendar capability, Calendar color codes, Capabilities list, Conversation memory, Core Shula system prompt, Drive capability, Gmail capability (+26 more)

### Community 1 - "shula_agent.py"
Cohesion: 0.07
Nodes (28): enabled(), _agenda(), consume_approval(), _ensure_loaded(), _facts_text(), forget(), forget_fact(), _from_gemini_history() (+20 more)

### Community 2 - "WhatsApp Webhook Server"
Cohesion: 0.07
Nodes (18): _answer(), ask_shula(), _collect(), _from_twilio(), google_auth_callback(), google_auth_start(), _key_ok(), _page() (+10 more)

### Community 3 - "Gmail Tools & Email Gate"
Cohesion: 0.10
Nodes (17): _Gmail, _setup(), test_email_is_not_sent_without_yossis_ok(), test_email_is_sent_after_yossi_says_yes(), test_one_yes_sends_only_one_email(), test_ordinary_words_that_contain_yes_are_not_approval(), test_short_approvals_still_work(), _body_text() (+9 more)

### Community 4 - "Google OAuth Connection"
Cohesion: 0.10
Nodes (21): _account(), auth_url(), connected_accounts(), credentials(), exchange_code(), _flow(), is_connected(), label() (+13 more)

### Community 5 - "Calendar Tools & Tests"
Cohesion: 0.13
Nodes (12): _FakeService, test_events_for_date_asks_for_that_whole_day(), test_events_for_date_empty_day(), create_calendar_event(), delete_calendar_event(), _extra_calendars(), _fmt(), get_calendar_events() (+4 more)

### Community 6 - "tools_social.py"
Cohesion: 0.13
Nodes (14): _Resp, test_days_clamped(), fake_get(), test_forecast_home_7_days(), fake_get(), test_forecast_other_city_uses_geocoding(), fake_get(), _headers() (+6 more)

### Community 7 - "WhatsApp Tests"
Cohesion: 0.10
Nodes (14): _keep_awake_loop(), _start_keep_awake(), client(), _send(), test_answer_is_xml_escaped(), test_empty_message_gets_greeting(), test_fast_answer_comes_back_directly(), test_keep_awake_does_not_start_outside_render() (+6 more)

### Community 8 - "Weekly Conversation Log"
Cohesion: 0.13
Nodes (12): format_entry(), _get_label_id(), _gmail(), _insert(), is_correction(), log_exchange(), run(), test_correction_is_flagged_with_previous_answer() (+4 more)

### Community 9 - "CI Test Workflow"
Cohesion: 0.13
Nodes (14): jobs, pytest, name, branches, runs-on, steps, run, uses (+6 more)

### Community 10 - "Deploy Workflow"
Cohesion: 0.17
Nodes (11): runs-on, steps, jobs, build-and-deploy, name, branches, name, run (+3 more)

### Community 11 - "Keepalive Ping"
Cohesion: 0.17
Nodes (11): jobs, ping, name, runs-on, steps, cron, name, run (+3 more)

### Community 12 - "Render Deployment Config"
Cohesion: 0.18
Nodes (10): key, sync, services, buildCommand, envVars, name, rootDir, runtime (+2 more)

### Community 13 - "Security Policy Template"
Cohesion: 0.67
Nodes (3): Security Policy, Supported Versions table, Reporting a Vulnerability

### Community 15 - "test_accounts.py"
Cohesion: 0.21
Nodes (4): _connect_both(), _Mail, test_email_search_covers_both_accounts(), test_reply_goes_out_from_the_account_it_came_to()

### Community 16 - "claude_brain.py"
Cohesion: 0.08
Nodes (20): build_tools(), client(), run(), _text_of(), _to_messages(), tool_schema(), _user_content(), _safe_text() (+12 more)

### Community 17 - "media.py"
Cohesion: 0.11
Nodes (7): BotManager, download(), prepare(), show_typing(), transcribe(), _twilio_auth(), test_voice_note_is_transcribed()

### Community 18 - "test_new_skills.py"
Cohesion: 0.13
Nodes (12): choose_model(), _block(), _Seq, test_complex_requests_use_smart_model(), test_long_web_search_continues_after_pause(), test_monday_items_are_read_and_filtered(), test_simple_question_uses_cheap_model(), test_web_search_turns_itself_off_if_account_does_not_allow() (+4 more)

## Ambiguous Edges - Review These
- `whatsapp_webhook()` → `twilio 9.3.7`  [AMBIGUOUS]
  engine/requirements.txt · relation: conceptually_related_to
- `SUPABASE_KEY` → `Python requirements`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to

## Knowledge Gaps
- **6 isolated node(s):** `Conversation memory`, `Yossi Kat (user)`, `requests 2.32.3`, `Shulamit OS - Strategic Command Center`, `Supported Versions table` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 171 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `whatsapp_webhook()` connect `WhatsApp Webhook Server` to `Shula Persona & Rules`, `media.py`, `shula_agent.py`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **What connects `Conversation memory`, `Yossi Kat (user)`, `requests 2.32.3` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Shula Persona & Rules` be split into smaller, more focused modules?**
  _Cohesion score 0.07435897435897436 - nodes in this community are weakly interconnected._
- **Why does `twilio 9.3.7` connect `Shula Persona & Rules` to `WhatsApp Webhook Server`?**
  _High betweenness centrality (0.137) - this node is a cross-community bridge._
- **Should `shula_agent.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06565656565656566 - nodes in this community are weakly interconnected._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `whatsapp_webhook()` and `twilio 9.3.7`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `SUPABASE_KEY` and `Python requirements`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._