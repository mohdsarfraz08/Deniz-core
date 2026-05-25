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


def test_terminate_pid_scoped_no_such_process_on_lookup():
    with patch(
        "core.security.scoped_terminate.psutil.Process",
        side_effect=psutil.NoSuchProcess(1),
    ):
        assert terminate_pid_scoped(999) is None


def test_terminate_pid_scoped_no_such_process_after_terminate():
    proc = MagicMock()
    proc.terminate.side_effect = psutil.NoSuchProcess(1)
    with patch("core.security.scoped_terminate.psutil.Process", return_value=proc):
        assert terminate_pid_scoped(12345) is None


def test_terminate_pid_scoped_access_denied_on_terminate():
    proc = MagicMock()
    proc.terminate.side_effect = psutil.AccessDenied("denied")
    with patch("core.security.scoped_terminate.psutil.Process", return_value=proc):
        out = terminate_pid_scoped(12345)
    assert out is not None
    assert "access denied" in out.lower()


def test_terminate_pid_scoped_double_timeout_returns_message():
    proc = MagicMock()
    proc.wait = MagicMock(side_effect=[psutil.TimeoutExpired(30), psutil.TimeoutExpired(8)])
    with patch("core.security.scoped_terminate.psutil.Process", return_value=proc):
        out = terminate_pid_scoped(12345)
    assert out is not None
    assert "couldn't confirm" in out.lower()
    proc.kill.assert_called_once()


def test_terminate_pid_scoped_access_denied_on_kill():
    proc = MagicMock()
    proc.wait = MagicMock(side_effect=[psutil.TimeoutExpired(30)])
    proc.kill.side_effect = psutil.AccessDenied("denied")
    with patch("core.security.scoped_terminate.psutil.Process", return_value=proc):
        out = terminate_pid_scoped(12345)
    assert out is not None
    assert "access denied" in out.lower()


def test_terminate_pid_scoped_no_such_process_during_wait():
    proc = MagicMock()
    proc.wait.side_effect = psutil.NoSuchProcess(1)
    with patch("core.security.scoped_terminate.psutil.Process", return_value=proc):
        assert terminate_pid_scoped(12345) is None


def test_terminate_pid_scoped_no_such_process_during_kill():
    proc = MagicMock()
    proc.wait = MagicMock(side_effect=[psutil.TimeoutExpired(30)])
    proc.kill.side_effect = psutil.NoSuchProcess(1)
    with patch("core.security.scoped_terminate.psutil.Process", return_value=proc):
        assert terminate_pid_scoped(12345) is None


def test_terminate_pid_scoped_no_such_process_after_kill_wait():
    proc = MagicMock()
    proc.wait = MagicMock(
        side_effect=[psutil.TimeoutExpired(30), psutil.NoSuchProcess(1)]
    )
    with patch("core.security.scoped_terminate.psutil.Process", return_value=proc):
        assert terminate_pid_scoped(12345) is None
