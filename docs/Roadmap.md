🧭 MASTER ROADMAP — assistant-v1

We build in 7 Phases.

Each phase produces something runnable.

No theoretical fluff.

🔵 PHASE 1 — Environment & Foundation ✅ (DONE)

You already completed:

Folder structure

venv

psutil install

requirements.txt

Status: ✔ Completed

🔵 PHASE 2 — Minimal Vertical Slice (Make It Alive)

Goal:

One full working intent through entire architecture.

Step 2.1 — Implement Core Execution Flow

Implement only:

main.py

engine.py

core/parser.py

core/intent_engine.py

core/action_registry.py

adapters/base_adapter.py

adapters/windows_adapter.py

core/monitoring/resource_monitor.py

utils/logger.py

Ignore everything else for now.

Step 2.2 — Support ONE Intent Only

Choose:

greet ← safest first

Test flow:

User: hello
Assistant: Hello. System operational.

If this works, architecture is validated.

Step 2.3 — Add Resource Monitoring

After action executes:

Measure execution time

Measure CPU before/after

Log to logs/session.log

Now your assistant becomes ethically transparent.

🎯 Deliverable of Phase 2:

CLI runs

One intent works

Logging works

Resource monitoring works

🔵 PHASE 3 — System Awareness Intents

Now expand capabilities.

Add:

check_cpu

check_memory

show_time

Update:

intent_engine.py

action_registry.py

windows_adapter.py

Do NOT change engine architecture.

🎯 Deliverable:

You now have a functioning system-monitor assistant.

🔵 PHASE 4 — Security Layer Activation

Now activate:

core/security/
    permissions.py
    validator.py
Step 4.1 — Input Validation

Sanitize:

Remove dangerous patterns

Strip shell injection attempts

Step 4.2 — Permission System

Use:

config/permissions.json

Example:

{
  "check_cpu": true,
  "check_memory": true,
  "open_browser": false
}

Before executing any action:

Check permission

Deny if disabled

🎯 Deliverable:

Assistant respects user-controlled permission policy.

🔵 PHASE 5 — Session & Context

Now activate:

core/session/session_manager.py

Goal:

Store last intent

Store conversation memory

No background threads

Example:

User: check cpu
User: and memory?

Assistant understands context.

🎯 Deliverable:

Context-aware rule-based assistant.

🔵 PHASE 6 — Adapter Expansion

Currently you have:

windows_adapter.py

Now implement:

linux_adapter.py

And auto-detect OS inside engine.

This makes assistant platform-independent.

🎯 Deliverable:

Cross-platform offline assistant.

🔵 PHASE 7 — Testing & Stability

Activate:

tests/

Write:

Unit tests for parser

Unit tests for intent detection

Unit tests for permission checks

Integration test for full flow

Run:

pytest

Now your assistant becomes production-quality.

🔥 AFTER v1 IS STABLE

Only then consider:

Voice layer

GUI (Tkinter or PySide)

Local NLP model

Plugin architecture

Packaging into executable