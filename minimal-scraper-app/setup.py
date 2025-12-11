#!/usr/bin/env python3
import os, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
VENV = ROOT / ".venv"
ENV_FILE = ROOT / ".env"

def info(msg): print(f"[INFO] {msg}")
def warn(msg): print(f"[WARN] {msg}")
def run(cmd, check=True, env=None):
    print(f"[RUN] {cmd}")
    return subprocess.run(cmd, shell=True, check=check, env=env)

def get_venv_bin(exe):
    if os.name == "nt":
        return str(VENV / "Scripts" / exe)
    else:
        return str(VENV / "bin" / exe)

def step_create_venv():
    if not VENV.exists():
        info("Creating virtual environment...")
        run(f'"{sys.executable}" -m venv "{VENV}"')
    else:
        info(".venv already exists.")

def step_pip_install():
    pip = get_venv_bin("pip.exe" if os.name == "nt" else "pip")
    if not Path(pip).exists():
        warn(f"pip not found in venv at {pip}")
        return
    info("Upgrading pip...")
    run(f'"{pip}" install --upgrade pip', check=False)
    req = ROOT / "requirements.txt"
    if req.exists():
        info("Installing requirements.txt...")
        run(f'"{pip}" install -r "{req}"', check=False)
    else:
        warn("requirements.txt not found, skipping.")

def step_env_and_dirs():
    if not ENV_FILE.exists():
        ENV_FILE.write_text("# scraper-platform-v4.8 env file\nALFABETA_USER_1=\nALFABETA_PASS_1=\n", encoding="utf-8")
        info("Created .env")
    for rel in ["sessions/cookies", "sessions/logs", "output/alfabeta/daily", "input"]:
        p = ROOT / rel
        p.mkdir(parents=True, exist_ok=True)
        info(f"Ensured dir: {p}")

def main():
    print("=== SCRAPER PLATFORM v4.8 SETUP ===")
    step_create_venv()
    step_pip_install()
    step_env_and_dirs()
    print("Setup basic environment complete.")

if __name__ == "__main__":
    main()
