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
