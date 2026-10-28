# Graph Report - shula  (2026-10-28)

## Corpus Check
- 24 files · ~6,594 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 1 file(s) not represented in the graph (top: (none) 1)

## Summary
- 304 nodes · 468 edges · 15 communities (14 shown, 1 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 36 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `494ca395`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Shula Persona & Rules
- Agent Brain & Memory
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

## God Nodes (most connected - your core abstractions)
1. `whatsapp_webhook()` - 11 edges
2. `reply()` - 11 edges
3. `Python requirements` - 10 edges
4. `format_entry()` - 8 edges
5. `service()` - 8 edges
6. `get_events_for_date()` - 8 edges
7. `services` - 8 edges
8. `Core Shula system prompt` - 8 edges
9. `log_exchange()` - 7 edges
10. `is_connected()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `twilio 9.3.7` --conceptually_related_to--> `whatsapp_webhook()`  [AMBIGUOUS]
  engine/requirements.txt → engine/main.py
- `SUPABASE_KEY` --conceptually_related_to--> `Python requirements`  [AMBIGUOUS]
  README.md → engine/requirements.txt
- `/bots folder` --conceptually_related_to--> `Core Shula system prompt`  [INFERRED]
  README.md → engine/bots/core_shula.txt
- `GEMINI_API_KEY` --conceptually_related_to--> `google-generativeai 0.8.3`  [INFERRED]
  README.md → engine/requirements.txt
- `Drive capability` --conceptually_related_to--> `google-api-python-client 2.149.0`  [INFERRED]
  engine/bots/core_shula.txt → engine/requirements.txt

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Parcel status lookup flow** — engine_bots_core_shula_parcel_rules, engine_bots_core_shula_search_emails, engine_bots_core_shula_read_email, engine_bots_core_shula_parcel_update_email, engine_bots_core_shula_my_parcels_page [EXTRACTED 1.00]
- **Prompt-file bot plugin mechanism** — readme_add_new_bot, readme_bots_folder, readme_github, readme_dashboard, engine_bots_core_shula_core_prompt [INFERRED 0.75]
- **Google Workspace integration stack** — engine_bots_core_shula_calendar, engine_bots_core_shula_gmail, engine_bots_core_shula_drive, engine_requirements_google_api_python_client, engine_requirements_google_auth, engine_requirements_google_auth_oauthlib [INFERRED 0.85]

## Communities (15 total, 1 thin omitted)

### Community 0 - "Shula Persona & Rules"
Cohesion: 0.07
Nodes (34): AGENTS.md Agent Guidelines, Calendar capability, Calendar color codes, Capabilities list, Conversation memory, Core Shula system prompt, Drive capability, Gmail capability (+26 more)

### Community 1 - "Agent Brain & Memory"
Cohesion: 0.06
Nodes (22): BotManager, _agenda(), _ensure_loaded(), forget(), _from_gemini_history(), _invalidate_agenda(), _learned_rules(), _log_usage() (+14 more)

### Community 2 - "WhatsApp Webhook Server"
Cohesion: 0.10
Nodes (13): ask_shula(), _collect(), _from_twilio(), google_auth_callback(), google_auth_start(), _page(), _push_when_ready(), run() (+5 more)

### Community 3 - "Gmail Tools & Email Gate"
Cohesion: 0.11
Nodes (13): _Gmail, _setup(), test_email_is_not_sent_without_yossis_ok(), test_email_is_sent_after_yossi_says_yes(), _body_text(), walk(), create_email_draft(), _gmail() (+5 more)

### Community 4 - "Google OAuth Connection"
Cohesion: 0.15
Nodes (12): auth_url(), credentials(), exchange_code(), _flow(), is_connected(), service(), _find_file(), load() (+4 more)

### Community 5 - "Calendar Tools & Tests"
Cohesion: 0.13
Nodes (10): _FakeService, test_events_for_date_asks_for_that_whole_day(), test_events_for_date_empty_day(), create_calendar_event(), delete_calendar_event(), _fmt(), get_calendar_events(), get_events_for_date() (+2 more)

### Community 6 - "tools_social.py"
Cohesion: 0.36
Nodes (5): _headers(), list_scheduled_posts(), _norm_networks(), _params(), schedule_social_post()

### Community 7 - "WhatsApp Tests"
Cohesion: 0.14
Nodes (9): client(), _send(), test_answer_is_xml_escaped(), test_empty_message_gets_greeting(), test_fast_answer_comes_back_directly(), test_push_blocked_keeps_answer_for_nudge(), test_reset_clears_memory(), test_slow_answer_is_delivered_on_nudge() (+1 more)

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

## Ambiguous Edges - Review These
- `whatsapp_webhook()` → `twilio 9.3.7`  [AMBIGUOUS]
  engine/requirements.txt · relation: conceptually_related_to
- `SUPABASE_KEY` → `Python requirements`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to

## Knowledge Gaps
- **6 isolated node(s):** `Conversation memory`, `Yossi Kat (user)`, `requests 2.32.3`, `Shulamit OS - Strategic Command Center`, `Supported Versions table` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 115 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `whatsapp_webhook()` connect `WhatsApp Webhook Server` to `Shula Persona & Rules`, `Agent Brain & Memory`?**
  _High betweenness centrality (0.198) - this node is a cross-community bridge._
- **What connects `Conversation memory`, `Yossi Kat (user)`, `requests 2.32.3` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Shula Persona & Rules` be split into smaller, more focused modules?**
  _Cohesion score 0.07435897435897436 - nodes in this community are weakly interconnected._
- **Why does `twilio 9.3.7` connect `Shula Persona & Rules` to `WhatsApp Webhook Server`?**
  _High betweenness centrality (0.178) - this node is a cross-community bridge._
- **Should `Agent Brain & Memory` be split into smaller, more focused modules?**
  _Cohesion score 0.05795918367346939 - nodes in this community are weakly interconnected._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `whatsapp_webhook()` and `twilio 9.3.7`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `SUPABASE_KEY` and `Python requirements`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._