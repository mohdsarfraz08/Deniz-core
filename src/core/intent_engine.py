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

        # -------------------------------------------------------------------------
        # Phase 9 — File System Tool Handlers
        # Safe operations are registered directly. Destructive operations
        # (delete_file, delete_folder) route through the PendingRiskyClose
        # confirmation gate to satisfy the AI Ethics transparency requirement.
        # -------------------------------------------------------------------------
        self.registry.register_action("create_file", self._handle_create_file)
        self.registry.register_action("read_file", self._handle_read_file)
        self.registry.register_action("write_file", self._handle_write_file)
        self.registry.register_action("append_file", self._handle_append_file)
        self.registry.register_action("delete_file", self._handle_delete_file)
        self.registry.register_action("copy_file", self._handle_copy_file)
        self.registry.register_action("move_file", self._handle_move_file)
        self.registry.register_action("create_folder", self._handle_create_folder)
        self.registry.register_action("delete_folder", self._handle_delete_folder)
        # move_folder: separate telemetry name, shared adapter backend (Q2 decision)
        self.registry.register_action("move_folder", self._handle_move_folder)
        self.registry.register_action("list_directory", self._handle_list_directory)

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

    # -------------------------------------------------------------------------
    # Phase 9 — File System Handlers
    # Each handler extracts path/content from the Intent, calls the executor,
    # and returns result.message (preserving the existing str output contract).
    # Destructive handlers arm self.pending_action and return a confirmation
    # prompt — the AI Ethics transparency gate.
    # -------------------------------------------------------------------------

    def _handle_create_file(self, intent: Intent) -> str:
        if not intent.target:
            return "Please specify a file name. Example: create file notes.txt"
        result = self.system_executor.create_file(intent.target, intent.value or "")
        return result.message

    def _handle_read_file(self, intent: Intent) -> str:
        if not intent.target:
            return "Please specify a file name. Example: read file notes.txt"
        result = self.system_executor.read_file(intent.target)
        return result.message

    def _handle_write_file(self, intent: Intent) -> str:
        if not intent.target:
            return "Please specify a file name. Example: write to notes.txt hello world"
        result = self.system_executor.write_file(intent.target, intent.value or "")
        return result.message

    def _handle_append_file(self, intent: Intent) -> str:
        if not intent.target:
            return "Please specify a file name. Example: append to notes.txt more text"
        result = self.system_executor.append_file(intent.target, intent.value or "")
        return result.message

    def _handle_delete_file(self, intent: Intent) -> str:
        """DESTRUCTIVE — arms the confirmation gate before executing.

        AI Ethics requirement: the model must never silently delete files.
        The user must explicitly confirm with 'yes' before deletion proceeds.
        """
        if not intent.target:
            return "Please specify a file name. Example: delete file notes.txt"
        path = intent.target

        def _do_delete() -> str:
            result = self.system_executor.delete_file(path)
            return result.message

        self.pending_action = _do_delete
        return f"Are you sure you want to permanently delete '{path}'? (yes / no)"

    def _handle_copy_file(self, intent: Intent) -> str:
        if not intent.target:
            return "Please specify source and destination. Example: copy file a.txt b.txt"
        if not intent.value:
            return f"Please specify a destination for '{intent.target}'. Example: copy file {intent.target} copy.txt"
        result = self.system_executor.copy_file(intent.target, intent.value)
        return result.message

    def _handle_move_file(self, intent: Intent) -> str:
        """Logged as 'move_file' in telemetry (Q2: separate intent, shared backend)."""
        if not intent.target:
            return "Please specify source and destination. Example: move file a.txt b.txt"
        if not intent.value:
            return f"Please specify a destination for '{intent.target}'. Example: move file {intent.target} new.txt"
        result = self.system_executor.move_file(intent.target, intent.value)
        return result.message

    def _handle_create_folder(self, intent: Intent) -> str:
        if not intent.target:
            return "Please specify a folder name. Example: create folder reports"
        result = self.system_executor.create_folder(intent.target)
        return result.message

    def _handle_delete_folder(self, intent: Intent) -> str:
        """DESTRUCTIVE — arms the confirmation gate before executing.

        AI Ethics requirement: the model must never silently delete directories.
        """
        if not intent.target:
            return "Please specify a folder name. Example: delete folder old_reports"
        path = intent.target

        def _do_delete_folder() -> str:
            result = self.system_executor.delete_folder(path)
            return result.message

        self.pending_action = _do_delete_folder
        return f"Are you sure you want to permanently delete folder '{path}' and all its contents? (yes / no)"

    def _handle_move_folder(self, intent: Intent) -> str:
        """Logged as 'move_folder' in telemetry (Q2: separate intent, shared backend)."""
        if not intent.target:
            return "Please specify source and destination. Example: move folder reports archive/reports"
        if not intent.value:
            return f"Please specify a destination for '{intent.target}'."
        result = self.system_executor.move_folder(intent.target, intent.value)
        return result.message

    def _handle_list_directory(self, intent: Intent) -> str:
        path = intent.target or "."
        result = self.system_executor.list_directory(path)
        return result.message