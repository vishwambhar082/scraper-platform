"""
Wrapper around tools.approve_patch for CLI integration.
"""
from __future__ import annotations

from tools.approve_patch import main as approve_patch_main


def approve_patch(patch_id: str) -> int:
    return approve_patch_main(["--patch-id", patch_id])

