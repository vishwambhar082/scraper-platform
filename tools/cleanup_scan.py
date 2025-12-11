#!/usr/bin/env python3
"""
Scan the repository for files that should be cleaned up.
"""

import os
from pathlib import Path
from typing import List, Dict, Set
import hashlib

def get_file_hash(filepath: Path) -> str:
    """Get MD5 hash of file content."""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def find_duplicate_files(root: Path) -> Dict[str, List[Path]]:
    """Find duplicate files by content hash."""
    hash_to_files: Dict[str, List[Path]] = {}
    
    for filepath in root.rglob('*.py'):
        if '__pycache__' in str(filepath):
            continue
        try:
            file_hash = get_file_hash(filepath)
            if file_hash not in hash_to_files:
                hash_to_files[file_hash] = []
            hash_to_files[file_hash].append(filepath)
        except Exception:
            continue
    
    # Return only duplicates
    return {h: files for h, files in hash_to_files.items() if len(files) > 1}

def scan_for_cleanup(root: Path) -> Dict[str, List[Path]]:
    """Scan for files that should be cleaned up."""
    results: Dict[str, List[Path]] = {
        'pycache': [],
        'compiled': [],
        'logs': [],
        'temp': [],
        'duplicates': [],
    }
    
    # Patterns to match
    patterns = {
        'pycache': ['__pycache__'],
        'compiled': ['.pyc', '.pyo'],
        'logs': ['.log'],
        'temp': ['.tmp', '.temp', '.swp', '.bak'],
    }
    
    for filepath in root.rglob('*'):
        if filepath.is_dir():
            if '__pycache__' in filepath.name:
                results['pycache'].append(filepath)
        elif filepath.is_file():
            name_lower = filepath.name.lower()
            for category, pattern_list in patterns.items():
                if any(name_lower.endswith(p) for p in pattern_list):
                    results[category].append(filepath)
    
    # Find duplicates between src/ and minimal-scraper-app/
    src_dir = root / 'src'
    minimal_dir = root / 'minimal-scraper-app' / 'src'
    
    if src_dir.exists() and minimal_dir.exists():
        src_files = {f.relative_to(src_dir): f for f in src_dir.rglob('*.py') if '__pycache__' not in str(f)}
        minimal_files = {f.relative_to(minimal_dir): f for f in minimal_dir.rglob('*.py') if '__pycache__' not in str(f)}
        
        for rel_path in set(src_files.keys()) & set(minimal_files.keys()):
            src_file = src_files[rel_path]
            minimal_file = minimal_files[rel_path]
            try:
                if get_file_hash(src_file) == get_file_hash(minimal_file):
                    results['duplicates'].append(minimal_file)
            except Exception:
                pass
    
    return results

def main():
    """Main function."""
    root = Path(__file__).parent.parent
    results = scan_for_cleanup(root)
    
    print("=" * 80)
    print("CLEANUP SCAN RESULTS")
    print("=" * 80)
    
    total = 0
    for category, files in results.items():
        if files:
            print(f"\n{category.upper()}: {len(files)} items")
            for f in files[:10]:  # Show first 10
                print(f"  - {f.relative_to(root)}")
            if len(files) > 10:
                print(f"  ... and {len(files) - 10} more")
            total += len(files)
    
    print(f"\n{'=' * 80}")
    print(f"TOTAL ITEMS TO CLEAN: {total}")
    print("=" * 80)
    
    # Write detailed report
    report_file = root / 'CLEANUP_REPORT.txt'
    with open(report_file, 'w') as f:
        f.write("CLEANUP REPORT\n")
        f.write("=" * 80 + "\n\n")
        for category, files in results.items():
            if files:
                f.write(f"{category.upper()}: {len(files)} items\n")
                f.write("-" * 80 + "\n")
                for filepath in files:
                    f.write(f"{filepath.relative_to(root)}\n")
                f.write("\n")
    
    print(f"\nDetailed report written to: {report_file}")

if __name__ == '__main__':
    main()

