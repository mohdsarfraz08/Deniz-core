"""ai/router.py — Three-tier triage router with AI Ethics sensitivity gating.

Milestone 10.5 — Security Module Member

Implements TriageRouter to classify user input into routing tiers:
  - Tier 0: Deterministic parser (zero latency, exact known commands).
  - Tier 1: Local Edge Engine via Ollama (fast basic natural language, offline,
    and ALL sensitive file/path operations that must never leave the device).
  - Tier 2: Cloud Specialist via Nebius Token Factory serving NVIDIA Nemotron
    (complex reasoning, multi-step planning, agentic workflows).
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Final


class Sensitivity(enum.Enum):
    """Data sensitivity level determining dispatch boundaries."""

    SAFE = "safe"
    SENSITIVE = "sensitive"


@dataclass(frozen=True)
class TriageDecision:
    """The outcome of a triage classification for a user input.

    Attributes:
        tier: Selected execution tier (0 = deterministic, 1 = Ollama local, 2 = Nebius cloud).
        sensitivity: Sensitivity classification (SAFE or SENSITIVE).
        reason: Explanation of why this tier and sensitivity were assigned.
    """

    tier: int
    sensitivity: Sensitivity
    reason: str


# Regex patterns indicating file system operations or local path references
_PATH_PATTERNS: Final[re.Pattern] = re.compile(
    r"""
    (?:[a-zA-Z]:[\\/])                     | # Drive letters (C:\, D:/)
    (?:[\\/][\w\.\-]+[\\/])                 | # Absolute or nested paths (/foo/bar)
    (?:\b[\w\.\-]+\.(?:txt|py|md|json|log|csv|ya?ml|docx?|xlsx?|pdf|env|sh|bat)\b) # File extensions
    """,
    re.IGNORECASE | re.VERBOSE,
)

_SENSITIVE_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        "create_file",
        "delete_file",
        "read_file",
        "write_file",
        "append_file",
        "copy_file",
        "move_file",
        "create_folder",
        "delete_folder",
        "move_folder",
        "list_directory",
        "search_files",
        "file",
        "folder",
        "directory",
        "delete",
        "remove",
        "erase",
        "rename",
        "wipe",
        "destroy",
    }
)

_COMPLEX_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        "plan",
        "planning",
        "workflow",
        "analyze",
        "analysis",
        "reason",
        "reasoning",
        "architect",
        "architecture",
        "generate",
        "script",
        "program",
        "refactor",
        "debug",
        "summarize",
        "multi-step",
        "sequence",
    }
)

# Exact command prefixes handled directly by Tier 0 deterministic parser
_TIER0_EXACT_PATTERNS: Final[tuple[str, ...]] = (
    "hello",
    "hi",
    "hey",
    "exit",
    "quit",
    "open chrome",
    "open edge",
    "open explorer",
    "open notepad",
    "open calculator",
    "close chrome",
    "close edge",
    "close explorer",
    "close notepad",
    "check cpu",
    "check memory",
    "what time is it",
    "show time",
    "time",
    "cpu",
    "memory",
    "also",
    "what else",
)


class TriageRouter:
    """Classifies user input into appropriate tier and sensitivity category."""

    def is_sensitive(self, user_input: str) -> bool:
        """Determine whether input contains sensitive local paths or file operations.

        Inputs touching the file system MUST stay on-device (Tier 1) and never be
        sent to cloud LLMs.

        Args:
            user_input: Raw user input text.

        Returns:
            True if input is classified as SENSITIVE, False otherwise.
        """
        lower = user_input.lower().strip()

        # Check for path patterns or file extensions
        if _PATH_PATTERNS.search(lower):
            return True

        # Check for sensitive action keywords
        tokens = set(re.findall(r"\b\w+\b", lower))
        if tokens & _SENSITIVE_KEYWORDS:
            return True

        return False

    def route(self, user_input: str) -> TriageDecision:
        """Evaluate user input and return a TriageDecision.

        Decision logic:
          1. Empty / whitespace -> Tier 0 unknown.
          2. Exact deterministic commands -> Tier 0 (zero latency).
          3. Sensitive input (file operations, local paths) -> Tier 1 (Ollama local edge).
          4. Complex reasoning / multi-step planning / code generation -> Tier 2 (Nebius cloud).
          5. General natural language -> Tier 1 (Ollama local edge).

        Args:
            user_input: Text entered by the user.

        Returns:
            TriageDecision with assigned tier, sensitivity, and reasoning.
        """
        trimmed = user_input.strip()
        lower = trimmed.lower()

        if not trimmed:
            return TriageDecision(
                tier=0,
                sensitivity=Sensitivity.SAFE,
                reason="Empty input routes to Tier 0 fallback",
            )

        # 1. Check exact Tier 0 deterministic commands
        if lower in _TIER0_EXACT_PATTERNS:
            return TriageDecision(
                tier=0,
                sensitivity=Sensitivity.SAFE,
                reason="Exact command matches Tier 0 deterministic parser",
            )

        # 2. AI Ethics Gate: Check sensitivity
        if self.is_sensitive(lower):
            return TriageDecision(
                tier=1,
                sensitivity=Sensitivity.SENSITIVE,
                reason="Sensitive file or path operation confined to Tier 1 local edge",
            )

        # 3. Check for complex reasoning / agentic planning keywords
        tokens = set(re.findall(r"\b\w+\b", lower))
        if tokens & _COMPLEX_KEYWORDS or len(trimmed.split()) > 15:
            return TriageDecision(
                tier=2,
                sensitivity=Sensitivity.SAFE,
                reason="Complex reasoning or planning dispatched to Tier 2 Cloud Specialist",
            )

        # 4. Standard conversational / natural language intent
        return TriageDecision(
            tier=1,
            sensitivity=Sensitivity.SAFE,
            reason="Standard natural language dispatched to Tier 1 Local Edge Engine",
        )
