# Folder Structure

```Folder Struct
Deniz/
│
├── main.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
│
├── docs/
│   ├── architecture/
│   ├── roadmap/
│   ├── api/
│   ├── development/
│   ├── deployment/
│   └── images/
│
├── config/
│   ├── settings.json
│   ├── permissions.json
│   ├── models.json
│   └── logging.json
│
├── assets/
│   ├── icons/
│   ├── sounds/
│   └── images/
│
├── logs/
│
├── data/
│   ├── memory/
│   ├── cache/
│   ├── embeddings/
│   └── database/
│
├── scripts/
│
├── src/
│   │
│   ├── engine.py
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   ├── classifier.py
│   │   ├── router.py
│   │   ├── prompt_builder.py
│   │   │
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base_provider.py
│   │   │   ├── nebius_provider.py
│   │   │   ├── gemini_provider.py
│   │   │   ├── openai_provider.py
│   │   │   └── ollama_provider.py
│   │   │
│   │   ├── models/
│   │   │   ├── base_model.py
│   │   │   ├── local_model.py
│   │   │   └── model_registry.py
│   │   │
│   │   ├── reasoning/
│   │   ├── planner/
│   │   ├── memory/
│   │   ├── embeddings/
│   │   ├── tools/
│   │   └── training/
│   │
│   ├── perception/
│   │   ├── vision/
│   │   │   ├── screenshot.py
│   │   │   ├── ocr.py
│   │   │   ├── object_detection.py
│   │   │   └── image_matching.py
│   │   │
│   │   ├── speech/
│   │   │   ├── speech_to_text.py
│   │   │   └── text_to_speech.py
│   │   │
│   │   └── input/
│   │
│   ├── automation/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── session.py
│   │   │
│   │   ├── backends/
│   │   │   ├── base_backend.py
│   │   │   ├── windows_backend.py
│   │   │   ├── linux_backend.py
│   │   │   └── macos_backend.py
│   │   │
│   │   ├── controllers/
│   │   │   ├── mouse_controller.py
│   │   │   ├── keyboard_controller.py
│   │   │   ├── window_controller.py
│   │   │   ├── clipboard_controller.py
│   │   │   ├── dialog_controller.py
│   │   │   ├── form_controller.py
│   │   │   ├── menu_controller.py
│   │   │   ├── table_controller.py
│   │   │   ├── tree_controller.py
│   │   │   └── tab_controller.py
│   │   │
│   │   ├── search/
│   │   │   ├── finder.py
│   │   │   ├── selectors.py
│   │   │   ├── filters.py
│   │   │   └── cache.py
│   │   │
│   │   ├── readers/
│   │   │   ├── ui_reader.py
│   │   │   ├── element_reader.py
│   │   │   └── window_reader.py
│   │   │
│   │   ├── applications/
│   │   │   ├── chrome.py
│   │   │   ├── edge.py
│   │   │   ├── explorer.py
│   │   │   ├── vscode.py
│   │   │   ├── paint.py
│   │   │   ├── terminal.py
│   │   │   ├── word.py
│   │   │   ├── excel.py
│   │   │   └── powerpoint.py
│   │   │
│   │   ├── models/
│   │   └── utils/
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   ├── intent_engine.py
│   │   ├── intent_resolution.py
│   │   ├── action_registry.py
│   │   ├── action_results.py
│   │   ├── session_context.py
│   │   │
│   │   ├── execution/
│   │   │   ├── system_executor.py
│   │   │   ├── task_executor.py
│   │   │   └── workflow_executor.py
│   │   │
│   │   ├── security/
│   │   ├── monitoring/
│   │   ├── session/
│   │   └── workflow/
│   │
│   ├── interfaces/
│   │   ├── desktop/
│   │   ├── web/
│   │   ├── cli/
│   │   └── voice/
│   │
│   ├── api/
│   │   ├── routes/
│   │   ├── middleware/
│   │   ├── schemas/
│   │   └── server.py
│   │
│   ├── services/
│   │   ├── assistant/
│   │   ├── conversation/
│   │   ├── notifications/
│   │   ├── workspace/
│   │   └── updater/
│   │
│   ├── infrastructure/
│   │   ├── config/
│   │   ├── logging/
│   │   ├── database/
│   │   ├── cache/
│   │   ├── events/
│   │   └── dependency_injection/
│   │
│   ├── plugins/
│   │   ├── manager.py
│   │   └── builtins/
│   │
│   ├── adapters/
│   │   ├── base_adapter.py
│   │   ├── windows_adapter.py
│   │   ├── linux_adapter.py
│   │   ├── macos_adapter.py
│   │   └── factory.py
│   │
│   └── utils/
│       ├── logger.py
│       ├── file_loader.py
│       ├── helpers.py
│       └── constants.py
│
└── tests/
    ├── unit/
    ├── integration/
    ├── automation/
    ├── ai/
    ├── perception/
    ├── api/
    └── fixtures/