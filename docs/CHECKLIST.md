# 🚀 Assistant-v1 Development Checklist

> **Status:** In progress — only items below marked `[x]` are implemented and verified in the repo today.

---

## 🔵 Phase 1: Foundation Setup

- [x] Initialize Git repo
- [x] Setup `.gitignore`
- [x] Create virtual environment *(local dev; `venv`/`.venv` ignored — not committed)*
- [x] Add `requirements.txt`
- [x] Install `psutil`
- [ ] Setup folder structure exactly as defined *(differs from `docs/folder_structure.md`: no `core/security/`, `config/`, `linux_adapter`, etc.)*
- [x] Add README with architecture explanation

---

## 🔵 Phase 2: Core Logic Implementation

### Parser

- [x] Lowercase normalization
- [x] Trim whitespace
- [ ] Remove unsafe characters *(only whitespace normalization; no injection / shell-metacharacter stripping)*
- [x] Unit tests pass

### Intent Engine (Rule-Based)

- [ ] Basic command detection (open, exit, help) *(open/greet/close patterns exist; no `help` intent; CLI handles `exit`/`quit` outside the parser)*
- [x] Intent mapping system
- [x] No OS-specific logic inside
- [x] Unit tests pass

### Action Registry

- [x] Centralized intent → callable mapping
- [x] Easily extendable dictionary structure
- [x] No direct execution logic here

---

## 🔵 Phase 3: Security Layer

### Validator

- [ ] Reject empty input *(skipped in `main` before `handle`; not centralized in parser/engine)*
- [ ] Block dangerous shell patterns
- [ ] Unit tests for malicious input

### Permissions

- [ ] Load permissions.json
- [ ] Validate intent against whitelist
- [ ] Deny by default if missing
- [ ] Unit tests pass
- [ ] Confirm permission check happens BEFORE execution

---

## 🔵 Phase 4: Adapter Layer

- [x] Implement BaseAdapter (abstract class)
- [x] Implement Windows adapter
- [ ] Implement Linux adapter
- [ ] Dynamic OS detection *(engine instantiates `WindowsAdapter` directly)*
- [x] No platform logic in core

---

## 🔵 Phase 5: Monitoring & Logging

### Resource Monitor

- [x] Measure execution time delta
- [x] Measure CPU usage delta
- [x] Return metrics dictionary
- [ ] Unit test validation *(no `test_resource_monitor` / dedicated tests)*

### Logger

- [x] Log actions safely
- [ ] Do not log raw shell input if disabled *(no toggle; no `settings.json`)*
- [ ] Respect settings.json flags

---

## 🔵 Phase 6: Integration Testing

- [ ] Test full flow pipeline
- [ ] Simulate blocked permission
- [ ] Simulate allowed execution
- [ ] Validate metrics recorded
- [ ] Validate logs written

---

## 🔵 Phase 7: Ethics Validation

- [x] No background loops running *(only interactive CLI loop)*
- [x] No hidden monitoring
- [ ] Resource monitor runs only after execution *(tracking starts before intent execution in `engine.py`)*
- [ ] Permissions default to False *(permissions system not implemented)*
- [x] System fails safely *(errors caught; user-facing fallback messages)*

---

## 🎯 Definition of DONE (v1 Complete)

You can say v1 is complete ONLY IF:

- [x] CLI works
- [x] Rule-based intent works
- [ ] Permission firewall works
- [x] Adapter abstraction works *(Windows implementation; Linux not present)*
- [x] Resource transparency works
- [x] Logs visible to user
- [x] All tests pass *(run `pytest tests/` — 4 unit tests as of last run)*
- [x] No hidden CPU usage
- [x] Clean code (no spaghetti architecture)
