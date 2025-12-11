#!/usr/bin/env python3
"""
Helper script to configure Airflow auth manager for Windows.

Airflow 3.x requires an auth manager to be configured for the API server to start.
This script helps set up a simple auth manager.
"""

import os
from pathlib import Path

AIRFLOW_HOME = Path.home() / "airflow"
CONFIG_FILE = AIRFLOW_HOME / "airflow.cfg"


def setup_simple_auth() -> bool:
    """Configure Airflow to use SimpleAuthManager."""
    if not CONFIG_FILE.exists():
        print(f"Airflow config file not found at {CONFIG_FILE}")
        print("Run 'airflow db migrate' first to create the config file.")
        return False
    
    # Read config
    with open(CONFIG_FILE, 'r') as f:
        lines = f.readlines()
    
    # Check if auth_manager is already configured
    auth_configured = False
    new_lines = []
    
    in_core_section = False
    for line in lines:
        if line.strip().startswith('[core]'):
            in_core_section = True
            new_lines.append(line)
        elif line.strip().startswith('[') and in_core_section:
            # New section started, add auth_manager before it
            if not auth_configured:
                new_lines.append("auth_manager = airflow.api_fastapi.auth.managers.simple.simple_auth_manager.SimpleAuthManager\n")
                auth_configured = True
            in_core_section = False
            new_lines.append(line)
        elif in_core_section and line.strip().startswith('auth_manager'):
            # Already configured
            auth_configured = True
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Add at end of [core] section if not found
    if in_core_section and not auth_configured:
        new_lines.append("auth_manager = airflow.api_fastapi.auth.managers.simple.simple_auth_manager.SimpleAuthManager\n")
        auth_configured = True
    
    # Write back
    if auth_configured:
        with open(CONFIG_FILE, 'w') as f:
            f.writelines(new_lines)
        print(f"✅ Configured auth_manager in {CONFIG_FILE}")
        print("Restart Airflow services for changes to take effect.")
        return True
    else:
        print("Could not find [core] section in config file")
        return False


if __name__ == "__main__":
    print("Setting up Airflow SimpleAuthManager...")
    if setup_simple_auth():
        print("\n✅ Configuration complete!")
        print("\nNote: On Windows, Airflow has limited support.")
        print("For best results, consider using WSL2 or Linux.")
    else:
        print("\n❌ Configuration failed. Check the error messages above.")

