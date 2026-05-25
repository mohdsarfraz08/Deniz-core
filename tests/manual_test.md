Here’s a practical manual test guide for your machine (you’re on **Windows**).

## 1. Setup and start

From the repo root (`d:\Project\Deniz`):

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -e ".[dev,windows]"
python main.py
```

You should see something like `Assistant v2.1 (Core) online. Type 'exit' to quit.`  
The engine picks **WindowsAdapter** automatically on Windows.

Optional: confirm automated tests first:

```powershell
pytest tests/ -q --cov=src --cov-fail-under=80
```

---

## 2. Core flow (both platforms)

Work through these in order in the CLI. After each line, check the **Assistant:** reply and optionally `logs/session.log`.

| You type | Expected behavior |
|----------|-------------------|
| `hello` | Greeting (“Hello. System operational.”) |
| `check cpu` | CPU % (may take ~1s on Windows/Linux) |
| `also` | Memory % (session follow-up after CPU) |
| `what time is it` | Current time |
| `what else` | After time, often bridges to CPU |
| `sdlkfjsldkfjsldkj` | “I didn’t understand that command.” (not “Access denied”) |
| `remind me at noon` | “That feature is not implemented yet.” |
| `shutdown system` | “Access denied for this action.” |
| *(empty Enter)* | Ignored (no response) |
| `   ` then Enter | Same as empty in CLI; engine would say empty if you called `handle` directly |

Exit with `exit` or `quit`.

---

## 3. Security / validation (safe, non-destructive)

| You type | Expected |
|----------|----------|
| `open notepad; calc` | Rejected — disallowed characters |
| `greet && whoami` | Rejected — disallowed characters |

These should **not** launch apps.

---

## 4. Apps and session (Windows)

Use apps you’re OK opening/closing.

| You type | Expected |
|----------|----------|
| `open notepad` | Notepad opens; success message |
| `close it` | Closes last opened app (notepad) via session |
| `open notepad` then `close notepad` | Closes by name |
| `open it again` / `launch it again` | Reopens last app from session |

**File Explorer (Windows-specific):**

| You type | Expected |
|----------|----------|
| Open File Explorer manually, then `close file explorer` | Window-level close message (count of windows) |
| `close explorer` | Same family of behavior |

---

## 5. Windows-only (terminals)

Only test if you’re comfortable closing terminals you opened for testing.

| You type | Expected |
|----------|----------|
| `open powershell` | New terminal (may prefer Windows Terminal) |
| `close terminal` | Focused/registry-based close; may ask to focus or list sessions |
| Multiple terminals open, unfocused `close terminal` | May list options; reply with `1`, `close 2`, or a PID from the list |
| Risky workload in terminal, then `close terminal` | May ask yes/no; `yes` / `no` |

Repeat launch within a few seconds → duplicate launch debounce message.

---

## 6. Linux manual test (if you have WSL or a VM)

```bash
cd /path/to/Deniz
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
python main.py
```

| You type | Expected |
|----------|----------|
| `hello`, `check cpu`, `also` | Same core behavior as Windows |
| `open gedit` (or another app in PATH) | Launches via `which` |
| `close gedit` | Terminates matching process |
| `close file manager` with Nautilus/Dolphin open | Process-level close (not per-window like Windows) |
| `close terminal` | Generic close / blocklist behavior — **no** Windows-style disambiguation |

Integration smoke on Linux only:

```bash
pytest tests/integration/test_linux_flow.py -v
```

---

## 7. What to watch while testing

1. **Console** — `Assistant:` lines match the table above.  
2. **`logs/session.log`** — intent name and timing after successful commands (not full chat transcript).  
3. **No crashes** — `Internal processing error` or init failure should not appear for normal phrases.  
4. **Permissions** — edit `config/permissions.json` (e.g. set `"greet": false`), restart CLI, `hello` → “Access denied”.

---

## 8. Quick smoke without the interactive CLI

One-shot checks from the repo root:

```powershell
python -c "from engine import AssistantEngine; e=AssistantEngine(); print(e.handle('hello')); print(e.handle('check cpu'))"
```

---

## 9. Safety tips

- Don’t manually test `shutdown system` expecting it to run — it should stay **denied**.  
- Prefer **notepad/calc** over system processes for open/close.  
- Terminal close tests can end real shells — use a dedicated test window.  
- On Linux, file-manager close kills **processes** (Nautilus, etc.), not individual folder windows.

If you want, we can turn this into a copy-paste checklist file in `docs/` for the repo.