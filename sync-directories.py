#!/usr/bin/env python3
"""
Script to synchronize code between main codebase and minimal-scraper-app.
"""

import os
import shutil
from pathlib import Path

def sync_directory(src: Path, dest: Path):
    """Sync files from src to dest directory."""
    if not src.exists():
        print(f"Source directory {src} does not exist")
        return
    
    # Create destination directory if it doesn't exist
    dest.mkdir(parents=True, exist_ok=True)
    
    # Remove existing files in destination
    for item in dest.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    
    # Copy files from source to destination
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, dest)
        elif item.is_dir():
            shutil.copytree(item, dest / item.name)
    
    print(f"Synced {src} -> {dest}")

def main():
    """Main function to sync all directories."""
    # Sync QC processors
    src_qc = Path("src/processors/qc")
    dest_qc = Path("minimal-scraper-app/src/processors/qc")
    sync_directory(src_qc, dest_qc)
    
    print("Directory synchronization complete!")

if __name__ == "__main__":
    main()