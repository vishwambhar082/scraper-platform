"""
Auto-update mechanism for the scraper platform.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import json
import hashlib
import tempfile
import shutil
import subprocess
import logging

try:
    import requests
except ImportError:
    requests = None

from .version import VersionInfo, get_version_info

logger = logging.getLogger(__name__)


@dataclass
class UpdateInfo:
    """Information about an available update."""
    version: VersionInfo
    download_url: str
    release_notes: str
    published_at: datetime
    checksum: str
    size_bytes: int
    is_required: bool = False


class UpdateChecker:
    """Check for available updates from a remote server."""

    def __init__(
        self,
        update_url: str,
        check_interval_hours: int = 24,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize update checker.

        Args:
            update_url: URL to check for updates (JSON endpoint)
            check_interval_hours: Hours between update checks
            cache_dir: Directory to cache update information
        """
        self.update_url = update_url
        self.check_interval = timedelta(hours=check_interval_hours)
        self.cache_dir = cache_dir or Path.home() / '.scraper-platform' / 'updates'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / 'update_cache.json'

    def check_for_updates(self, force: bool = False) -> Optional[UpdateInfo]:
        """
        Check if updates are available.

        Args:
            force: Force check even if checked recently

        Returns:
            UpdateInfo if update available, None otherwise
        """
        if not requests:
            logger.warning("requests library not available, cannot check for updates")
            return None

        # Check cache first unless forced
        if not force and self.cache_file.exists():
            try:
                cache_data = json.loads(self.cache_file.read_text())
                last_check = datetime.fromisoformat(cache_data.get('last_check', ''))
                if datetime.utcnow() - last_check < self.check_interval:
                    if cache_data.get('update_available'):
                        return self._parse_update_info(cache_data['update_info'])
                    return None
            except Exception as e:
                logger.debug(f"Cache read error: {e}")

        # Fetch update information
        try:
            response = requests.get(self.update_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            current_version = get_version_info()
            latest_version = VersionInfo.from_string(data['version'])

            # Update cache
            cache_data = {
                'last_check': datetime.utcnow().isoformat(),
                'update_available': latest_version > current_version,
                'update_info': data if latest_version > current_version else None
            }
            self.cache_file.write_text(json.dumps(cache_data, indent=2))

            if latest_version > current_version:
                return self._parse_update_info(data)

        except Exception as e:
            logger.warning(f"Update check failed: {e}")

        return None

    def _parse_update_info(self, data: Dict[str, Any]) -> UpdateInfo:
        """Parse update info from JSON data."""
        return UpdateInfo(
            version=VersionInfo.from_string(data['version']),
            download_url=data['download_url'],
            release_notes=data.get('release_notes', ''),
            published_at=datetime.fromisoformat(data['published_at']),
            checksum=data['checksum'],
            size_bytes=data['size_bytes'],
            is_required=data.get('is_required', False)
        )


class AutoUpdater:
    """
    Auto-update manager for the scraper platform.

    Handles:
    - Downloading updates
    - Verifying checksums
    - Installing updates
    - Rollback on failure
    """

    def __init__(
        self,
        checker: UpdateChecker,
        install_dir: Optional[Path] = None,
        backup_dir: Optional[Path] = None
    ):
        """
        Initialize auto-updater.

        Args:
            checker: UpdateChecker instance
            install_dir: Installation directory (defaults to executable location)
            backup_dir: Backup directory for rollback
        """
        self.checker = checker
        self.install_dir = install_dir or Path(__file__).parent.parent.parent
        self.backup_dir = backup_dir or self.install_dir / '.backup'
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def download_update(
        self,
        update_info: UpdateInfo,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Path]:
        """
        Download update package.

        Args:
            update_info: Update information
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Returns:
            Path to downloaded file or None on failure
        """
        if not requests:
            logger.error("requests library not available")
            return None

        try:
            # Download to temp file
            temp_file = Path(tempfile.gettempdir()) / f"scraper-update-{update_info.version}.exe"

            response = requests.get(update_info.download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = update_info.size_bytes
            downloaded = 0

            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            # Verify checksum
            if not self._verify_checksum(temp_file, update_info.checksum):
                logger.error("Checksum verification failed")
                temp_file.unlink()
                return None

            logger.info(f"Update downloaded successfully: {temp_file}")
            return temp_file

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None

    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        actual_checksum = sha256.hexdigest()
        return actual_checksum == expected_checksum

    def create_backup(self) -> bool:
        """Create backup of current installation."""
        try:
            backup_path = self.backup_dir / f"backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            backup_path.mkdir(parents=True, exist_ok=True)

            # Backup critical directories
            for dir_name in ['src', 'config', 'dsl', 'schemas']:
                src_dir = self.install_dir / dir_name
                if src_dir.exists():
                    shutil.copytree(src_dir, backup_path / dir_name, dirs_exist_ok=True)

            # Save version info
            version_file = backup_path / 'version.json'
            version_info = get_version_info()
            version_file.write_text(json.dumps({
                'version': version_info.to_string(),
                'backup_date': datetime.utcnow().isoformat()
            }))

            logger.info(f"Backup created: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False

    def install_update(self, update_package: Path) -> bool:
        """
        Install update package.

        Args:
            update_package: Path to update installer

        Returns:
            True if installation succeeded
        """
        try:
            # Create backup before installation
            if not self.create_backup():
                logger.error("Backup failed, aborting update")
                return False

            # Run installer (platform-specific)
            if update_package.suffix == '.exe':
                # Windows installer
                subprocess.run([str(update_package), '/SILENT'], check=True)
            elif update_package.suffix in ['.sh', '.run']:
                # Linux installer
                subprocess.run(['sh', str(update_package), '--silent'], check=True)
            elif update_package.suffix == '.dmg':
                # macOS installer
                subprocess.run(['hdiutil', 'attach', str(update_package)], check=True)
            else:
                logger.error(f"Unknown installer format: {update_package.suffix}")
                return False

            logger.info("Update installed successfully")
            return True

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return False

    def rollback(self) -> bool:
        """Rollback to previous version from backup."""
        try:
            # Find most recent backup
            backups = sorted(self.backup_dir.glob('backup-*'), reverse=True)
            if not backups:
                logger.error("No backup found for rollback")
                return False

            latest_backup = backups[0]
            logger.info(f"Rolling back to: {latest_backup}")

            # Restore from backup
            for item in latest_backup.iterdir():
                if item.name == 'version.json':
                    continue
                dest = self.install_dir / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            logger.info("Rollback completed successfully")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def cleanup_old_backups(self, keep_count: int = 3) -> None:
        """Remove old backups, keeping only recent ones."""
        backups = sorted(self.backup_dir.glob('backup-*'), reverse=True)
        for old_backup in backups[keep_count:]:
            try:
                shutil.rmtree(old_backup)
                logger.debug(f"Removed old backup: {old_backup}")
            except Exception as e:
                logger.warning(f"Failed to remove backup {old_backup}: {e}")
