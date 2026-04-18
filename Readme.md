# Assistant v1

Rule-based CLI assistant: parse user text into intents, route through a platform-agnostic core, and execute actions via OS adapters.

## Architecture

| Layer | Role |
|--------|------|
| **`main.py`** | CLI loop; no business logic. |
| **`engine.py`** | Orchestrates parse → intent execution → resource metrics and logging. |
| **`core/parser.py`** | Normalizes input and returns structured `Intent` objects. |
| **`core/intent_engine.py`** | Maps intents to handlers via `ActionRegistry`; no OS calls. |
| **`core/action_registry.py`** | Intent name → callable registration. |
| **`adapters/`** | `BaseAdapter` defines the contract; `WindowsAdapter` implements Windows behavior. |
| **`core/monitoring/resource_monitor.py`** | Execution time and CPU delta around each intent. |
| **`utils/logger.py`** | Console and `logs/session.log` output. |

Data flow: **input → `CommandParser` → `IntentEngine` → adapter (`SystemExecutor`) → response**, with metrics recorded after execution.

## Run

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Tests

```bash
pytest tests/
```
