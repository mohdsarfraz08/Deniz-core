# core/intent_engine.py

from core.parser import Intent


class IntentEngine:
    """
    Receives structured Intent objects and routes them
    to the appropriate execution handlers.

    This class contains NO parsing logic.
    """

    def __init__(self, system_executor):
        """
        Dependency injection of executor layer.
        Keeps engine platform-agnostic.
        """
        self.system_executor = system_executor

    def execute(self, intent: Intent) -> str:
        """
        Main routing function.
        """

        if intent.intent == "greet":
            return self._handle_greet()

        elif intent.intent == "open_app":
            return self._handle_open_app(intent)

        elif intent.intent == "close_app":
            return self._handle_close_app(intent)

        elif intent.intent == "get_time":
            return self._handle_get_time()

        elif intent.intent == "unknown":
            return "Sorry, I didn't understand that."

        else:
            return "Intent not supported."

    # ---------------------------
    # Intent Handlers
    # ---------------------------

    def _handle_greet(self) -> str:
        return "Hello. System operational."

    def _handle_open_app(self, intent: Intent) -> str:
        if not intent.target:
            return "No application specified."

        return self.system_executor.open_app(intent.target)

    def _handle_close_app(self, intent: Intent) -> str:
        if not intent.target:
            return "No application specified."

        return self.system_executor.close_app(intent.target)

    def _handle_get_time(self) -> str:
        return self.system_executor.get_time()