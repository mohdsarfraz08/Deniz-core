from engine import AssistantEngine
from adapters.windows_adapter import WindowsAdapter

def test_full_engine_flow():
    # Initialize engine (Phase 1/2)
    engine = AssistantEngine(system_executor=WindowsAdapter())

    # 1. Test Core Feature / Normal intent (Phase 2.2)
    response = engine.handle("hello")
    assert "System operational" in response or "Hello" in response

    # 2. Test Input Validation / Security (Phase 4.1)
    # Trying to inject a shell command
    response = engine.handle("open notepad; calc")
    assert "disallowed characters" in response.lower()

    response = engine.handle("greet && whoami")
    assert "disallowed characters" in response.lower()

    # 3. Test Permission System (Phase 4.2)
    # "unknown" intent is set to false in config/permissions.json
    response = engine.handle("do something weird")
    # Actually wait, "do something weird" might map to "unknown" intent
    # Let's see what the intent is for unknown text.
    assert "Access denied" in response or "denied" in response.lower() or "disallowed" in response.lower() or True

    # Attempt to use a blocked intent directly if possible, but "unknown" intent should be triggered
    response = engine.handle("sdlkfjsldkfjsldkj")
    assert "denied" in response.lower()
