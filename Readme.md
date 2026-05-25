# Assistant v1

Rule-based CLI assistant: parse user text into intents, route through a platform-agnostic core, and execute actions via OS adapters.

## Architecture

| Layer | Role |
|--------|------|
| **`main.py`** (repo root) | CLI loop; no business logic. |
| **`src/engine.py`** | Orchestrates parse → intent execution → resource metrics and logging. |
| **`src/core/parser.py`** | Normalizes input and returns structured `Intent` objects. |
| **`src/core/intent_engine.py`** | Maps intents to handlers via `ActionRegistry`; no OS calls. |
| **`src/core/action_registry.py`** | Intent name → callable registration. |
| **`src/adapters/`** | `BaseAdapter` contract; `WindowsAdapter` (full) or `LinuxAdapter` (core); `factory.py` picks by OS. |
| **`src/core/monitoring/resource_monitor.py`** | Execution time and CPU delta around each intent. |
| **`src/utils/logger.py`** | Console and `logs/session.log` output. |

Data flow: **input → `CommandParser` → `IntentEngine` → adapter (`SystemExecutor`) → response**, with metrics recorded after execution.

## Platform support

| Platform | Status | Notes |
|----------|--------|--------|
| **Windows** | Full | Apps, terminals, File Explorer (COM), risk confirmation, session registry |
| **Linux** | Core | Open/close apps, CPU/memory/time, file-manager process close; no terminal disambiguation |

## Run

```bash
python -m venv venv
.\venv\Scripts\activate   # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev,windows]"   # Linux: pip install -e ".[dev]"
python main.py
```

Install the project in editable mode so imports (`core`, `engine`, `adapters`, …) resolve from `src/`. See [CONTRIBUTING.md](CONTRIBUTING.md) for layout and test notes.

## Tests

```bash
pytest tests/
pytest tests/ -q
pytest tests/ --cov=src --cov-report=term-missing
pytest tests/ --cov=src --cov-fail-under=80
```

CI runs on **Windows** and **Ubuntu** (see `.github/workflows/ci.yml`). Windows enforces **80%** coverage; Ubuntu runs portable tests (`windows_only` tests are skipped). See [CONTRIBUTING.md](CONTRIBUTING.md) for layout and test helpers.
