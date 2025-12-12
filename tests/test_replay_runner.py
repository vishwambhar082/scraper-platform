import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.tests_replay.replay_runner as replay_runner
import src.tests_replay.snapshot_loader as snapshot_loader


def _write_snapshot(path: Path, title: str = "") -> None:
    html = f"<html><head><title>{title}</title></head><body>content</body></html>"
    path.write_text(html, encoding="utf-8")


def test_list_snapshots_handles_kinds(monkeypatch, tmp_path):
    base = tmp_path / "snapshots"
    monkeypatch.setattr(replay_runner, "REPLAY_SNAPSHOTS_DIR", base)
    monkeypatch.setattr(snapshot_loader, "REPLAY_SNAPSHOTS_DIR", base)

    daily = base / "alfabeta" / "daily"
    weekly = base / "alfabeta" / "weekly"
    daily.mkdir(parents=True)
    weekly.mkdir(parents=True)

    daily_a = daily / "2024-01-01.html"
    daily_b = daily / "2024-01-02.htm"
    weekly_a = weekly / "2024-01-07.html"
    for path in (daily_a, daily_b, weekly_a):
        _write_snapshot(path)
    (daily / "ignore.txt").write_text("skip", encoding="utf-8")

    assert replay_runner.list_snapshots("alfabeta", "daily") == [daily_a, daily_b]
    assert replay_runner.list_snapshots("alfabeta") == [daily_a, daily_b, weekly_a]
    assert replay_runner.list_snapshots("missing") == []
    assert replay_runner.list_snapshots("alfabeta", "invalid") == []


def test_describe_snapshot_includes_relative_path(monkeypatch, tmp_path, caplog):
    base = tmp_path / "snapshots"
    monkeypatch.setattr(replay_runner, "REPLAY_SNAPSHOTS_DIR", base)
    path = base / "alfabeta" / "daily" / "2024-01-01.html"
    path.parent.mkdir(parents=True)
    _write_snapshot(path, title="Hello World")

    caplog.set_level("INFO")
    replay_runner.describe_snapshot(path)

    messages = [rec.message for rec in caplog.records if rec.levelname == "INFO"]
    # Cross-platform: check for components separately instead of full path
    assert any("alfabeta" in msg and "daily" in msg and "2024-01-01.html" in msg for msg in messages)
    assert any("Hello World" in msg for msg in messages)
