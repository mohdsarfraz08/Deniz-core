from core.parser import CommandParser
from core.intent_engine import IntentEngine
from core.action_registry import ActionRegistry
from core.monitoring.resource_monitor import ResourceMonitor
from adapters.windows_adapter import WindowsAdapter # Import the executor
from utils.logger import setup_logger

logger = setup_logger("AssistantEngine")

class AssistantEngine:
    def __init__(self):
        try:
            # 1. Initialize the Hardware/OS Adapter first
            self.executor = WindowsAdapter()
            
            # 2. Inject the executor into the IntentEngine as required
            self.intent_engine = IntentEngine(system_executor=self.executor)
            
            # 3. Initialize remaining components
            self.parser = CommandParser()
            self.action_registry = ActionRegistry()
            self.monitor = ResourceMonitor()
            
            logger.info("Engine components synchronized and initialized.")
        except Exception as e:
            logger.error(f"Dependency Injection Failed: {e}")
            raise # Re-raise to let Main.py handle the critical failure

    def handle(self, text: str) -> str:
        """
        Main public interface of the assistant.
        Orchestrates full pipeline:
        parse → route → execute
        """

        try:
            intent = self.parser.parse(text)

        # If you're using ActionRegistry later,
        # this is where it could integrate.
            response = self.intent_engine.execute(intent)

            return response

        except Exception as e:
            logger.exception(f"Error during request handling: {e}")
            return "Internal processing error."