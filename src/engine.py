from core.parser import CommandParser
from core.intent_engine import IntentEngine
from core.action_registry import ActionRegistry
from core.monitoring.resource_monitor import ResourceMonitor
from core.security import PermissionChecker, validate_input
from core.session_context import SessionManager
from core.session.app_registry import SessionRegistry
from core.system_executor import SystemExecutor
from adapters.factory import create_system_executor
from utils.logger import setup_logger

logger = setup_logger("AssistantEngine")

# User-facing: parser miss vs policy vs roadmap (not security-style denial).
MSG_UNKNOWN_COMMAND = "I didn't understand that command."
MSG_NOT_IMPLEMENTED = "That feature is not implemented yet."


class AssistantEngine:
    def __init__(
        self,
        system_executor: SystemExecutor | None = None,
        permission_checker: PermissionChecker | None = None,
        session_manager: SessionManager | None = None,
        session_registry: SessionRegistry | None = None,
    ):
        try:
            self.session_registry = (
                session_registry if session_registry is not None else SessionRegistry()
            )
            self.executor = (
                system_executor
                if system_executor is not None
                else create_system_executor(self.session_registry)
            )

            self.intent_engine = IntentEngine(system_executor=self.executor)

            self.parser = CommandParser()
            self.action_registry = ActionRegistry()
            self.monitor = ResourceMonitor()
            self.permissions = (
                permission_checker if permission_checker is not None else PermissionChecker()
            )
            self.session = session_manager if session_manager is not None else SessionManager()

            logger.info("Engine components synchronized and initialized.")
        except Exception as e:
            logger.error(f"Dependency Injection Failed: {e}")
            raise

    def handle(self, text: str) -> str:
        """
        Main public interface of the assistant.
        Orchestrates full pipeline:
        validate → parse → session enrich → permission → route → execute
        """

        try:
            ok, err = validate_input(text)
            if not ok:
                return err

            resolver = getattr(self.executor, "try_resolve_pending_risky_close", None)
            if callable(resolver):
                resolved_early = resolver(text)
                if resolved_early is not None:
                    return resolved_early

            resolver_disambig = getattr(
                self.executor, "try_resolve_pending_terminal_disambiguation", None
            )
            if callable(resolver_disambig):
                resolved_disambig = resolver_disambig(text)
                if resolved_disambig is not None:
                    return resolved_disambig

            intent = self.parser.parse(text)
            intent = self.session.enrich(text, intent)

            if intent.intent == "unknown":
                logger.info("Unrecognized input (no matching intent); text=%r", text[:200])
                return MSG_UNKNOWN_COMMAND

            if intent.intent == "not_implemented":
                logger.info("Unsupported feature request; text=%r", text[:200])
                return MSG_NOT_IMPLEMENTED

            if not self.permissions.is_allowed(intent.intent):
                logger.warning("Access Denied: intent '%s'", intent.intent)
                return "Access denied for this action."

            self.monitor.start_intent_tracking()

            response = self.intent_engine.execute(intent)

            stats = self.monitor.stop_intent_tracking()
            logger.info(
                f"Intent '{intent.intent}' executed in {stats['execution_time']:.4f}s "
                f"with CPU usage delta: {stats['cpu_usage']}%"
            )

            self.session.record_successful_turn(intent, response)

            return response

        except Exception as e:
            logger.exception(f"Error during request handling: {e}")
            return "Internal processing error."
