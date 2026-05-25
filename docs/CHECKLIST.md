# Assistant-v1 — Phase checklist (archived)

> **This document is deprecated as a source of truth.** Use [`Roadmap.md`](Roadmap.md) for phase status and [`CONTRIBUTING.md`](../CONTRIBUTING.md) for how to run tests and coverage. This file is retained as a historical audit trail aligned with the repo as of Phase 7 stabilization.

---

## Phase 1–5: Feature complete (Windows)

| Area | Status | Notes |
|------|--------|--------|
| Foundation | Done | `src/` layout, `pyproject.toml`, `requirements.txt`, README |
| Core pipeline | Done | `main.py` → `engine.py` → parser → intent engine → adapter |
| System intents | Done | CPU, memory, time (+ aliases) |
| Security | Done | `validate_input`, `config/permissions.json`, deny-before-execute |
| Session context | Done | Follow-ups (`also`), pronouns (`close it`), reopen last app |
| Windows adapter | Done | Apps, terminals, File Explorer, risk confirmation |
| Linux adapter | Done (minimal) | `linux_adapter.py` + `factory.py`; Ubuntu CI |

---

## Phase 7: Testing & stabilization

| Item | Status | Where |
|------|--------|--------|
| Unit tests (~130+ cases) | Done | `tests/unit/` |
| Integration smoke test | Done | `tests/integration/test_full_flow.py` |
| Shared fixtures | Done | `tests/conftest.py` (`MiniExecutor`, permissions helpers) |
| Coverage tooling | Done | `pytest-cov` in `[dev]`; see CONTRIBUTING |
| CI (Windows) | Done | `.github/workflows/ci.yml` on `windows-latest` |
| Coverage 80% gate | Done | `--cov-fail-under=80` in CI and `pyproject.toml` |

### Ethics & logging (ongoing awareness)

- No background monitoring beyond the interactive CLI loop.
- Engine logs intent names and timing metrics, not full conversational transcripts by default.
- **P2:** `utils/logger.py` policy tests and optional redaction toggles remain future work.

---

## Definition of done (v1 Windows, pre–Phase 6)

- [x] CLI runs (`python main.py`)
- [x] Rule-based intents and session context
- [x] Permission firewall
- [x] Windows adapter behind `BaseAdapter`
- [x] Resource metrics logged per intent
- [x] Test suite + CI quality gate
- [x] Linux adapter and OS auto-detection (Phase 6 minimal)
