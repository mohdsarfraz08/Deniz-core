from core.parser import Parser
from core.intent_engine import IntentEngine
from core.action_registry import ActionRegistry
from core.monitoring.resource_monitor import ResourceMonitor

class AssistantEngine:
    def __init__(self):
        self.parser = Parser()
        self.intent_engine = IntentEngine()
        self.action_registry = ActionRegistry()
        self.monitor = ResourceMonitor()

    def handle(self, text: str) -> str:
        normalized = self.parser.normalize(text)
        intent = self.intent_engine.detect(normalized)
        action = self.action_registry.get_action(intent)

        result = action()

        self.monitor.log_usage(intent)

        return result