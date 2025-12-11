"""Cross-platform file/folder opener."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional


def open_path(path: str) -> bool:
    target = Path(path).expanduser().resolve()
    if not target.exists():
        return False
    try:
        if os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.call(["open", str(target)])
        else:
            subprocess.call(["xdg-open", str(target)])
        return True
    except Exception:
        return False


def open_parent_folder(path: str) -> bool:
    target = Path(path).expanduser().resolve()
    if target.is_file():
        target = target.parent
    return open_path(str(target))

