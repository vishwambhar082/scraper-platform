#!/usr/bin/env python
"""
Build script for creating distributable installers.

Usage:
    python build_installer.py [--method pyinstaller|nuitka] [--with-installer]
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from packaging.installer import InstallerBuilder
from packaging.version import get_version_info


def main():
    parser = argparse.ArgumentParser(description='Build Scraper Platform installer')
    parser.add_argument(
        '--method',
        choices=['pyinstaller', 'nuitka'],
        default='pyinstaller',
        help='Build method to use'
    )
    parser.add_argument(
        '--with-installer',
        action='store_true',
        help='Create Windows installer (requires Inno Setup)'
    )
    parser.add_argument(
        '--icon',
        type=Path,
        help='Path to application icon'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Cleanup build artifacts after build'
    )

    args = parser.parse_args()

    version_info = get_version_info()
    print(f"Building Scraper Platform v{version_info}")
    print(f"Build method: {args.method}")
    print("-" * 50)

    builder = InstallerBuilder()

    # Build executable
    if args.method == 'pyinstaller':
        executable = builder.build_pyinstaller(
            app_name='ScraperPlatform',
            icon=args.icon,
            one_file=True
        )
    else:  # nuitka
        executable = builder.build_nuitka(
            app_name='ScraperPlatform',
            icon=args.icon,
            standalone=True,
            optimize=True
        )

    if not executable:
        print("Build failed!")
        return 1

    print(f"\nExecutable built: {executable}")

    # Create Windows installer if requested
    if args.with_installer and sys.platform == 'win32':
        print("\nCreating Windows installer...")
        installer = builder.create_windows_installer(
            executable=executable,
            app_name='Scraper Platform'
        )
        if installer:
            print(f"Installer created: {installer}")
        else:
            print("Installer creation skipped (Inno Setup not found)")

    # Cleanup if requested
    if args.cleanup:
        print("\nCleaning up build artifacts...")
        builder.cleanup_build_artifacts()

    print("\nBuild completed successfully!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
