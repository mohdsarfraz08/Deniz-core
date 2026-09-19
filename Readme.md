# Deniz (Assistant v2)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-589%20passed-success.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](pyproject.toml)
[![Platform](https://img.shields.io/badge/platform-Windows%20(Full)%20%7C%20Linux%20(Core)-informational.svg)](src/adapters/)
[![AI Triage](https://img.shields.io/badge/AI%20Triage-Nebius%20%C3%97%20NVIDIA%20Nemotron%20%7C%20Ollama-purple.svg)](docs/AI_LAYER.md)
<!-- [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) -->

> **Deniz** is a hybrid, secure AI desktop operating engine and autonomous assistant. It bridges deterministic, zero-latency system operations with a multi-tier AI triage architecture—pairing local on-device LLMs (Ollama) for air-gapped sensitive actions with high-reasoning cloud models (Nebius Token Factory with NVIDIA Nemotron) for complex tasks.

---

## 📑 Table of Contents

- [Vision & Architecture](#-vision--architecture)
  - [The 3-Tier AI Triage Model](#the-3-tier-ai-triage-model)
  - [End-to-End Execution Flow](#end-to-end-execution-flow)
- [Key Features](#-key-features)
- [Platform Support Matrix](#-platform-support-matrix)
- [Repository Structure](#-repository-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration & Environment Variables](#configuration--environment-variables)
- [Usage & Examples](#-usage--examples)
  - [Interactive Assistant CLI](#1-interactive-assistant-cli)
  - [AI Layer Diagnostic Tool](#2-ai-layer-diagnostic-tool)
- [Security, AI Ethics & Governance](#-security-ai-ethics--governance)
  - [PathGuard 3-Layer Sandbox](#pathguard-3-layer-sandbox)
  - [Terminal Session Trust & Safe Process Termination](#terminal-session-trust--safe-process-termination)
  - [Dynamic Permission Firewall](#dynamic-permission-firewall)
  - [Fail-Closed Guarantee](#fail-closed-guarantee)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Master Roadmap Status](#-master-roadmap-status)
- [Contributing](#-contributing)

---

## 🏛 Vision & Architecture

Traditional AI assistants either send all raw user input to the cloud (creating critical data privacy risks) or rely entirely on rigid rule-matching (lacking natural language understanding). 

**Deniz resolves this dichotomy with a hybrid 3-tier architecture:**

```text
                  User Input
                      │
                      ▼
        ┌───────────────────────────┐
        │ Tier 0 — Deterministic    │  ← Zero latency. No model.
        │ (CommandParser)           │    Exact command matches route here.
        └─────────────┬─────────────┘
                      │ (Unmatched / natural language)
                      ▼
        ┌───────────────────────────┐
        │     TriageRouter          │  ← Sensitivity & Complexity Gating
        └──────┬─────────────┬──────┘
               │             │
        ┌──────┴──────┐      └───────────────────────────┐
        ▼                                                ▼
┌───────────────────────────┐            ┌───────────────────────────────┐
│ Tier 1: Local Edge        │            │ Tier 2: Cloud Specialist      │
│ Engine (Ollama)           │            │ (Nebius Token Factory +       │
│                           │            │  NVIDIA Nemotron 30B / 120B)  │
│ • Low latency offline     │            │                               │
│ • Basic natural language  │            │ • Complex multi-step reasoning│
│ • SENSITIVE commands      │            │ • Agentic tool-use planning   │
│   (data NEVER leaves host)│            │ • PII-scrubbed before dispatch│
└──────────────┬────────────┘            └───────────────┬───────────────┘
               │                                         │
               └─────────────────┬───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │ validate_intent_result()│  ← Allowlist runtime binding
                    └────────────┬────────────┘
                                 ▼
                            IntentResult
```

### The 3-Tier AI Triage Model

| Tier | Engine / Provider | Latency | Network | Role & Responsibility |
|---|---|---|---|---|
| **Tier 0** | Deterministic `CommandParser` | `< 1 ms` | Offline | Exact keyword matches (`greet`, `open`, `close`, `cpu`, `ram`, `time`, file paths). Zero LLM overhead. |
| **Tier 1** | Local Edge Engine (`Ollama` / `llama3.2`) | `~200–500 ms` | Localhost (`127.0.0.1`) | Natural language variants containing file paths or sensitive system data. **Data never leaves the host machine.** |
| **Tier 2** | Cloud Specialist (`Nebius` / `NVIDIA Nemotron`, `OpenAI`, `Gemini`) | Variable | Cloud (TLS) | High-order reasoning, multi-step task planning, abstract logic. All requests are **PII-scrubbed** prior to network transmission. |

### End-to-End Execution Flow

```text
User Input
   │
   ▼
1. validate_input()                [Security: Shell injection & pattern validation]
   │
   ▼
2. Resolution Handlers             [Resolves pending risky closes & terminal disambiguation]
   │
   ▼
3. CommandParser                   [Extracts Intent or detects compound command guard]
   │
   ▼
4. SessionManager.enrich()         [Context memory: pronoun resolution ('close it', 'open it again')]
   │
   ▼
5. PermissionChecker               [Dynamic firewall against config/permissions.json]
   │
   ▼
6. ResourceMonitor.start()         [Tracks execution time and CPU delta]
   │
   ▼
7. IntentEngine → SystemExecutor   [Dispatches to WindowsAdapter / LinuxAdapter]
   │
   ▼
8. PathGuard & OS Execution        [Sandboxed filesystem or OS process execution]
   │
   ▼
9. Telemetry & Audit Logging       [Standardized ActionResult captured in logs/session.log]
```

---

## ✨ Key Features

- **⚡ Zero-Latency Fast Path**: Instantaneous command parsing for repetitive and predictable operational commands.
- **🛡 Enterprise Security Firewall**: Every intent is verified against a dynamic permissions policy (`config/permissions.json`) before execution.
- **📁 Sandboxed File System Tools**: Complete suite of managed file/folder operations (`create_file`, `read_file`, `write_file`, `append_file`, `delete_file`, `copy_file`, `move_file`, `create_folder`, `delete_folder`, `move_folder`, `list_directory`), isolated within a designated workspace sandbox via `PathGuard`.
- **💻 Safe Terminal & Process Management**: Deep Windows Terminal session inspection with trust scoring to avoid terminating active IDE shells, editor tasks, or build processes inadvertently.
- **🤖 Privacy-First Hybrid AI**: Automatic routing between local Ollama instances and cloud providers (Nebius AI Studio, OpenAI, Gemini) based on data sensitivity and task complexity.
- **🔒 Cloud PII Redaction**: Automatic stripping of local user accounts, usernames, and Windows/Linux home directory paths before any cloud model payload is dispatched.
- **🧠 Conversational Memory**: Remembers previous turns, context targets, and resolved pronouns (`"close it"`, `"open it again"`, `"also check memory"`).
- **📊 Execution Auditing & Resource Metrics**: Records granular execution time, CPU usage delta, and standardized `ActionResult` states for every operation.
- **🤖 Automation Framework Foundation**: Dedicated automation layer (`src/automation`) with session lifecycle management and mouse, keyboard, and window controllers ready for desktop UI automation.

---

## 💻 Platform Support Matrix

| Feature / Capability | Windows 10/11 | Linux / Ubuntu | macOS |
|---|---|---|---|
| **Core Engine & Intent Pipeline** | ✅ Full | ✅ Full | 🔄 Planned |
| **System Metrics (CPU, RAM, Time)** | ✅ Full | ✅ Full | 🔄 Planned |
| **File System Sandbox (`PathGuard`)** | ✅ Full | ✅ Full | 🔄 Planned |
| **Application Launch & Process Kill** | ✅ Full | ✅ Full | 🔄 Planned |
| **Terminal Trust & Disambiguation** | ✅ Full (Win32 APIs) | ⚠️ Basic PID tracking | 🔄 Planned |
| **COM Window Management (Explorer)**| ✅ Full (pywin32) | N/A | N/A |
| **AI Triage & Classification** | ✅ Full | ✅ Full | ✅ Full |
| **Automation Manager Foundation** | ✅ WindowsBackend | 🔄 In Progress | 🔄 Planned |

---

## 📂 Repository Structure

```text
Deniz/
├── main.py                     # Interactive assistant CLI entrypoint
├── pyproject.toml              # Build config, dependencies, pytest & coverage settings
├── requirements.txt            # Base Python requirements
├── Readme.md                   # Comprehensive project documentation
├── CONTRIBUTING.md             # Developer workflow and contribution guidelines
│
├── config/                     # Runtime configuration files
│   ├── ai_config.json          # Provider settings (Nebius, Ollama, OpenAI, Gemini)
│   ├── permissions.json        # Intent firewall allowlist/denylist
│   └── settings.json           # Workspace root and sandbox containment configuration
│
├── docs/                       # Architectural & design documentation
│   ├── AI_LAYER.md             # Deep-dive documentation for Phase 10 AI layer
│   ├── Roadmap.md              # Master multi-phase engineering roadmap
│   ├── architecture.md         # ASCII architecture and triage diagrams
│   ├── automation_roadmap.md   # UI automation and desktop control roadmap
│   └── folder_structure.md     # Reference layout for future expansion
│
├── scripts/
│   └── test_ai.py              # Diagnostic CLI tool for AI routing & PII scrubbing verification
│
├── src/                        # Core source code (installed in editable mode)
│   ├── engine.py               # Main AssistantEngine orchestrator
│   │
│   ├── adapters/               # OS-level hardware and system adapters
│   │   ├── base_adapter.py     # Abstract base adapter contract
│   │   ├── windows_adapter.py  # Win32 / COM / process adapter
│   │   ├── linux_adapter.py    # Linux POSIX / procfs adapter
│   │   ├── factory.py          # OS detection and adapter factory
│   │   ├── terminal_constants.py
│   │   └── terminal_windows.py
│   │
│   ├── ai/                     # AI Foundation Layer (Phase 10)
│   │   ├── schema.py           # IntentResult dataclass & validation logic
│   │   ├── router.py           # TriageRouter (Tier 0 / Tier 1 / Tier 2 gating)
│   │   ├── prompt_builder.py   # Few-shot prompts & Cloud PII scrubber
│   │   ├── classifier.py       # AIClassifier with fail-closed guarantee
│   │   └── providers/          # Modular LLM provider integrations
│   │       ├── base_provider.py
│   │       ├── nebius_provider.py   # Nebius Token Factory + NVIDIA Nemotron
│   │       ├── ollama_provider.py   # Local edge Ollama provider
│   │       ├── openai_provider.py   # OpenAI GPT-4o fallback
│   │       └── gemini_provider.py   # Google Gemini fallback
│   │
│   ├── automation/             # Desktop UI Automation Framework
│   │   ├── manager.py          # AutomationManager orchestrator
│   │   ├── session.py          # AutomationSession lifecycle
│   │   ├── enums.py / errors.py
│   │   ├── backends/           # BaseBackend, WindowsBackend
│   │   └── controllers/        # Mouse, Keyboard, Window controllers
│   │
│   ├── core/                   # Platform-agnostic execution core
│   │   ├── parser.py           # Deterministic CommandParser & compound guards
│   │   ├── intent_engine.py    # Maps intents to execution handlers
│   │   ├── action_registry.py  # Intent registry
│   │   ├── action_results.py   # Standardized ActionResult contract
│   │   ├── audit_log.py        # Structured execution telemetry logger
│   │   ├── session_context.py  # Conversational memory & pronoun enricher
│   │   ├── system_executor.py  # Adapter facade
│   │   ├── intent_resolution.py
│   │   ├── executor/           # Window and execution helpers
│   │   ├── monitoring/         # ResourceMonitor (CPU delta & latency)
│   │   ├── security/           # PathGuard sandbox, validator, permissions, terminal trust
│   │   └── session/            # AppRegistry & terminal disambiguation
│   │
│   └── utils/                  # Logging, loaders, and shared helpers
│       └── logger.py           # Synchronized console & session logger
│
├── tests/                      # Automated test suite (589+ tests)
│   ├── unit/                   # Comprehensive unit tests for all modules
│   ├── integration/            # End-to-end full execution flow tests
│   ├── conftest.py             # Pytest fixtures and mock adapters
│   └── helpers.py              # Test doubles and execution assertions
│
├── workspace/                  # Default sandboxed directory for safe file operations
└── logs/                       # Runtime logs (session.log)
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: `>= 3.10` (tested on Python 3.10, 3.11, 3.12)
- **Git**
- *(Optional for Tier 1)*: [Ollama](https://ollama.ai/) installed and running locally on `http://localhost:11434` with model `llama3.2`
- *(Optional for Tier 2)*: Nebius AI Studio, OpenAI, or Gemini API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mohdsarfraz08/Deniz-core.git
   cd Deniz-core
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies in editable mode:**
   ```bash
   # Windows (includes pywin32, testing & AI dependencies)
   pip install -e ".[dev,windows]"

   # Linux / Ubuntu (core dependencies)
   pip install -e ".[dev]"
   ```

### Configuration & Environment Variables

Deniz functions immediately out of the box for deterministic operations. To activate Tier 2 cloud intelligence or configure model endpoints, configure `config/ai_config.json` and set your API keys:

```bash
# Windows (PowerShell)
$env:NEBIUS_API_KEY="your-nebius-api-key"
$env:OPENAI_API_KEY="your-openai-api-key"    # Optional fallback
$env:GEMINI_API_KEY="your-gemini-api-key"    # Optional fallback

# Linux / macOS (Bash)
export NEBIUS_API_KEY="your-nebius-api-key"
export OPENAI_API_KEY="your-openai-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
```

---

## 💡 Usage & Examples

### 1. Interactive Assistant CLI

Launch the primary conversational loop:

```bash
python -m venv venv
.\venv\Scripts\activate   # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev,windows]"   # Linux: pip install -e ".[dev]"
python main.py
```

```text
Assistant v2.1 (Core) online. Type 'exit' to quit.
You: hello
Assistant: Hello. System operational.

You: check cpu
Assistant: CPU usage: 12.4%

You: also check memory
Assistant: Memory usage: 48.2% (15.8 GB used of 31.9 GB)

You: open notepad
Assistant: notepad opened successfully.

You: close it
Assistant: notepad closed successfully.

You: create file notes.txt meeting at 3pm
Assistant: File 'notes.txt' created successfully.

You: read file notes.txt
Assistant: Content of 'notes.txt':
meeting at 3pm

You: list files
Assistant: Contents of '.':
  [FILE] notes.txt

You: exit
System offline.
```

### 2. AI Layer Diagnostic Tool

Use `scripts/test_ai.py` to inspect triage routing, PII scrubbing, and classifier results without invoking the full assistant:

```bash
# Test a sensitive file operation (routes to Tier 1 - Local Edge Ollama)
python scripts/test_ai.py "delete file C:/Users/john/Documents/report.docx"
```

```text
============================================================
Query: 'delete file C:/Users/john/Documents/report.docx'
------------------------------------------------------------
Triage Decision:
  - Tier:        1
  - Sensitivity: SENSITIVE
  - Reason:      Matched sensitive file operation: delete_file
...
Result:
  - Intent:     delete_file
  - Target:     report.docx
  - Confidence: 1.00
  - Tier:       1
  - Actionable: True
============================================================
```

```bash
# Interactive diagnostic shell
python scripts/test_ai.py
```

---

## 🔒 Security, AI Ethics & Governance

### PathGuard 3-Layer Sandbox
All file and directory commands are guarded by `src/core/security/path_guard.py`:
1. **Workspace Boundary Confinement**: Operations are strictly anchored within the designated `workspace/` folder. Directory traversal attempts (`../`, `..\`) raise `PathSecurityError`.
2. **Device & Protocol Hardening**: Rejects Windows DOS reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9` - CWE-440), UNC network paths (`\\server\share`), and NTFS Alternate Data Streams (`file.txt:hidden`).
3. **Symlink Escape Prevention**: Canonical path resolution verifies that symlinks do not resolve to locations outside the sandbox root.

### Terminal Session Trust & Safe Process Termination
When closing applications or killing processes, Deniz avoids naive `taskkill` commands:
- Detects whether a terminal process belongs to an active IDE (VS Code, JetBrains), terminal multiplexer, or external shell.
- Prompts for explicit user confirmation if multiple ambiguous sessions or unsaved processes are detected.

### Dynamic Permission Firewall
`config/permissions.json` defines granular execution boundaries:
- High-risk operations (`dangerous_system`: shutdown, format, reboot) are disabled by default (`false`).
- Permissions can be locked down or opened per deployment environment without altering code.

### Fail-Closed Guarantee
- Any model hallucination proposing an unrecognized intent is automatically caught by `validate_intent_result()` and downgraded to `unknown`.
- Network outages, JSON parse failures, and provider timeouts fail closed to `IntentResult(intent="unknown", confidence=0.0)`—guaranteeing that Deniz will never crash or execute unvetted instructions.

---

## 🧪 Testing & Quality Assurance

The codebase enforces strict test coverage and verification standards:

```bash
# Run the complete test suite
pytest tests/

# Run tests with summary
pytest tests/ -q

# Run with detailed coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Enforce the CI 80% coverage threshold
pytest tests/ --cov=src --cov-fail-under=80
```

### Continuous Integration (CI)
GitHub Actions (`.github/workflows/ci.yml`) runs on every push and PR:
- **`windows-latest`**: Executes all 589+ unit and integration tests; enforces `--cov-fail-under=80` (currently achieving **85%** overall coverage).
- **`ubuntu-latest`**: Executes portable core and POSIX tests; automatically skips platform-exclusive Windows API tests via `@pytest.mark.windows_only`.

---

## 🧭 Master Roadmap Status

| Phase | Milestone | Focus Area | Status | Deliverables & Verification |
|---|---|---|---|---|
| **Phase 1** | Foundation | Environment, dependencies, project layout | ✅ Completed | Virtualenv, packaging, baseline scripts |
| **Phase 2** | Minimal Slice | Core execution loop & basic intents | ✅ Completed | `main.py`, `engine.py`, `greet`, `open_app`, `close_app` |
| **Phase 3** | System Awareness | Hardware resource metrics | ✅ Completed | CPU, RAM, Time tracking, resource deltas |
| **Phase 4** | Security Layer | Input validation & permission firewall | ✅ Completed | Injection sanitization, `permissions.json` |
| **Phase 5** | Session & Memory | Conversational context & memory | ✅ Completed | Pronoun resolution, follow-up intent enrichment |
| **Phase 6** | Cross-Platform | OS adapter abstraction | ✅ Completed | `BaseAdapter`, `WindowsAdapter`, `LinuxAdapter` |
| **Phase 7** | Quality Gate | Test suite & CI stabilization | ✅ Completed | 195+ tests, `--cov-fail-under=80` |
| **Phase 8** | Execution Hardening | Fault tolerance & structured telemetry | ✅ Completed | `ActionResult` contract, execution auditing |
| **Phase 9** | Tool Expansion | OS filesystem manipulation | ✅ Completed | 11 file/folder tools, `PathGuard` 3-layer sandbox |
| **Phase 10** | AI Foundation | Nebius × NVIDIA 3-tier triage architecture | ✅ Completed | `TriageRouter`, Ollama edge, Nebius cloud, PII scrubber |
| **Phase 11** | Hybrid Router | Unified deterministic + AI intent routing | 🚀 Active | Deterministic fast path with AI fallback in `AssistantEngine` |
| **Phase 12** | Multi-Step Planner | Agentic planning & task decomposition | 📋 Planned | Complex goal breakdown into tool execution DAGs |
| **Phase 13** | UI Automation | Desktop GUI control & element interaction | 📋 Planned | Win32 UIA tree inspection, mouse/keyboard automation |
| **Phase 14** | Long-Term Memory | Vector store & semantic memory | 📋 Planned | Persistent preferences, session retrieval |
| **Phase 15** | Multi-Modal Perception | Vision & Voice interfaces | 📋 Planned | Screen OCR, desktop vision fallback, STT / TTS |

*For complete details, see [docs/Roadmap.md](docs/Roadmap.md) and [docs/AI_LAYER.md](docs/AI_LAYER.md).*

---

<!-- ## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Review [CONTRIBUTING.md](CONTRIBUTING.md) for testing guidelines and architecture norms.
2. Fork the repository and create a feature branch (`git checkout -b feature/my-feature`).
3. Ensure all tests pass and coverage remains above 80%:
   ```bash
   pytest tests/ --cov=src --cov-fail-under=80
   ```
4. Commit your changes and open a Pull Request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE). -->
