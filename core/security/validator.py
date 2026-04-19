import re

# Block common shell metacharacters and command chaining (see roadmap Phase 4).
_INVALID = re.compile(r"[;&|`$]|\$\(|&&|\|\||[\n\r]")


def validate_input(text: str) -> tuple[bool, str]:
    """
    Returns (ok, error_message). When ok is False, error_message is safe to show the user.
    """
    if not text or not text.strip():
        return False, "Input cannot be empty."

    if _INVALID.search(text):
        return False, "Input contains disallowed characters."

    return True, ""
