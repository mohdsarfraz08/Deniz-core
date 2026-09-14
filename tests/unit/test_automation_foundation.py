import sys
import time
from unittest.mock import MagicMock, patch
import pytest

from automation.errors import (
    UnsupportedPlatformError,
    UnsupportedActionError,
    SessionError,
    BackendError,
)
from automation.backends.base_backend import BaseBackend
from automation.backends.windows_backend import WindowsBackend
from automation.session import AutomationSession
from automation.enums import SessionStatus, ActionStatus, MouseButton
from automation.manager import AutomationManager
from automation.controllers.mouse_controller import BaseMouseController
from automation.controllers.keyboard_controller import BaseKeyboardController
from automation.controllers.window_controller import BaseWindowController


# --- BaseBackend Tests ---


def test_base_backend_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseBackend()  # type: ignore


# --- Session Tests ---


def test_session_lifecycle():
    session = AutomationSession()
    assert session.status == SessionStatus.INACTIVE
    assert session.start_time is not None
    assert session.end_time is None
    assert len(session.history) == 0

    session.start()
    assert session.status == SessionStatus.ACTIVE

    session.close(SessionStatus.COMPLETED)
    assert session.status == SessionStatus.COMPLETED
    assert session.end_time is not None


def test_session_duplicate_start_raises():
    session = AutomationSession()
    session.start()
    with pytest.raises(SessionError, match="already active"):
        session.start()


def test_session_close_inactive_raises():
    session = AutomationSession()
    with pytest.raises(SessionError, match="not active"):
        session.close()


def test_session_close_invalid_status_raises():
    session = AutomationSession()
    session.start()
    with pytest.raises(ValueError, match="Close status must be"):
        session.close("invalid_status")  # type: ignore


def test_session_record_action_not_active_raises():
    session = AutomationSession()
    with pytest.raises(SessionError, match="Session is not active"):
        session.record_action_start("test_action", {})


def test_session_record_action_end_not_active_raises():
    session = AutomationSession()
    with pytest.raises(SessionError, match="Session is not active"):
        session.record_action_end("fake_id", ActionStatus.SUCCESS)


def test_session_record_action_flow():
    session = AutomationSession()
    session.start()

    action_id = session.record_action_start("click", {"x": 100, "y": 200, "button": MouseButton.LEFT})
    assert action_id is not None
    assert len(session.history) == 1

    record = session.history[0]
    assert record.action_id == action_id
    assert record.action_name == "click"
    assert record.parameters == {"x": 100, "y": 200, "button": MouseButton.LEFT}
    assert record.status == ActionStatus.PENDING
    assert record.end_time is None

    time.sleep(0.01)
    session.record_action_end(action_id, ActionStatus.SUCCESS)
    assert record.status == ActionStatus.SUCCESS
    assert record.end_time is not None
    assert record.duration is not None
    assert record.duration > 0


def test_session_record_action_end_invalid_id_raises():
    session = AutomationSession()
    session.start()
    with pytest.raises(SessionError, match="not found in this session"):
        session.record_action_end("non_existent_id", ActionStatus.SUCCESS)


# --- WindowsBackend Tests ---


@pytest.mark.windows_only
def test_windows_backend_support_on_windows():
    with patch("sys.platform", "win32"):
        assert WindowsBackend.is_supported() is True

    with patch("sys.platform", "linux"):
        assert WindowsBackend.is_supported() is False


@pytest.mark.windows_only
@patch("pythoncom.CoInitialize")
def test_windows_backend_initialize_com(mock_co_init):
    backend = WindowsBackend()
    with patch("sys.platform", "win32"):
        backend.initialize()
    assert backend.initialized is True
    assert backend.mouse is not None
    assert backend.keyboard is not None
    assert backend.window is not None
    mock_co_init.assert_called_once()


@pytest.mark.windows_only
def test_windows_backend_initialize_unsupported_raises():
    backend = WindowsBackend()
    with patch("sys.platform", "linux"):
        with pytest.raises(UnsupportedPlatformError, match="only supported on Windows"):
            backend.initialize()


@pytest.mark.windows_only
@patch("pythoncom.CoInitialize", side_effect=Exception("COM Failure"))
def test_windows_backend_initialize_com_error_raises(_mock_co_init):
    backend = WindowsBackend()
    with patch("sys.platform", "win32"):
        with pytest.raises(BackendError, match="COM initialization failed"):
            backend.initialize()


@pytest.mark.windows_only
@patch("pythoncom.CoInitialize")
@patch("pythoncom.CoUninitialize")
def test_windows_backend_shutdown(mock_co_uninit, mock_co_init):
    backend = WindowsBackend()
    with patch("sys.platform", "win32"):
        backend.initialize()
        backend.shutdown()
    assert backend.initialized is False
    mock_co_uninit.assert_called_once()


@pytest.mark.windows_only
@patch("pythoncom.CoInitialize")
def test_windows_backend_execute_uninitialized_raises(mock_co_init):
    backend = WindowsBackend()
    with pytest.raises(BackendError, match="Backend is not initialized"):
        backend.execute_action("ping")


@pytest.mark.windows_only
@patch("pythoncom.CoInitialize")
def test_windows_backend_execute_supported_action(mock_co_init):
    backend = WindowsBackend()
    with patch("sys.platform", "win32"):
        backend.initialize()
    res = backend.execute_action("ping")
    assert res == "pong"


@pytest.mark.windows_only
@patch("pythoncom.CoInitialize")
def test_windows_backend_execute_unsupported_action(mock_co_init):
    backend = WindowsBackend()
    with patch("sys.platform", "win32"):
        backend.initialize()
    with pytest.raises(UnsupportedActionError, match="Action 'invalid_action' is not supported"):
        backend.execute_action("invalid_action")


# --- AutomationManager Tests ---


def test_manager_detect_unsupported_platform_raises():
    with patch("automation.backends.windows_backend.WindowsBackend.is_supported", return_value=False):
        with patch("sys.platform", "unsupported_os"):
            with pytest.raises(UnsupportedPlatformError, match="No supported automation backend"):
                AutomationManager()


def test_manager_initialization_with_custom_backend():
    mock_backend = MagicMock(spec=BaseBackend)
    manager = AutomationManager(backend=mock_backend)
    assert manager.backend == mock_backend


def test_manager_session_lifecycle():
    mock_backend = MagicMock(spec=BaseBackend)
    manager = AutomationManager(backend=mock_backend)

    assert manager.get_active_session() is None

    session = manager.start_session()
    assert session is not None
    assert manager.get_active_session() == session
    mock_backend.initialize.assert_called_once()

    manager.end_session()
    assert manager.get_active_session() is None
    mock_backend.shutdown.assert_called_once()
    assert session.status == SessionStatus.COMPLETED


def test_manager_start_session_already_active_raises():
    mock_backend = MagicMock(spec=BaseBackend)
    manager = AutomationManager(backend=mock_backend)
    manager.start_session()
    with pytest.raises(SessionError, match="session is already active"):
        manager.start_session()


def test_manager_end_session_none_active_raises():
    mock_backend = MagicMock(spec=BaseBackend)
    manager = AutomationManager(backend=mock_backend)
    with pytest.raises(SessionError, match="No active session to end"):
        manager.end_session()


def test_manager_execute_without_session_raises():
    mock_backend = MagicMock(spec=BaseBackend)
    manager = AutomationManager(backend=mock_backend)
    with pytest.raises(SessionError, match="No active session"):
        manager.execute("ping")


def test_manager_execute_success():
    mock_backend = MagicMock(spec=BaseBackend)
    mock_backend.execute_action.return_value = "pong"

    manager = AutomationManager(backend=mock_backend)
    session = manager.start_session()

    result = manager.execute("ping", param1="val1")
    assert result == "pong"
    mock_backend.execute_action.assert_called_once_with("ping", param1="val1")

    assert len(session.history) == 1
    record = session.history[0]
    assert record.action_name == "ping"
    assert record.parameters == {"param1": "val1"}
    assert record.status == ActionStatus.SUCCESS
    assert record.error is None


def test_manager_execute_failure():
    mock_backend = MagicMock(spec=BaseBackend)
    mock_backend.execute_action.side_effect = BackendError("Mock failure")

    manager = AutomationManager(backend=mock_backend)
    session = manager.start_session()

    with pytest.raises(BackendError, match="Mock failure"):
        manager.execute("fail_action")

    assert len(session.history) == 1
    record = session.history[0]
    assert record.action_name == "fail_action"
    assert record.status == ActionStatus.FAILURE
    assert "Mock failure" in str(record.error)


# --- Refactoring Enhancement Tests (Enums, Registry, Context Manager, Controller Delegation) ---


def test_enums_correctness():
    assert SessionStatus.ACTIVE == "active"
    assert SessionStatus.COMPLETED == "completed"
    assert ActionStatus.SUCCESS == "success"
    assert ActionStatus.FAILURE == "failure"


def test_manager_context_manager_success():
    mock_backend = MagicMock(spec=BaseBackend)
    mock_backend.execute_action.return_value = "pong"

    with AutomationManager(backend=mock_backend) as manager:
        active_session = manager.get_active_session()
        assert active_session is not None
        assert active_session.status == SessionStatus.ACTIVE
        mock_backend.initialize.assert_called_once()

        res = manager.execute("ping")
        assert res == "pong"

    mock_backend.shutdown.assert_called_once()
    assert active_session.status == SessionStatus.COMPLETED


def test_manager_context_manager_failure():
    mock_backend = MagicMock(spec=BaseBackend)

    with pytest.raises(ValueError, match="Inside block failure"):
        with AutomationManager(backend=mock_backend) as manager:
            active_session = manager.get_active_session()
            assert active_session is not None
            raise ValueError("Inside block failure")

    mock_backend.shutdown.assert_called_once()
    assert active_session.status == SessionStatus.FAILED


def test_manager_controller_delegation_guards():
    mock_backend = MagicMock(spec=BaseBackend)
    mock_backend.mouse = MagicMock(spec=BaseMouseController)
    mock_backend.keyboard = MagicMock(spec=BaseKeyboardController)
    mock_backend.window = MagicMock(spec=BaseWindowController)

    manager = AutomationManager(backend=mock_backend)

    # Controller access raises error outside active session
    with pytest.raises(SessionError, match="Cannot access mouse controller"):
        _ = manager.mouse

    with pytest.raises(SessionError, match="Cannot access keyboard controller"):
        _ = manager.keyboard

    with pytest.raises(SessionError, match="Cannot access window controller"):
        _ = manager.window

    # Inside session they are accessible and delegated
    with manager:
        assert manager.mouse == mock_backend.mouse
        assert manager.keyboard == mock_backend.keyboard
        assert manager.window == mock_backend.window
