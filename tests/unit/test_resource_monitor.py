"""ResourceMonitor behavior with deterministic mocks (avoids long psutil intervals in assertions)."""

from unittest.mock import MagicMock, patch

import pytest

from core.monitoring.resource_monitor import ResourceMonitor


def test_get_system_stats_returns_keys_and_values() -> None:
    with patch("core.monitoring.resource_monitor.psutil") as psutil_mock:
        psutil_mock.cpu_percent.return_value = 12.5
        vm = MagicMock()
        vm.percent = 34.0
        psutil_mock.virtual_memory.return_value = vm
        m = ResourceMonitor()
        stats = m.get_system_stats()
    assert stats["cpu_usage"] == 12.5
    assert stats["memory_usage"] == 34.0


def test_intent_tracking_returns_elapsed_and_cpu_delta() -> None:
    with patch("core.monitoring.resource_monitor.psutil") as psutil_mock:
        psutil_mock.cpu_percent.return_value = 3.0
        m = ResourceMonitor()
        with patch("core.monitoring.resource_monitor.time") as time_mock:
            time_mock.time.side_effect = [100.0, 100.05]
            m.start_intent_tracking()
            out = m.stop_intent_tracking()
    assert out["execution_time"] == pytest.approx(0.05)
    assert out["cpu_usage"] == 3.0
    psutil_mock.cpu_percent.assert_called()
