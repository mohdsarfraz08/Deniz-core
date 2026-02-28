# 🚀 assistant-v1 Development Checklist

> Do NOT move to v2 until all tasks are complete.

---

## 🔵 Phase 1: Foundation Setup

- [ ] Initialize Git repo
- [ ] Setup .gitignore
- [ ] Create virtual environment
- [ ] Add requirements.txt
- [ ] Install psutil
- [ ] Setup folder structure exactly as defined
- [ ] Add README with architecture explanation

---

## 🔵 Phase 2: Core Logic Implementation

### Parser

- [ ] Lowercase normalization
- [ ] Trim whitespace
- [ ] Remove unsafe characters
- [ ] Unit tests pass

### Intent Engine (Rule-Based)

- [ ] Basic command detection (open, exit, help)
- [ ] Intent mapping system
- [ ] No OS-specific logic inside
- [ ] Unit tests pass

### Action Registry

- [ ] Centralized intent → callable mapping
- [ ] Easily extendable dictionary structure
- [ ] No direct execution logic here

---

## 🔵 Phase 3: Security Layer

### Validator

- [ ] Reject empty input
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

- [ ] Implement BaseAdapter (abstract class)
- [ ] Implement Windows adapter
- [ ] Implement Linux adapter
- [ ] Dynamic OS detection
- [ ] No platform logic in core

---

## 🔵 Phase 5: Monitoring & Logging

### Resource Monitor

- [ ] Measure execution time delta
- [ ] Measure CPU usage delta
- [ ] Return metrics dictionary
- [ ] Unit test validation

### Logger

- [ ] Log actions safely
- [ ] Do not log raw shell input if disabled
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

- [ ] No background loops running
- [ ] No hidden monitoring
- [ ] Resource monitor runs only after execution
- [ ] Permissions default to False
- [ ] System fails safely

---

## 🎯 Definition of DONE (v1 Complete)

You can say v1 is complete ONLY IF:

- [ ] CLI works
- [ ] Rule-based intent works
- [ ] Permission firewall works
- [ ] Adapter abstraction works
- [ ] Resource transparency works
- [ ] Logs visible to user
- [ ] All tests pass
- [ ] No hidden CPU usage
- [ ] Clean code (no spaghetti architecture)
