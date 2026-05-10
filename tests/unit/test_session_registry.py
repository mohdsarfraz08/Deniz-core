"""Session registry for assistant-opened terminals."""

from core.session.app_registry import SessionRegistry


def test_register_and_get_last_terminal(monkeypatch):
    monkeypatch.setattr("core.session.app_registry.psutil.pid_exists", lambda pid: True)
    r = SessionRegistry()
    r.register_app(
        category="terminal",
        pid=100,
        process_name="WindowsTerminal.exe",
        launch_method="wt.exe",
        launch_canonical="terminal",
    )
    last = r.get_last_app("terminal")
    assert last is not None
    assert last.pid == 100
    assert last.launch_canonical == "terminal"


def test_cleanup_dead_removes_stale_pid(monkeypatch):
    r = SessionRegistry()
    r.register_app(
        category="terminal",
        pid=99999,
        process_name="x.exe",
        launch_method="test",
        launch_canonical="terminal",
    )
    monkeypatch.setattr("core.session.app_registry.psutil.pid_exists", lambda pid: False)
    r.cleanup_dead_processes("terminal")
    assert r.get_last_app("terminal") is None


def test_pop_close_candidate_returns_most_recent_terminal(monkeypatch):
    r = SessionRegistry()
    r.register_app(
        category="terminal",
        pid=1,
        process_name="a",
        launch_method="t",
        launch_canonical="terminal",
    )
    r.register_app(
        category="terminal",
        pid=2,
        process_name="b",
        launch_method="t",
        launch_canonical="powershell",
    )
    monkeypatch.setattr("core.session.app_registry.psutil.pid_exists", lambda pid: True)
    e = r.pop_close_candidate("terminal")
    assert e is not None and e.pid == 2


def test_pop_powershell_prefers_matching_canonical(monkeypatch):
    r = SessionRegistry()
    r.register_app(
        category="terminal",
        pid=10,
        process_name="wt",
        launch_method="wt",
        launch_canonical="terminal",
    )
    r.register_app(
        category="terminal",
        pid=11,
        process_name="powershell",
        launch_method="powershell.exe",
        launch_canonical="powershell",
    )
    monkeypatch.setattr("core.session.app_registry.psutil.pid_exists", lambda pid: True)
    e = r.pop_close_candidate("powershell")
    assert e is not None and e.pid == 11


def test_remove_app():
    r = SessionRegistry()
    r.register_app(
        category="terminal",
        pid=5,
        process_name="x",
        launch_method="m",
        launch_canonical="terminal",
    )
    assert r.remove_app("terminal", 5) is True
    assert r.remove_app("terminal", 5) is False
