# ​​🧭 MASTER ROADMAP — assistant-v1

**Guiding Principle:** We build in 7 Phases. Each phase produces a runnable artifact. No feature is started until the previous version is reviewed and stabilized.

**Implementation snapshot (kept in sync with the repo):** Phases 1–5 and **Phase 7** are done (~195 tests, 80% coverage gate on Windows CI). **Phase 6** (minimal Linux adapter + OS auto-detect + Ubuntu CI) is in progress or complete per latest commit.

---

## 🔵 PHASE 1 — Environment & Foundation ✅

-    Create project folder structure.
-    Initialize virtual environment (`venv`).
-    Install dependencies (`psutil`).
-    Generate `requirements.txt`.
-   **Status:** **COMPLETED**

---

## 🔵 PHASE 2 — Minimal Vertical Slice (Core Stability) ✅

*Goal: Validate the architecture with a single end-to-end flow.*

-    **Step 2.1 — Implement Core Execution Flow**
    
    -    `main.py` & `engine.py` (orchestration).
    -    `core/parser.py` (Intent extraction).
    -    `core/intent_engine.py` (Logic routing via `ActionRegistry`).
    -    `core/system_executor.py` (adapter-facing executor).
    -    `adapters/base_adapter.py` (**CRITICAL:** abstract contract for adapters).
    -    `adapters/windows_adapter.py` (Windows implementation).
-    **Step 2.2 — Support Basic Intents**
    
    -    `greet`: "Hello. System operational."
    -    `open_app` / `close_app` (including guarded flows such as File Explorer handling in `core/intent_resolution.py`).
-    **Step 2.3 — Add Resource Monitoring**
    
    -    Measure execution time per intent.
    -    Log CPU usage delta (Before/After action).
    -    Output metrics to `logs/session.log`.

**🎯 Deliverable:** CLI runs, intents execute without crashes, and performance metrics are logged.

-   **Status:** **COMPLETED**

---

## 🔵 PHASE 3 — System Awareness Intents ✅

*Goal: Expand the assistant’s knowledge of the host machine.*

-    **New Intents:** `check_cpu`, `check_memory`, `show_time` (registered alongside `get_cpu_usage`, `get_memory_usage`, `get_time` in `intent_engine.py`).
-    **Update:** `action_registry.py`, `windows_adapter.py`, and parser keyword routing in `core/parser.py`.
-    **Constraint:** Original note was to avoid destabilizing routing; intent detection remains in `CommandParser`, execution in `IntentEngine`.

**🎯 Deliverable:** A functioning system-monitor assistant.

-   **Status:** **COMPLETED**

---

## 🔵 PHASE 4 — Security Layer Activation ✅

*Goal: Protect the host system from malicious or accidental input.*

-    **Step 4.1 — Input Validation:** `core/security` input validation blocks risky patterns (e.g. shell injection) before parsing.
-    **Step 4.2 — Permission System:**
    -    `config/permissions.json` with `core/security/permissions.py` (`PermissionChecker`).
    -    `AssistantEngine.handle` checks permissions after parse and before execution; denied intents return a user-facing message and are logged.

-   **Status:** **COMPLETED**

---

## 🔵 PHASE 5 — Session & Context ✅

*Goal: Add "Memory" to the conversation.*

-    **Session Manager:** `core/session_context.py` (`SessionManager`) stores the last successful intent and last app target after each completed turn.
-    **Contextual Logic:** Rule-based `enrich()` after parse — e.g. bare follow-ups (`also`, `and?`, `what else`) alternate system metrics after CPU/memory/time; pronoun `close it` / `close that` resolves to the last opened app; `launch it again` / `open it again` reopens the last app (including after a close).
-    **Constraint:** Rule-based only; no background threads.

-   **Status:** **COMPLETED** (session is separate from `logs/session.log`, which remains operational logging only.)

---

## 🔵 PHASE 6 — Adapter Expansion (Cross-Platform) ✅ (minimal)

*Goal: Hardware independence.*

-    **Linux Adapter:** `linux_adapter.py` — core intents (greet path via engine, open/close apps, metrics, file-manager process close).
-    **Auto-Detection:** `adapters/factory.py` + `AssistantEngine` load Windows or Linux adapter by `sys.platform`.
-    **CI:** `ubuntu-latest` job alongside Windows (coverage gate on Windows only).

**Linux v1 limits:** No terminal disambiguation, risky-close prompts, or Shell COM window-level Explorer close.

-   **Status:** **COMPLETED (minimal)** — full terminal/session-trust stack remains Windows-only.

---

## 🔵 PHASE 7 — Testing & Stability 🛠️

*Goal: Production-grade reliability.*

-    **Unit Tests:** Parser, intents, validator, permissions, intent resolution, Windows adapter, engine security, session context.
-    **Integration Tests:** Full "User Input -> Action -> Response" flow (`tests/integration/`).
-    **Command:** Run `pytest tests/` locally or in CI. **Coverage:** `pytest tests/ --cov=src --cov-report=term-missing` (see `CONTRIBUTING.md`); target 80%+ with a future `--cov-fail-under` gate.

-   **Status:** **COMPLETED** (195+ tests, `--cov-fail-under=80` on Windows CI, shared fixtures in `tests/conftest.py`.)

---

## 🔥 AFTER v1 IS STABLE

-    **UI:** GUI (Tkinter/PySide) or Voice Layer.
-    **NLP:** Integration of local LLM/Model.
-    **Deployment:** Package into a single `.exe` or binary.

# 🧭 DENIZ v2 ROADMAP

## Mission

Transform Deniz from a command-driven system assistant into a secure, AI-powered desktop operator capable of understanding goals, creating plans, executing tasks, and interacting through voice.

---

# 🔵 PHASE 8 — Execution Hardening

**Goal:** Ensure the existing execution pipeline is production-grade before AI is introduced.

### Current Architecture

```text
User
 ↓
Parser
 ↓
Intent Engine
 ↓
System Executor
 ↓
Adapter
```

## Tasks

### 8.1 Standardized Action Results

All adapter operations return:

```python
@dataclass
class ActionResult:
    success: bool
    message: str
    data: dict | None = None
    recoverable: bool = True
```

No raw exceptions should cross adapter boundaries.

### 8.2 Failure Recovery

Support:

* Partial execution recovery
* Structured error messages
* Retryable failures

### 8.3 Execution Auditing

Log:

* Requested action
* Execution result
* Failure reason
* Recovery status

## 🎯 Deliverable

Reliable execution layer that AI can safely depend on.

---

# 🔵 PHASE 9 — Tool Expansion

**Goal:** Transform Deniz from an app launcher into a computer operator.

## File System Tools

```text
create_folder
delete_folder
rename_folder
move_folder

create_file
delete_file
read_file
write_file
append_file
copy_file
move_file

list_directory
search_files
```

## Process Tools

```text
start_process
stop_process
restart_process
```

## System Tools

```text
check_cpu
check_memory
check_disk
check_battery
```

## Adapter Expansion

### BaseAdapter

Add contracts for:

```python
create_file()
write_file()
read_file()
create_folder()
delete_folder()
```

### WindowsAdapter

Implement all contracts.

### LinuxAdapter

Implement all contracts.

## 🎯 Deliverable

Deniz can manipulate the operating system safely.

---

# 🔵 PHASE 10 — AI Foundation Layer

**Goal:** Introduce LLM support without changing execution logic.

## New Structure

```text
src/
└── ai/
    ├── models/
    ├── providers/
    ├── classifier.py
    ├── schema_validator.py
    └── prompt_builder.py
```

## Provider Layer

Support:

```text
OpenAI
Gemini
Ollama
```

through a common interface.

## Intent Schema

```python
@dataclass
class IntentResult:
    intent: str
    target: str | None
    confidence: float
```

## Example

Input:

```text
please launch my browser
```

Output:

```json
{
  "intent": "open_app",
  "target": "chrome",
  "confidence": 0.95
}
```

## 🎯 Deliverable

AI classification works independently.

No engine integration yet.

---

# 🔵 PHASE 11 — Hybrid Router

**Goal:** Combine deterministic parsing and AI.

## Flow

```text
User
 ↓
Parser
 ↓
Known Intent?
 ↓          ↓
Yes         No
 ↓          ↓
Execute     AI Classifier
```

## New Component

```text
core/
└── hybrid_router.py
```

## Benefits

Fast commands:

```text
open chrome
```

never use AI.

Complex requests:

```text
could you launch my browser
```

use AI.

## 🎯 Deliverable

Deterministic parser with AI fallback.

---

# 🔵 PHASE 12 — Planning Engine

**Goal:** Support goal-based execution.

## Example

User:

```text
Create a Python project
```

Generated Plan:

```json
[
  {"tool":"create_folder"},
  {"tool":"create_file"},
  {"tool":"write_file"}
]
```

## New Components

```text
ai/
├── planner.py
├── plan_models.py
└── plan_executor.py
```

## Plan Validation

Every step passes through:

```text
Security
 ↓
Permissions
 ↓
Executor
```

## 🎯 Deliverable

Multi-step task execution.

---

# 🔵 PHASE 13 — Context & Memory Intelligence

**Goal:** Allow natural follow-up conversations.

## Example

User:

```text
Open Chrome
```

Later:

```text
Close it
```

or

```text
Reopen that
```

## New Components

```text
ai/
├── context_builder.py
└── memory_formatter.py
```

## 🎯 Deliverable

Context-aware interactions.

---

# 🔵 PHASE 14 — Security & Ethical Control Layer

**Goal:** Ensure AI never gains direct system authority.

## Core Principle

```text
AI proposes
Deniz authorizes
```

## Tier 1 — Safe

Examples:

```text
check_cpu
show_time
read_file
```

Execute automatically.

## Tier 2 — Sensitive

Examples:

```text
delete_file
move_file
kill_process
```

Require confirmation.

## Tier 3 — Critical

Examples:

```text
install_software
modify_registry
network_changes
```

Blocked from voice.

Require UI confirmation.

## Audit Logging

Log:

```text
User Request
AI Output
Selected Tool
Approval Status
Execution Result
```

## 🎯 Deliverable

Enterprise-grade safety controls.

---

# 🔵 PHASE 15 — Voice Integration Epoch

**Goal:** Add voice as an input/output interface.

## 15.1 Speech-to-Text

```text
src/voice/
├── microphone.py
└── speech_recognizer.py
```

### Recommended

* Faster-Whisper
* Whisper.cpp

### Flow

```text
Voice
 ↓
Speech-to-Text
 ↓
Hybrid Router
```

---

## 15.2 Text-to-Speech

```text
voice/
├── speaker.py
└── tts_engine.py
```

---

## 15.3 Wake Word Detection

```text
voice/
├── wake_detector.py
└── listener.py
```

Example:

```text
Hey Deniz
```

---

## Voice States

```text
Sleeping
Listening
Thinking
Speaking
```

## 🎯 Deliverable

Fully voice-controlled assistant.

---

# 🔵 PHASE 16 — Desktop Automation Layer

**Goal:** Enable Deniz to operate applications like a human.

## New Components

```text
desktop/
├── mouse_controller.py
├── keyboard_controller.py
├── screen_capture.py
└── ui_automation.py
```

## Capabilities

```text
Click buttons
Type text
Read screen
Scroll
Interact with applications
```

## 🎯 Deliverable

Computer operator functionality.

---

# 🔵 PHASE 17 — Conversational Intelligence

**Goal:** Transform Deniz into a true assistant.

## Example

User:

```text
Why is my CPU usage high?
```

Deniz:

1. Reads system metrics
2. Analyzes processes
3. Explains findings
4. Suggests solutions

## New Components

```text
ai/
├── chat_agent.py
├── knowledge_router.py
└── response_generator.py
```

## 🎯 Deliverable

Reasoning and explanation capabilities.

---

# 🔵 PHASE 18 — Desktop UI

**Goal:** Create the visual interface.

## Structure

```text
ui/
└── desktop/
    ├── main_window.py
    ├── chat_panel.py
    ├── metrics_panel.py
    ├── settings_panel.py
    └── audit_viewer.py
```

## Features

* Chat window
* Voice controls
* Permission prompts
* Execution history
* Settings
* Audit logs

## 🎯 Deliverable

Complete end-user experience.

---

# ✅ Success Criteria for Deniz v2

```text
User
 ↓
Voice / Text / UI
 ↓
AI Understanding
 ↓
Planning
 ↓
Security
 ↓
Tool Execution
 ↓
OS
```

At the end of Phase 18, Deniz should:

* ✅ Understand natural language
* ✅ Create execution plans
* ✅ Manipulate files and applications
* ✅ Operate through voice
* ✅ Enforce security boundaries
* ✅ Maintain context
* ✅ Explain actions
* ✅ Execute desktop workflows safely

### Final Vision

Deniz is not a chatbot.

Deniz is a secure, multi-modal desktop assistant that can understand goals, create plans, execute tasks, and interact naturally while maintaining strict security and ethical controls.

