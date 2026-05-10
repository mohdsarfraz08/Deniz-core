# Contributing

## Layout

The project uses a **`src/` layout**: importable packages (`core`, `adapters`, `utils`) and the top-level `engine` module live under `src/`. This keeps test and runtime imports aligned with what is declared in `pyproject.toml` and avoids accidentally importing stray modules from the repository root.

## Environment

```bash
python -m venv venv
.\venv\Scripts\activate   # Windows
pip install -e ".[dev]"
```

Editable install (`-e`) is the supported way to run the CLI and tests so `import core`, `import engine`, etc. resolve the same tree you are editing.

## Tests

```bash
pytest tests/
```

`pyproject.toml` sets `pythonpath = ["src"]` for pytest so collection works even if you have not run `pip install -e .` yet; for behavior closest to production, prefer running tests after an editable install.

## Imports

- **Core** (`core/`): parsing, intent routing, security, session context, monitoring — no direct OS calls except through abstractions used by the executor.
- **Adapters** (`adapters/`): host-specific behavior; keep OS and process calls here (or in `core/executor` helpers used only by adapters) so policy and parsing stay testable without the platform layer.
- **Engine** (`engine.py`): orchestration only (validate → parse → session → permissions → execute → metrics).

When adding data loaders or configuration readers, keep I/O at the edges (dedicated modules or small functions) so higher layers stay easy to audit for privacy and policy.
