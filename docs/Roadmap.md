# ​​🧭 MASTER ROADMAP — assistant-v1

**Guiding Principle:** We build in 7 Phases. Each phase produces a runnable artifact. No feature is started until the previous version is reviewed and stabilized.

---

## 🔵 PHASE 1 — Environment & Foundation ✅

-    Create project folder structure.
-    Initialize virtual environment (`venv`).
-    Install dependencies (`psutil`).
-    Generate `requirements.txt`.
-   **Status:** **COMPLETED**

---

## 🔵 PHASE 2 — Minimal Vertical Slice (Core Stability) 🛠️

*Goal: Validate the architecture with a single end-to-end flow.*

-    **Step 2.1 — Implement Core Execution Flow**
    
    -    `main.py` & `engine.py` (The heart).
    -    `core/parser.py` (Intent extraction).
    -    `core/intent_engine.py` (Logic routing).
    -    `adapters/base_adapter.py` (**CRITICAL:** Define abstract methods to prevent `AttributeError`).
    -    `adapters/windows_adapter.py` (Implementation).
-    **Step 2.2 — Support Basic Intents**
    
    -    `greet`: "Hello. System operational."
    -    `open_app`: (Verified with `code` and `cmd`).
-    **Step 2.3 — Add Resource Monitoring (CURRENT FOCUS)**
    
    -    Measure execution time per intent.
    -    Log CPU usage delta (Before/After action).
    -    Output metrics to `logs/session.log`.

**🎯 Deliverable:** CLI runs, intents execute without crashes, and performance metrics are logged.

---

## 🔵 PHASE 3 — System Awareness Intents

*Goal: Expand the assistant’s knowledge of the host machine.*

-    **New Intents:** `check_cpu`, `check_memory`, `show_time`.
-    **Update:** `action_registry.py` and `windows_adapter.py`.
-    **Constraint:** Do NOT modify the core `engine.py` architecture.

**🎯 Deliverable:** A functioning system-monitor assistant.

---

## 🔵 PHASE 4 — Security Layer Activation

*Goal: Protect the host system from malicious or accidental input.*

-    **Step 4.1 — Input Validation:** Sanitize strings; block shell injection attempts (`;`, `&&`, `|`).
-    **Step 4.2 — Permission System:**
    -    Implement `config/permissions.json`.
    -    Check permissions before any adapter call.
    -    Log "Access Denied" for unauthorized attempts.

---

## 🔵 PHASE 5 — Session & Context

*Goal: Add "Memory" to the conversation.*

-    **Session Manager:** Store the last intent/context.
-    **Contextual Logic:** Support follow-up questions (e.g., "Check CPU" -> "And memory?").
-    **Constraint:** Use rule-based logic; no background threads yet.

---

## 🔵 PHASE 6 — Adapter Expansion (Cross-Platform)

*Goal: Hardware independence.*

-    **Linux Adapter:** Implement `linux_adapter.py` following the `BaseAdapter` interface.
-    **Auto-Detection:** Engine detects OS at runtime and loads the correct adapter.

---

## 🔵 PHASE 7 — Testing & Stability

*Goal: Production-grade reliability.*

-    **Unit Tests:** Parser and Intent Detection.
-    **Integration Tests:** Full "User Input -> Action -> Response" flow.
-    **Command:** Run `pytest` and achieve 80%+ coverage.

---

## 🔥 AFTER v1 IS STABLE

-    **UI:** GUI (Tkinter/PySide) or Voice Layer.
-    **NLP:** Integration of local LLM/Model.
-    **Deployment:** Package into a single `.exe` or binary.