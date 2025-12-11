from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Core directories
CONFIG_DIR = ROOT / "config"
SESSIONS_DIR = ROOT / "sessions"
COOKIES_DIR = SESSIONS_DIR / "cookies"
SESSION_LOGS_DIR = SESSIONS_DIR / "logs"
OUTPUT_DIR = ROOT / "output"
INPUT_DIR = ROOT / "input"
LOGS_DIR = ROOT / "logs"
REPLAY_SNAPSHOTS_DIR = ROOT / "replay_snapshots"

for p in [
    SESSIONS_DIR,
    COOKIES_DIR,
    SESSION_LOGS_DIR,
    OUTPUT_DIR,
    INPUT_DIR,
    LOGS_DIR,
    REPLAY_SNAPSHOTS_DIR,
]:
    p.mkdir(parents=True, exist_ok=True)
