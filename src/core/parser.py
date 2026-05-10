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

        # --- Dangerous system commands (after open/close so \"open shutdown.exe\" stays open_app) ---
        if self._matches_dangerous_system_command(text):
            return Intent(intent="dangerous_system")

        return Intent(intent="unknown")

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