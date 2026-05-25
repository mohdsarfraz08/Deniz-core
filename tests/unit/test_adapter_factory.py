"""Adapter factory platform selection."""

import sys
from unittest.mock import patch

import pytest

from adapters.factory import create_system_executor


def test_factory_returns_windows_adapter_on_win32():
    with patch.object(sys, "platform", "win32"):
        adapter = create_system_executor()
    assert adapter.__class__.__name__ == "WindowsAdapter"


def test_factory_returns_linux_adapter_on_linux():
    with patch.object(sys, "platform", "linux"):
        adapter = create_system_executor()
    assert adapter.__class__.__name__ == "LinuxAdapter"


def test_factory_raises_on_unsupported_platform():
    with patch.object(sys, "platform", "darwin"):
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            create_system_executor()
