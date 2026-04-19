from core.parser import CommandParser
from core.intent_engine import IntentEngine
from core.action_registry import ActionRegistry
from core.monitoring.resource_monitor import ResourceMonitor
from core.security import PermissionChecker, validate_input
from core.system_executor import SystemExecutor
from adapters.windows_adapter import WindowsAdapter
from utils.logger import setup_logger

logger = setup_logger("AssistantEngine")


class AssistantEngine:
    def __init__(
        self,
        system_executor: SystemExecutor | None = None,
        permission_checker: PermissionChecker | None = None,
    ):
        try:
            self.executor = system_executor if system_executor is not None else WindowsAdapter()

            self.intent_engine = IntentEngine(system_executor=self.executor)

            self.parser = CommandParser()
            self.action_registry = ActionRegistry()
            self.monitor = ResourceMonitor()
            self.permissions = (
                permission_checker if permission_checker is not None else PermissionChecker()
            )

            logger.info("Engine components synchronized and initialized.")
        except Exception as e:
            logger.error(f"Dependency Injection Failed: {e}")
            raise

    def handle(self, text: str) -> str:
        """
        Main public interface of the assistant.
        Orchestrates full pipeline:
        validate → parse → permission → route → execute
        """

        try:
            ok, err = validate_input(text)
            if not ok:
                return err

            intent = self.parser.parse(text)

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

            return response

        except Exception as e:
            logger.exception(f"Error during request handling: {e}")
            return "Internal processing error."
