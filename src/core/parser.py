from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class Intent:
    intent: str
    target: Optional[str] = None
    value: Optional[str] = None


class CommandParser:

    OPEN_KEYWORDS = ["open", "launch", "start"]
    CLOSE_KEYWORDS = ["close", "quit", "exit"]
    CPU_KEYWORDS = ["cpu", "processor"]
    MEMORY_KEYWORDS = ["memory", "ram"]
    TIME_KEYWORDS = ["time", "clock"]
    GREET_KEYWORDS = ["hello", "hi"]

    # Conjunctions that signal a compound command attempt.
    COMPOUND_CONJUNCTIONS = (" and ", " then ", " also ")

    _NOT_IMPLEMENTED_EXACT = frozenset({"remind me", "set timer", "set alarm"})
    _NOT_IMPLEMENTED_PREFIXES = (
        "remind me ",
        "translate ",
        "send email",
        "schedule ",
        "set timer ",
        "set alarm ",
    )

    def parse(self, text: str) -> Intent:
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)

        # --- Compound command guard (must be first, before any intent routing) ---
        if self._is_compound_command(text):
            return Intent(intent="compound_command")

        # --- Greet ---
        if text in self.GREET_KEYWORDS:
            return Intent(intent="greet")

        # --- Confirmation replies (must match before unknown / broad keyword checks) ---
        if text == "yes":
            return Intent(intent="confirm_yes")
        if text == "no":
            return Intent(intent="confirm_no")

        # --- Supported someday (clear capability gap vs random gibberish) ---
        if self._matches_not_implemented(text):
            return Intent(intent="not_implemented")

        # --- Open App ---
        for keyword in self.OPEN_KEYWORDS:
            if text.startswith(keyword + " "):
                target = text.replace(keyword, "", 1).strip()
                # Disambiguate "open file" intent vs "open app" intent.
                # "open file" / "show file" is handled below as read_file.
                if not any(text.startswith(kw + " file") for kw in self.OPEN_KEYWORDS):
                    return Intent(intent="open_app", target=target)

        # --- Close App ---
        for keyword in self.CLOSE_KEYWORDS:
            if text.startswith(keyword + " "):
                target = text.replace(keyword, "", 1).strip()
                return Intent(intent="close_app", target=target)

        # --- CPU ---
        if any(word in text for word in self.CPU_KEYWORDS):
            return Intent(intent="get_cpu_usage")

        # --- Memory ---
        if any(word in text for word in self.MEMORY_KEYWORDS):
            return Intent(intent="get_memory_usage")

        # --- Time ---
        if any(word in text for word in self.TIME_KEYWORDS):
            return Intent(intent="get_time")

        # --- Dangerous system commands (after open/close so "open shutdown.exe" stays open_app) ---
        if self._matches_dangerous_system_command(text):
            return Intent(intent="dangerous_system")

        # -------------------------------------------------------------------------
        # Phase 9 — File System Intent Routing
        #
        # Extraction strategy (Q1 decision — Option A: Positional):
        #   The first token after the verb/keyword group is treated as the file or
        #   folder path. All remaining tokens are treated as content (value field).
        #   This approach is intentional for the v1 deterministic parser and is
        #   documented explicitly here so the Phase 10 AI team knows the exact
        #   contract to replace with natural-language extraction.
        #
        #   Format:  <verb phrase> <path> [content...]
        #   Example: "write to notes.txt hello world"
        #            → intent="write_file", target="notes.txt", value="hello world"
        #
        # NOTE FOR PHASE 10 AI TEAM:
        #   Replace _extract_path_and_value() with an LLM-based entity extractor
        #   that handles quoted strings, relative paths, and multi-word paths
        #   (e.g. "my documents/report"). The positional split below will break
        #   on paths containing spaces — this is the known limitation of v1.
        # -------------------------------------------------------------------------

        # --- create_file ---
        for phrase in ("create file ", "make file ", "new file "):
            if text.startswith(phrase):
                path, _, content = text[len(phrase):].partition(" ")
                return Intent(intent="create_file", target=path.strip(), value=content.strip() or None)

        # --- read_file ---
        for phrase in ("read file ", "show file ", "open file "):
            if text.startswith(phrase):
                path = text[len(phrase):].strip()
                return Intent(intent="read_file", target=path)

        # --- write_file ---
        for phrase in ("write to ", "write file "):
            if text.startswith(phrase):
                path, _, content = text[len(phrase):].partition(" ")
                return Intent(intent="write_file", target=path.strip(), value=content.strip() or None)

        # --- append_file ---
        for phrase in ("append to ", "add to file "):
            if text.startswith(phrase):
                path, _, content = text[len(phrase):].partition(" ")
                return Intent(intent="append_file", target=path.strip(), value=content.strip() or None)

        # --- delete_file ---
        for phrase in ("delete file ", "remove file "):
            if text.startswith(phrase):
                path = text[len(phrase):].strip()
                return Intent(intent="delete_file", target=path)

        # --- copy_file ---
        if text.startswith("copy file "):
            rest = text[len("copy file "):].strip()
            # Positional: first token = src, second token = dst
            parts = rest.split(" ", 1)
            src = parts[0] if parts else ""
            dst = parts[1] if len(parts) > 1 else ""
            return Intent(intent="copy_file", target=src, value=dst or None)

        # --- move_file ---
        if text.startswith("move file "):
            rest = text[len("move file "):].strip()
            parts = rest.split(" ", 1)
            src = parts[0] if parts else ""
            dst = parts[1] if len(parts) > 1 else ""
            return Intent(intent="move_file", target=src, value=dst or None)

        # --- create_folder ---
        for phrase in ("create folder ", "make folder ", "new folder ", "mkdir "):
            if text.startswith(phrase):
                path = text[len(phrase):].strip()
                return Intent(intent="create_folder", target=path)

        # --- delete_folder ---
        for phrase in ("delete folder ", "remove folder "):
            if text.startswith(phrase):
                path = text[len(phrase):].strip()
                return Intent(intent="delete_folder", target=path)

        # --- move_folder (Q2: separate intent name, shared adapter backend) ---
        if text.startswith("move folder "):
            rest = text[len("move folder "):].strip()
            parts = rest.split(" ", 1)
            src = parts[0] if parts else ""
            dst = parts[1] if len(parts) > 1 else ""
            return Intent(intent="move_folder", target=src, value=dst or None)

        # --- list_directory ---
        for phrase in ("list folder ", "list files ", "ls ", "dir "):
            if text.startswith(phrase):
                path = text[len(phrase):].strip() or "."
                return Intent(intent="list_directory", target=path)
        # Bare "ls" / "dir" with no argument defaults to workspace root
        if text in ("ls", "dir", "list files", "list folder"):
            return Intent(intent="list_directory", target=".")

        return Intent(intent="unknown")

    @classmethod
    def _is_compound_command(cls, text: str) -> bool:
        """Return True when both sides of a conjunction contain a distinct command.

        A segment is considered a command only when it contains:
          - A verb keyword (open/close/quit/launch/start/exit), OR
          - A multi-word metric phrase (e.g. 'check cpu', 'show time', 'check memory').

        This avoids false positives on natural metric phrases like
        ``check cpu and memory`` or ``check cpu and time`` where the right
        side is a bare noun, not an independent command.
        """
        _VERB_KEYWORDS = cls.OPEN_KEYWORDS + cls.CLOSE_KEYWORDS
        _METRIC_PHRASES = (
            "check cpu", "check processor",
            "check memory", "check ram",
            "check time", "show time", "show clock",
            "get cpu", "get memory", "get time",
        )

        def _is_command_segment(segment: str) -> bool:
            # Has an action verb
            if any(segment.startswith(v) or f" {v} " in segment or segment.endswith(v)
                   for v in _VERB_KEYWORDS):
                return True
            # Has a recognisable multi-word metric phrase
            if any(phrase in segment for phrase in _METRIC_PHRASES):
                return True
            return False

        for conj in cls.COMPOUND_CONJUNCTIONS:
            if conj in text:
                left, _, right = text.partition(conj)
                if _is_command_segment(left.strip()) and _is_command_segment(right.strip()):
                    return True
        return False

    @classmethod
    def _matches_not_implemented(cls, text: str) -> bool:
        if text in cls._NOT_IMPLEMENTED_EXACT:
            return True
        return any(text.startswith(p) for p in cls._NOT_IMPLEMENTED_PREFIXES)

    @staticmethod
    def _matches_dangerous_system_command(text: str) -> bool:
        """Shell/OS destructive verbs — matched before generic unknown."""
        if re.search(r"\bshutdown\b", text):
            return True
        if re.search(r"\b(poweroff|halt)\b", text):
            return True
        if re.search(r"\b(reboot|restart)\b", text) and re.search(
            r"\b(system|computer|pc|machine|windows)\b", text
        ):
            return True
        if re.search(r"\bformat\b", text) and re.search(r"\bc:", text):
            return True
        if re.search(r"\b(wipe|erase)\b", text) and re.search(
            r"\b(disk|drive|system|windows)\b", text
        ):
            return True
        return False