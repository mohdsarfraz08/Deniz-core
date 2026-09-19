# 🤖 Phase 10 — AI Foundation Layer Documentation
## Version 4.0: Nebius × NVIDIA Triage Architecture

The Phase 10 AI Foundation Layer introduces natural language intent classification to Deniz without destabilizing or modifying the underlying execution pipeline.

---

## 1. Architecture Overview

Deniz employs a **three-tier triage architecture**. Every user utterance is analyzed for complexity and data sensitivity before any large language model (LLM) is contacted:

```
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

---

## 2. Module Inventory

| Module | Responsibility | Key Classes & Functions |
|---|---|---|
| `src/ai/schema.py` | Authoritative data contract | `IntentResult`, `IntentValidationError`, `validate_intent_result`, `unknown_result` |
| `src/ai/router.py` | 3-tier classification & sensitivity gating | `TriageRouter`, `Sensitivity`, `TriageDecision` |
| `src/ai/prompt_builder.py` | Prompt construction & PII scrubbing | `PromptBuilder` |
| `src/ai/classifier.py` | Orchestration, tier dispatch & fail-closed fallback | `AIClassifier`, `_extract_json_payload` |
| `src/ai/providers/base_provider.py` | Abstract provider interface | `AbstractProvider`, `ProviderError` |
| `src/ai/providers/ollama_provider.py` | Tier 1 local edge provider | `OllamaProvider` |
| `src/ai/providers/nebius_provider.py` | Tier 2 Nebius Token Factory + NVIDIA Nemotron | `NebiusProvider` |
| `src/ai/providers/openai_provider.py` | Cloud fallback provider | `OpenAIProvider` |
| `src/ai/providers/gemini_provider.py` | Cloud fallback provider | `GeminiProvider` |
| `src/ai/providers/__init__.py` | Provider factory registry | `get_provider()` |

---

## 3. AI Ethics & Data Governance

### 3.1 Tier-Based Sensitivity Boundary (On-Device Isolation)
- Any command matching file system operations (`create_file`, `delete_file`, `write_file`, `move_file`, `list_directory`, etc.) or containing workspace paths is strictly tagged `Sensitivity.SENSITIVE`.
- **Guarantee:** Sensitive commands are **never** transmitted over external networks or sent to cloud LLMs. They are exclusively handled by Tier 1 (Ollama on `127.0.0.1`).

### 3.2 Cloud PII Scrubbing
- Whenever an utterance is routed to Tier 2 (Nebius Cloud Specialist), `PromptBuilder` passes the input through `sanitise_for_audit()`.
- Windows user home paths (`C:\Users\<username>\...`) and Linux home paths (`/home/<username>/...`) are redacted before HTTP payload construction.

### 3.3 Dynamic Allowlist Binding
- `validate_intent_result()` checks proposed intents against `config/permissions.json` at runtime.
- If a model hallucinates an intent not registered in permissions, `IntentValidationError` is raised, triggering fail-closed fallback to `unknown`.

### 3.4 Strict Fail-Closed Guarantee
- No exception from any provider, timeout, network error, or malformed JSON ever crashes the application.
- All error pathways return `IntentResult(intent="unknown", confidence=0.0)`.

---

## 4. Configuration & Provider Switching

Configured in `config/ai_config.json`:

```json
{
  "tier2": {
    "provider": "nebius",
    "model": "nvidia/llama-3.1-nemotron-70b-instruct",
    "timeout_s": 30.0,
    "max_retries": 2,
    "data_governance": {
      "pii_scrubbing": true,
      "input_logged_to_audit": true,
      "data_leaves_device": true,
      "provider": "Nebius AI Studio",
      "provider_privacy_policy": "https://nebius.com/legal/privacy-policy",
      "model_vendor": "NVIDIA",
      "model_license": "NVIDIA Open Model License"
    }
  },
  "tier1": {
    "provider": "ollama",
    "model": "llama3.2",
    "timeout_s": 10.0,
    "max_retries": 1,
    "data_governance": {
      "pii_scrubbing": false,
      "data_leaves_device": false
    }
  },
  "tier0": {
    "provider": "deterministic",
    "description": "Zero latency deterministic command parser"
  }
}
```

### Environment Variables
- `NEBIUS_API_KEY`: Required for Tier 2 Nebius Token Factory.
- `OPENAI_API_KEY`: Required if Tier 2 provider is switched to `openai`.
- `GEMINI_API_KEY`: Required if Tier 2 provider is switched to `gemini`.

---

## 5. Verification & Testing

### 5.1 Automated Unit Tests (CI — 100% Mocked)
```bash
pytest tests/unit/test_ai_classifier.py -v
pytest tests/ -q --cov=src --cov-fail-under=80
```

### 5.2 Diagnostic CLI
```bash
# Single command test
python scripts/test_ai.py "launch edge browser"

# Sensitive test (routes to Tier 1)
python scripts/test_ai.py "delete C:/Users/alice/Documents/temp.txt"

# Complex reasoning test (routes to Tier 2)
python scripts/test_ai.py "plan a multi-step sequence to build a web scraper"

# Interactive loop
python scripts/test_ai.py
```
