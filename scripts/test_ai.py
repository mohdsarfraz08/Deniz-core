"""scripts/test_ai.py — Live validation CLI tool for AI Foundation Layer.

Milestone 10.10 — OS Adapters Module Member

Allows interactive or single-command testing of the Phase 10 AI layer:
  - TriageRouter routing decision (tier, sensitivity, rationale)
  - PII scrubbing preview for Tier 2 cloud requests
  - Provider dispatch & IntentResult validation
  - Fail-closed fallback verification

Usage:
  python scripts/test_ai.py "launch my browser"
  python scripts/test_ai.py "delete C:/Users/alice/Documents/file.txt"
  python scripts/test_ai.py (runs interactive test loop)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from ai.classifier import AIClassifier
from ai.prompt_builder import PromptBuilder
from ai.router import Sensitivity, TriageRouter


def evaluate_query(query: str, classifier: AIClassifier, router: TriageRouter) -> None:
    """Evaluate a single query through router and classifier and print results."""
    print("=" * 60)
    print(f"Query: {query!r}")
    print("-" * 60)

    # 1. Triage Decision
    decision = router.route(query)
    print(f"Triage Decision:")
    print(f"  - Tier:        {decision.tier}")
    print(f"  - Sensitivity: {decision.sensitivity.value.upper()}")
    print(f"  - Reason:      {decision.reason}")

    # 2. PII Scrubbing check for Tier 2
    if decision.tier == 2:
        pb = PromptBuilder()
        scrubbed = pb.build_prompt(query, is_cloud=True)
        print(f"  - Cloud PII Scrubbing: Active")

    # 3. AI Classifier Execution
    print("\nExecuting Classifier...")
    try:
        result = classifier.classify(query)
        print(f"Result:")
        print(f"  - Intent:     {result.intent}")
        print(f"  - Target:     {result.target}")
        print(f"  - Value:      {result.value}")
        print(f"  - Confidence: {result.confidence:.2f}")
        print(f"  - Tier:       {result.tier}")
        print(f"  - Actionable: {result.is_actionable}")
        print(f"  - Unknown:    {result.is_unknown}")
    except Exception as exc:
        print(f"Classification failed with unhandled exception (Violates Fail-Closed!): {exc}")
    print("=" * 60 + "\n")


def main() -> None:
    router = TriageRouter()
    classifier = AIClassifier()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        evaluate_query(query, classifier, router)
        return

    print("Deniz Phase 10 AI Foundation Layer — Live Diagnostic Tool")
    print("Type your natural language command or 'exit' to quit.\n")

    while True:
        try:
            user_input = input("AI Test > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Exiting.")
                break
            evaluate_query(user_input, classifier, router)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


if __name__ == "__main__":
    main()
