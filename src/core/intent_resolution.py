from core.action_results import CloseFileExplorerWindowsResult

EXPLORER_ALIASES: frozenset[str] = frozenset(
    {
        "explorer",
        "file explorer",
        "file manager",
        "windows explorer",
        "folders",
        "my files",
        "my folders",
    }
)


def _normalize_close_target(raw: str) -> str:
    s = raw.strip().lower()
    if s.endswith(".exe"):
        s = s[: -len(".exe")].strip()
    return s


def is_file_explorer_window_target(raw: str) -> bool:
    if not raw or not raw.strip():
        return False
    return _normalize_close_target(raw) in EXPLORER_ALIASES


def _terminal_close_slug(raw: str) -> str:
    return _normalize_close_target(raw).replace(" ", "")


def terminal_close_request_key(raw: str) -> str | None:
    """
    Map \"close powershell\" / \"close terminal\" style targets to a canonical key:

    ``powershell`` | ``pwsh`` | ``cmd`` | ``terminal``

    Returns None when the phrase should use generic app-close logic.
    """
    slug = _terminal_close_slug(raw)
    aliases: dict[str, str] = {
        "powershell": "powershell",
        "windowspowershell": "powershell",
        "pwsh": "pwsh",
        "powershellcore": "pwsh",
        "cmd": "cmd",
        "commandprompt": "cmd",
        "terminal": "terminal",
        "windowsterminal": "terminal",
        "wt": "terminal",
    }
    return aliases.get(slug)


def format_close_file_explorer_message(result: CloseFileExplorerWindowsResult) -> str:
    if result["status"] == "error":
        return result.get("detail") or "Could not close File Explorer windows."
    n = result["count"]
    if n == 0:
        return "No File Explorer windows were open."
    if n == 1:
        return "Closed 1 File Explorer window."
    return f"Closed {n} File Explorer windows."
