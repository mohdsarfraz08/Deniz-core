"""Integration smoke test on Linux using the real LinuxAdapter."""

import sys

import pytest

from adapters.linux_adapter import LinuxAdapter
from engine import AssistantEngine


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux adapter integration")
def test_linux_engine_flow():
    engine = AssistantEngine(system_executor=LinuxAdapter())

    response = engine.handle("hello")
    assert "System operational" in response or "Hello" in response

    response = engine.handle("open notepad; calc")
    assert "disallowed characters" in response.lower()

    response = engine.handle("shutdown system")
    assert "denied" in response.lower()

    assert engine.handle("") == "Input cannot be empty."

    r_cpu = engine.handle("check cpu")
    assert "CPU" in r_cpu or "cpu" in r_cpu.lower()
    r_mem = engine.handle("also")
    assert "Memory" in r_mem or "memory" in r_mem.lower()
