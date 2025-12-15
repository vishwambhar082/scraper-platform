# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Scraper Platform Desktop Application.

Build commands:
    Windows: pyinstaller ScraperPlatform.spec
    macOS: pyinstaller ScraperPlatform.spec --osx-bundle-identifier com.scraper-platform.app
    Linux: pyinstaller ScraperPlatform.spec

Signing:
    Windows: signtool sign /f cert.pfx /p password /t http://timestamp.digicert.com dist/ScraperPlatform.exe
    macOS: codesign --deep --force --verify --verbose --sign "Developer ID" dist/ScraperPlatform.app
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Project root
project_root = Path(SPECPATH)

# Collect all data files
datas = [
    # Configuration files
    (str(project_root / 'config'), 'config'),

    # DSL schema files
    (str(project_root / 'dsl'), 'dsl'),

    # JSON schemas
    (str(project_root / 'schemas'), 'schemas'),

    # UI resources (if any)
    # (str(project_root / 'resources'), 'resources'),
]

# Collect PySide6 data files
datas += collect_data_files('PySide6')

# Hidden imports - modules not detected by PyInstaller
hiddenimports = [
    # PySide6 modules
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',

    # Playwright/Selenium
    'playwright',
    'playwright.sync_api',
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.chrome',
    'selenium.webdriver.firefox',

    # Core dependencies
    'structlog',
    'psutil',
    'requests',
    'aiohttp',

    # Scraper platform modules
    'src.execution.core_engine',
    'src.scheduler.local_scheduler',
    'src.ui.app_state',
    'src.core.cancellation',
    'src.core.resource_governor',
    'src.run_tracking.checkpoints',
    'src.replay.replay_recorder',
    'src.observability.events',
    'src.storage.manifest',
    'src.plugins.loader',
    'src.agents.runtime',
    'src.entrypoints.bootstrap',

    # Security modules
    'src.security.secrets_manager',
    'src.security.vault_integration',
    'src.audit.logger',

    # Database
    'sqlite3',

    # Cryptography
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.backends',
]

# Collect all submodules from key packages
hiddenimports += collect_submodules('PySide6')
hiddenimports += collect_submodules('playwright')

# Excluded modules - reduce binary size
excludes = [
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'IPython',
    'notebook',
    'jupyter',
    'tkinter',
]

a = Analysis(
    ['src/ui/main_window.py'],  # Main entry point
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Single file executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ScraperPlatform',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application, no console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,  # Set to "Developer ID Application: Your Name" for macOS
    entitlements_file=None,
    icon=str(project_root / 'resources' / 'icon.ico') if (project_root / 'resources' / 'icon.ico').exists() else None,
)

# macOS .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='ScraperPlatform.app',
        icon=str(project_root / 'resources' / 'icon.icns') if (project_root / 'resources' / 'icon.icns').exists() else None,
        bundle_identifier='com.scraper-platform.app',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHumanReadableCopyright': 'Copyright © 2025 Scraper Platform',
        },
    )
