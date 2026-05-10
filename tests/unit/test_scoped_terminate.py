"""Verified termination helper (wait + kill fallback)."""

from unittest.mock import MagicMock, patch

import psutil

from core.security.scoped_terminate import terminate_pid_scoped


def test_terminate_pid_scoped_success_after_wait():
    proc = MagicMock()
    proc.wait = MagicMock(return_value=0)
    with patch("core.security.scoped_terminate.psutil.Process", return_value=proc):
        assert terminate_pid_scoped(12345) is None
    proc.terminate.assert_called_once()
    proc.wait.assert_called_once()


def test_terminate_pid_scoped_escalates_on_timeout():
    proc = MagicMock()
    proc.wait = MagicMock(side_effect=[psutil.TimeoutExpired(30), None])
    with patch("core.security.scoped_terminate.psutil.Process", return_value=proc):
        assert terminate_pid_scoped(12345) is None
    proc.kill.assert_called_once()
