import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from automation.enums import SessionStatus, ActionStatus
from automation.errors import SessionError


@dataclass
class AutomationActionRecord:
    action_id: str
    action_name: str
    parameters: Dict[str, Any]
    status: ActionStatus  # Use ActionStatus Enum
    error: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None


class AutomationSession:
    """
    Manages state and action history for a single automation session.
    """

    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id: str = session_id or str(uuid.uuid4())
        self.start_time: datetime = datetime.now()
        self.end_time: Optional[datetime] = None
        self.status: SessionStatus = SessionStatus.INACTIVE
        self.history: List[AutomationActionRecord] = []
        self._action_lookup: Dict[str, AutomationActionRecord] = {}

    def start(self) -> None:
        if self.status == SessionStatus.ACTIVE:
            raise SessionError(f"Session '{self.session_id}' is already active.")
        self.status = SessionStatus.ACTIVE

    def close(self, status: SessionStatus = SessionStatus.COMPLETED) -> None:
        if self.status != SessionStatus.ACTIVE:
            raise SessionError("Cannot close a session that is not active.")
        if status not in (SessionStatus.COMPLETED, SessionStatus.FAILED):
            raise ValueError(f"Close status must be {SessionStatus.COMPLETED} or {SessionStatus.FAILED}.")
        self.status = status
        self.end_time = datetime.now()

    def record_action_start(self, action_name: str, parameters: Dict[str, Any]) -> str:
        if self.status != SessionStatus.ACTIVE:
            raise SessionError("Cannot record action: Session is not active.")
        action_id = str(uuid.uuid4())
        record = AutomationActionRecord(
            action_id=action_id,
            action_name=action_name,
            parameters=parameters,
            status=ActionStatus.PENDING
        )
        self.history.append(record)
        self._action_lookup[action_id] = record
        return action_id

    def record_action_end(self, action_id: str, status: ActionStatus, error: Optional[str] = None) -> None:
        if self.status != SessionStatus.ACTIVE:
            raise SessionError("Cannot record action end: Session is not active.")
        record = self._action_lookup.get(action_id)
        if not record:
            raise SessionError(f"Action ID '{action_id}' not found in this session.")

        record.status = status
        record.error = error
        record.end_time = time.time()
        record.duration = record.end_time - record.start_time
