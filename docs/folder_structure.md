# Folder Structure

```bash
assistant-v1/
│
├── main.py                     # CLI entry point only   (no logic)
├── engine.py                   # Central execution orchestrator
├── requirements.txt
├── README.md
├── .gitignore
│
├── core/                       # Platform-agnostic brain
│   ├── __init__.py
│   │
│   ├── parser.py               # Input normalization
│   ├── intent_engine.py        # Rule-based intent detection
│   ├── action_registry.py      # Maps intent → callable action
│   │
│   ├── security/
│   │   ├── __init__.py
│   │   ├── permissions.py      # Permission validation logic
│   │   └── validator.py        # Input sanitization layer
│   │
│   ├── session/
│   │   ├── __init__.py
│   │   └── session_manager.py  # Context memory (no background loops)
│   │
│   └── monitoring/
│       ├── __init__.py
│       └── resource_monitor.py # Post-execution CPU/time usage
│
├── adapters/                   # OS-specific implementations
│   ├── __init__.py
│   ├── base_adapter.py         # Abstract adapter interface
│   ├── windows_adapter.py
│   └── linux_adapter.py
│
├── config/                     # User-controlled configs
│   ├── permissions.json
│   └── settings.json
│
├── logs/
│   └── session.log
│
├── utils/                      # Shared helpers (no business logic)
│   ├── logger.py
│   └── file_loader.py
│
└── tests/
    ├── unit/
    │   ├── test_parser.py
    │   ├── test_permissions.py
    │   ├── test_intent.py
    │   └── test_resource_monitor.py
    │
    └── integration/
        └── test_full_flow.py
```
