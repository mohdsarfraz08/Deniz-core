import sys

import pytest

from engine import AssistantEngine
from adapters.windows_adapter import WindowsAdapter


@pytest.mark.skipif(sys.platform != "win32", reason="Windows adapter integration")
def test_full_engine_flow():
    """Integration path against real Windows adapter (timing-heavy metrics use psutil)."""
    engine = AssistantEngine(system_executor=WindowsAdapter())

    # Greeting (permissions allow greet)
    response = engine.handle("hello")
    assert "System operational" in response or "Hello" in response

    # Validation rejects chained / shell metacharacters before OS calls
    response = engine.handle("open notepad; calc")
    assert "disallowed characters" in response.lower()

    response = engine.handle("greet && whoami")
    assert "disallowed characters" in response.lower()

    # Unrecognized text: clarification (not framed as security denial)
    response = engine.handle("do something weird")
    assert "didn't understand" in response.lower() or "understand" in response.lower()

    response = engine.handle("sdlkfjsldkfjsldkj")
    assert "didn't understand" in response.lower() or "understand" in response.lower()

    # Destructive system intent: permission policy (security)
    response = engine.handle("shutdown system")
    assert "denied" in response.lower()

    # Edge: empty / whitespace-only rejected by validator (no adapter invocation)
    assert engine.handle("") == "Input cannot be empty."
    assert engine.handle(" \t ") == "Input cannot be empty."

    # Session follow-up (Phase 5): CPU then bare bridge → memory
    r_cpu = engine.handle("check cpu")
    assert "CPU" in r_cpu or "cpu" in r_cpu.lower()
    r_mem = engine.handle("also")
    assert "Memory" in r_mem or "memory" in r_mem.lower()
