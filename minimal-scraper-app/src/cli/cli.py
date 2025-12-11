"""
Unified CLI using argparse to expose common workflows.
"""
from __future__ import annotations

import argparse

from src.cli.scraper_wizard import create_source
from src.cli.debug_session import start_debug_session
from src.cli.migration_tool import apply_migrations
from src.cli.approve_patch import approve_patch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scraper-cli")
    sub = parser.add_subparsers(dest="command", required=True)

    wizard = sub.add_parser("create-source", help="Create a new scraper source")
    wizard.add_argument("--name", required=True)
    wizard.add_argument("--engine", default="selenium")

    debug = sub.add_parser("debug", help="Start a debug session")
    debug.add_argument("--source", required=True)
    debug.add_argument("--run-id")

    migrate = sub.add_parser("migrate", help="Apply DB migrations")

    approve = sub.add_parser("approve-patch", help="Approve scraper patch output")
    approve.add_argument("--patch-id", required=True)

    return parser


def app(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "create-source":
        create_source(args.name, engine=args.engine)
    elif args.command == "debug":
        start_debug_session(args.source, run_id=args.run_id)
    elif args.command == "migrate":
        apply_migrations()
    elif args.command == "approve-patch":
        approve_patch(args.patch_id)
    else:
        parser.error(f"Unknown command {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(app())

