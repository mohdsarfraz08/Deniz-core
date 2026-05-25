"""Linux adapter unit tests (mocked subprocess/psutil; runs on any OS)."""

from unittest.mock import MagicMock, patch

import psutil

from adapters.linux_adapter import LinuxAdapter


def test_get_status_and_execute_command():
    adapter = LinuxAdapter()
    assert adapter.get_status() == "Linux System Active"
    assert "Linux" in adapter.execute_command("ls")


@patch("adapters.linux_adapter.psutil.cpu_percent", return_value=12.5)
def test_get_cpu_usage(mock_cpu):
    assert "12.5" in LinuxAdapter().get_cpu_usage()
    mock_cpu.assert_called_once()


@patch("adapters.linux_adapter.psutil.virtual_memory")
def test_get_memory_usage(mock_vm):
    mock_vm.return_value = MagicMock(percent=55.0)
    assert "55.0" in LinuxAdapter().get_memory_usage()


def test_get_time_format():
    out = LinuxAdapter().get_time()
    assert out.startswith("Current time is ")


@patch("adapters.linux_adapter.subprocess.Popen")
@patch("adapters.linux_adapter.shutil.which")
def test_open_app_uses_which(mock_which, mock_popen):
    mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name == "gedit" else None
    out = LinuxAdapter().open_app("gedit")
    assert out == "gedit opened."
    mock_popen.assert_called_once()


@patch("adapters.linux_adapter.subprocess.Popen")
@patch("adapters.linux_adapter.shutil.which")
def test_open_app_falls_back_to_xdg_open(mock_which, mock_popen):
    mock_which.side_effect = lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None
    out = LinuxAdapter().open_app("myfile.pdf")
    assert out == "myfile.pdf opened."


@patch("adapters.linux_adapter.shutil.which", return_value=None)
def test_open_app_not_found(mock_which):
    out = LinuxAdapter().open_app("missing-app-xyz")
    assert "not found" in out.lower()


def test_close_app_blocks_critical():
    out = LinuxAdapter().close_app("systemd")
    assert "Blocked" in out


def test_close_app_blocks_mass_kill_shell():
    out = LinuxAdapter().close_app("powershell")
    assert "Can't close every running instance" in out


@patch("adapters.linux_adapter.psutil.process_iter")
def test_close_app_terminates_matching_process(mock_iter):
    proc = MagicMock()
    proc.info = {"pid": 100, "name": "gedit"}
    mock_iter.return_value = [proc]
    out = LinuxAdapter().close_app("gedit")
    assert "closed successfully" in out
    proc.terminate.assert_called_once()


@patch("adapters.linux_adapter.psutil.process_iter", return_value=[])
def test_close_app_not_running(_mock_iter):
    assert "not running" in LinuxAdapter().close_app("nobody-here").lower()


@patch("adapters.linux_adapter.psutil.process_iter")
def test_close_file_explorer_windows_counts_managers(mock_iter):
    nautilus = MagicMock()
    nautilus.info = {"pid": 1, "name": "nautilus"}
    other = MagicMock()
    other.info = {"pid": 2, "name": "bash"}
    mock_iter.return_value = [nautilus, other]
    result = LinuxAdapter().close_file_explorer_windows()
    assert result["status"] == "success"
    assert result["count"] == 1
    nautilus.terminate.assert_called_once()


@patch("adapters.linux_adapter.psutil.process_iter")
def test_close_app_handles_access_denied(mock_iter):
    proc = MagicMock()
    proc.info = {"pid": 1, "name": "gedit"}
    proc.terminate.side_effect = psutil.AccessDenied("nope")
    mock_iter.return_value = [proc]
    assert "not running" in LinuxAdapter().close_app("gedit").lower()
