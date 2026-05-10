from typing import Literal, NotRequired, TypedDict


class CloseFileExplorerWindowsResult(TypedDict):
    status: Literal["success", "error"]
    action: Literal["close_file_explorer_windows"]
    count: int
    detail: NotRequired[str]
