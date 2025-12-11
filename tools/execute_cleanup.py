#!/usr/bin/env python3
"""
Execute cleanup: remove duplicate files and unnecessary items.
"""

import shutil
from pathlib import Path
from typing import List

def remove_duplicates(root: Path) -> List[str]:
    """Remove duplicate files from minimal-scraper-app/src that exist in src/."""
    removed = []
    src_dir = root / 'src'
    minimal_dir = root / 'minimal-scraper-app' / 'src'
    
    if not minimal_dir.exists():
        return removed
    
    # Keep these unique files from minimal-scraper-app
    keep_files = {
        'simple_logging_config.py',  # Unique simple logging
    }
    
    # Remove duplicate src directory
    if minimal_dir.exists():
        for filepath in minimal_dir.rglob('*'):
            if filepath.is_file():
                rel_path = filepath.relative_to(minimal_dir)
                src_equivalent = src_dir / rel_path
                
                # Skip if it's a file we want to keep
                if filepath.name in keep_files:
                    continue
                
                # Remove if duplicate exists in src/
                if src_equivalent.exists():
                    try:
                        filepath.unlink()
                        removed.append(str(filepath.relative_to(root)))
                    except Exception as e:
                        print(f"Error removing {filepath}: {e}")
    
    # Remove empty directories
    for dirpath in sorted(minimal_dir.rglob('*'), reverse=True):
        if dirpath.is_dir():
            try:
                if not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    removed.append(f"{dirpath.relative_to(root)}/ (empty dir)")
            except Exception:
                pass
    
    return removed

def main():
    """Main cleanup function."""
    root = Path(__file__).parent.parent
    print("Starting cleanup...")
    
    removed = remove_duplicates(root)
    
    print(f"\nRemoved {len(removed)} duplicate files/directories")
    print("\nFirst 20 items removed:")
    for item in removed[:20]:
        print(f"  - {item}")
    if len(removed) > 20:
        print(f"  ... and {len(removed) - 20} more")
    
    # Save report
    report_file = root / 'CLEANUP_EXECUTED.txt'
    with open(report_file, 'w') as f:
        f.write("CLEANUP EXECUTED\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total items removed: {len(removed)}\n\n")
        for item in removed:
            f.write(f"{item}\n")
    
    print(f"\nReport saved to: {report_file}")

if __name__ == '__main__':
    main()

