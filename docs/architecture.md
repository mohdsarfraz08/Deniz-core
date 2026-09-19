 # Deniz - Hybrid AI Router Architecture                  

                  User Input
                      │
                      ▼
        ┌───────────────────────────┐
        │ Tier 0 — Deterministic    │  ← Zero latency. No model.
        │ (CommandParser)           │    Exact matches route here.
        └─────────────┬─────────────┘
                      │ (Unmatched / natural language)
                      ▼
        ┌───────────────────────────┐
        │     TriageRouter          │  ← Complexity & AI Ethics Sensitivity Gating
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
│ • SENSITIVE file commands │            │ • Agentic tool-use planning   │
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
