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
    GREET_KEYWORDS = ["hello", "hi"]

    def parse(self, text: str) -> Intent:
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)

        # --- Greet ---
        if text in self.GREET_KEYWORDS:
            return Intent(intent="greet")

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

        return Intent(intent="unknown")