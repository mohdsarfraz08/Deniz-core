# core/intent_engine.py

from core.intent_resolution import (
    format_close_file_explorer_message,
    is_file_explorer_window_target,
)
from core.parser import Intent
from core.action_registry import ActionRegistry
from core.system_executor import SystemExecutor

class IntentEngine:
    """
    Receives structured Intent objects and routes them
    to the appropriate execution handlers.

    This class contains NO parsing logic.
    """

    def __init__(self, system_executor: SystemExecutor):
        """
        Dependency injection of executor layer.
        Keeps engine platform-agnostic.
        """
        self.pending_action = None
        self.system_executor = system_executor
        self.registry = ActionRegistry()
        
        # Register core actions
        self.registry.register_action("greet", self._handle_greet)
        self.registry.register_action("open_app", self._handle_open_app)
        self.registry.register_action("close_app", self._handle_close_app)
        
        # Register system awareness actions
        self.registry.register_action("get_time", self._handle_get_time)
        self.registry.register_action("get_cpu_usage", self._handle_cpu)
        self.registry.register_action("get_memory_usage", self._handle_memory)
        # Roadmap aliases for the same capabilities
        self.registry.register_action("show_time", self._handle_get_time)
        self.registry.register_action("check_cpu", self._handle_cpu)
        self.registry.register_action("check_memory", self._handle_memory)

    def execute(self, intent: Intent) -> str:

    #  If waiting for confirmation
        if self.pending_action:
            if intent.intent == "confirm_yes":
                action = self.pending_action
                self.pending_action = None
                return action()

            elif intent.intent == "confirm_no":
                self.pending_action = None
                return "Action cancelled."

        if intent.intent in ("confirm_yes", "confirm_no"):
            return "Nothing to confirm."

        handler = self.registry.get_action(intent.intent)

        if handler:
            return handler(intent)

        return "Unknown intent"

    # ---------------------------
    # Intent Handlers
    # ---------------------------

    def _handle_greet(self, intent: Intent = None) -> str:
        return "Hello. System operational."

    def _handle_open_app(self, intent: Intent) -> str:
        if not intent.target:
            return "No application specified."

        return self.system_executor.open_app(intent.target)

    def _handle_close_app(self, intent):
        if not intent.target:
            return "No application specified."

        if is_file_explorer_window_target(intent.target):
            result = self.system_executor.close_file_explorer_windows()
            return format_close_file_explorer_message(result)

        return self.system_executor.close_app(intent.target)

    def _handle_get_time(self, intent: Intent = None) -> str:
        return self.system_executor.get_time()

    def _handle_cpu(self, intent: Intent = None) -> str:
        return self.system_executor.get_cpu_usage()

    def _handle_memory(self, intent: Intent = None) -> str:
        return self.system_executor.get_memory_usage()