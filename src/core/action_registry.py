class ActionRegistry:
    def __init__(self):
        self._registry = {}

    def register_action(self, intent_name, func):
        self._registry[intent_name] = func

    def get_action(self, intent_name):
        return self._registry.get(intent_name)