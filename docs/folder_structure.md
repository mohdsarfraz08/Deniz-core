# Folder Structure

```Folder Struct
Deniz/
│
├── main.py
├── pyproject.toml
├── requirements.txt
├── Readme.md
├── CONTRIBUTING.md
├── .gitignore
│
├── docs/
│   ├── CHECKLIST.md
│   ├── Roadmap.md
│   ├── folder_structure.md
│   └── manual_test.md
│
├── config/
│   ├── permissions.json
│   └── settings.json
│
├── logs/
│
├── src/
│   ├── engine.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base_adapter.py
│   │   ├── factory.py
│   │   ├── linux_adapter.py
│   │   ├── terminal_constants.py
│   │   ├── terminal_windows.py
│   │   └── windows_adapter.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── action_registry.py
│   │   ├── action_results.py
│   │   ├── intent_engine.py
│   │   ├── intent_resolution.py
│   │   ├── parser.py
│   │   ├── session_context.py
│   │   ├── system_executor.py
│   │   ├── executor/
│   │   │   ├── __init__.py
│   │   │   └── window_executor.py
│   │   │
│   │   ├── monitoring/
│   │   │   ├── __init__.py
│   │   │   └── resource_monitor.py
│   │   │
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── permissions.py
│   │   │   ├── process_kill_policy.py
│   │   │   ├── scoped_terminate.py
│   │   │   ├── terminal_session_analysis.py
│   │   │   ├── terminal_trust.py
│   │   │   └── validator.py
│   │   │
│   │   └── session/
│   │       ├── __init__.py
│   │       ├── app_registry.py
│   │       ├── pending_terminal_disambiguation.py
│   │       └── session_manager.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_loader.py
│   │   └── logger.py
│   │
│   └── assistant_v1.egg-info/
│
└── tests/
    ├── conftest.py
    ├── helpers.py
    ├── manual_test.md
    ├── integration/
    │   ├── test_full_flow.py
    │   └── test_linux_flow.py
    │
    └── unit/
        ├── test_action_registry.py
        ├── test_adapter_factory.py
        ├── test_engine_pipeline.py
        ├── test_engine_risk_confirmation.py
        ├── test_engine_security.py
        ├── test_intent.py
        ├── test_intent_resolution.py
        ├── test_linux_adapter.py
        ├── test_parser.py
        ├── test_parser_edges.py
        ├── test_pending_terminal_disambiguation.py
        ├── test_permissions.py
        ├── test_process_kill_policy.py
        ├── test_resource_monitor.py
        ├── test_scoped_terminate.py
        ├── test_session_context.py
        ├── test_session_registry.py
        ├── test_terminal_constants.py
        ├── test_terminal_risk.py
        ├── test_terminal_session_analysis.py
        ├── test_terminal_trust.py
        ├── test_terminal_windows.py
        ├── test_validator.py
        ├── test_window_executor.py
        └── test_windows_adapter.py
```
