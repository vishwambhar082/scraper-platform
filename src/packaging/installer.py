"""
Installer builder for creating distributable packages.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess
import shutil
import json
import logging

from .version import get_version_info, save_version_metadata

logger = logging.getLogger(__name__)


class InstallerBuilder:
    """Build installer packages for distribution."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize installer builder.

        Args:
            project_root: Root directory of the project
            output_dir: Output directory for built installers
        """
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.output_dir = output_dir or self.project_root / 'dist'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir = self.project_root / 'build'

    def build_pyinstaller(
        self,
        entry_point: str = 'src/ui/app.py',
        app_name: str = 'ScraperPlatform',
        icon: Optional[Path] = None,
        hidden_imports: Optional[List[str]] = None,
        data_files: Optional[List[tuple]] = None,
        one_file: bool = True
    ) -> Optional[Path]:
        """
        Build executable using PyInstaller.

        Args:
            entry_point: Main application entry point
            app_name: Application name
            icon: Path to application icon
            hidden_imports: List of hidden imports to include
            data_files: List of (src, dest) tuples for data files
            one_file: Build as single file executable

        Returns:
            Path to built executable or None on failure
        """
        try:
            import PyInstaller.__main__

            # Base PyInstaller arguments
            args = [
                str(self.project_root / entry_point),
                '--name', app_name,
                '--distpath', str(self.output_dir),
                '--workpath', str(self.build_dir / 'pyinstaller'),
                '--specpath', str(self.build_dir),
                '--clean',
                '--noconfirm',
            ]

            if one_file:
                args.append('--onefile')

            if icon:
                args.extend(['--icon', str(icon)])

            # Hidden imports
            default_hidden = [
                'PySide6',
                'structlog',
                'playwright',
                'selenium',
                'psutil',
                'cryptography',
            ]
            all_hidden = (hidden_imports or []) + default_hidden
            for imp in all_hidden:
                args.extend(['--hidden-import', imp])

            # Data files
            default_data = [
                ('config', 'config'),
                ('dsl', 'dsl'),
                ('schemas', 'schemas'),
            ]
            all_data = (data_files or []) + default_data
            for src, dest in all_data:
                src_path = self.project_root / src
                if src_path.exists():
                    args.extend(['--add-data', f'{src_path}{Path.pathsep}{dest}'])

            # Save version metadata
            version_file = self.build_dir / 'version.json'
            save_version_metadata(version_file)
            args.extend(['--add-data', f'{version_file}{Path.pathsep}.'])

            # Run PyInstaller
            logger.info(f"Building with PyInstaller: {' '.join(args)}")
            PyInstaller.__main__.run(args)

            # Find built executable
            exe_name = f"{app_name}.exe" if Path.name == 'nt' else app_name
            exe_path = self.output_dir / exe_name

            if exe_path.exists():
                logger.info(f"Executable built successfully: {exe_path}")
                return exe_path
            else:
                logger.error("Executable not found after build")
                return None

        except ImportError:
            logger.error("PyInstaller not installed. Run: pip install pyinstaller")
            return None
        except Exception as e:
            logger.error(f"PyInstaller build failed: {e}")
            return None

    def build_nuitka(
        self,
        entry_point: str = 'src/ui/app.py',
        app_name: str = 'ScraperPlatform',
        icon: Optional[Path] = None,
        standalone: bool = True,
        optimize: bool = True
    ) -> Optional[Path]:
        """
        Build executable using Nuitka (better performance).

        Args:
            entry_point: Main application entry point
            app_name: Application name
            icon: Path to application icon
            standalone: Build standalone executable
            optimize: Enable optimizations

        Returns:
            Path to built executable or None on failure
        """
        try:
            args = [
                'python', '-m', 'nuitka',
                str(self.project_root / entry_point),
                f'--output-dir={self.output_dir}',
                f'--output-filename={app_name}',
                '--assume-yes-for-downloads',
            ]

            if standalone:
                args.append('--standalone')

            if optimize:
                args.append('--lto=yes')

            if icon:
                args.append(f'--windows-icon-from-ico={icon}')

            # Include packages
            packages = ['PySide6', 'structlog', 'playwright', 'selenium']
            for pkg in packages:
                args.append(f'--include-package={pkg}')

            # Include data directories
            for dir_name in ['config', 'dsl', 'schemas']:
                data_dir = self.project_root / dir_name
                if data_dir.exists():
                    args.append(f'--include-data-dir={data_dir}={dir_name}')

            logger.info(f"Building with Nuitka: {' '.join(args)}")
            result = subprocess.run(args, check=True, capture_output=True, text=True)
            logger.debug(result.stdout)

            # Find built executable
            exe_name = f"{app_name}.exe" if Path.name == 'nt' else app_name
            exe_path = self.output_dir / exe_name

            if exe_path.exists():
                logger.info(f"Executable built successfully: {exe_path}")
                return exe_path
            else:
                logger.error("Executable not found after build")
                return None

        except FileNotFoundError:
            logger.error("Nuitka not installed. Run: pip install nuitka")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Nuitka build failed: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Nuitka build failed: {e}")
            return None

    def create_windows_installer(
        self,
        executable: Path,
        app_name: str = 'Scraper Platform',
        publisher: str = 'Your Company',
        install_dir: str = '{pf}\\ScraperPlatform'
    ) -> Optional[Path]:
        """
        Create Windows installer using Inno Setup.

        Args:
            executable: Path to built executable
            app_name: Application display name
            publisher: Publisher name
            install_dir: Default installation directory

        Returns:
            Path to installer or None on failure
        """
        try:
            version_info = get_version_info()

            # Create Inno Setup script
            iss_content = f"""
; Scraper Platform Installer Script

[Setup]
AppName={app_name}
AppVersion={version_info.to_string()}
AppPublisher={publisher}
DefaultDirName={install_dir}
DefaultGroupName={app_name}
OutputDir={self.output_dir}
OutputBaseFilename={app_name.replace(' ', '')}-Setup-{version_info.to_string()}
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
UninstallDisplayIcon={{app}}\\{executable.name}

[Files]
Source: "{executable}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{self.project_root}\\config\\*"; DestDir: "{{app}}\\config"; Flags: ignoreversion recursesubdirs
Source: "{self.project_root}\\dsl\\*"; DestDir: "{{app}}\\dsl"; Flags: ignoreversion recursesubdirs
Source: "{self.project_root}\\schemas\\*"; DestDir: "{{app}}\\schemas"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{{group}}\\{app_name}"; Filename: "{{app}}\\{executable.name}"
Name: "{{commondesktop}}\\{app_name}"; Filename: "{{app}}\\{executable.name}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{{app}}\\{executable.name}"; Description: "Launch {app_name}"; Flags: postinstall nowait skipifsilent
"""

            iss_file = self.build_dir / 'installer.iss'
            iss_file.write_text(iss_content)

            # Run Inno Setup compiler
            iscc_path = Path(r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe')
            if not iscc_path.exists():
                logger.warning("Inno Setup not found, skipping installer creation")
                logger.info(f"Install from: https://jrsoftware.org/isdl.php")
                logger.info(f"ISS script saved to: {iss_file}")
                return None

            subprocess.run([str(iscc_path), str(iss_file)], check=True)

            installer_name = f"{app_name.replace(' ', '')}-Setup-{version_info.to_string()}.exe"
            installer_path = self.output_dir / installer_name

            if installer_path.exists():
                logger.info(f"Installer created: {installer_path}")
                return installer_path

        except Exception as e:
            logger.error(f"Installer creation failed: {e}")

        return None

    def cleanup_build_artifacts(self) -> None:
        """Remove build artifacts."""
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            logger.info("Build artifacts cleaned up")
