"""
Debug helper that proxies to tools.run_repair_session.
"""
from __future__ import annotations

from tools import run_repair_session


def start_debug_session(source: str, run_id: str | None = None) -> None:
    args = ["--source", source]
    if run_id:
        args.extend(["--run-id", run_id])
    run_repair_session.main(args)  # type: ignore[arg-type]

