"""
Atomic data writer with versioning and manifests.
"""

import json
import hashlib
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class DatasetFile:
    """File in dataset."""
    filename: str
    size_bytes: int
    checksum_sha256: str
    created_at: str
    mime_type: Optional[str] = None


@dataclass
class DatasetManifest:
    """Dataset version manifest."""
    dataset_id: str
    version: str
    run_id: str
    source: str
    created_at: str
    files: List[DatasetFile]
    metadata: Dict[str, Any]
    parent_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class AtomicDatasetWriter:
    """
    Atomic dataset writer with versioning.

    Ensures all-or-nothing writes:
    - Writes to temporary location
    - Validates all files
    - Atomic rename on success
    - Automatic cleanup on failure
    """

    def __init__(
        self,
        output_dir: Path,
        run_id: str,
        source: str,
        dataset_id: Optional[str] = None
    ):
        """
        Initialize atomic writer.

        Args:
            output_dir: Base output directory
            run_id: Execution run ID
            source: Data source name
            dataset_id: Override dataset ID (default: source)
        """
        self.output_dir = output_dir
        self.run_id = run_id
        self.source = source
        self.dataset_id = dataset_id or source

        # Create version based on timestamp
        self.version = datetime.utcnow().strftime('%Y%m%d-%H%M%S')

        # Temporary directory for atomic writes
        self.temp_dir = output_dir / f".tmp_{run_id}"
        self.final_dir = output_dir / self.dataset_id / self.version

        # Manifest tracking
        self.files: List[DatasetFile] = []
        self.metadata: Dict[str, Any] = {}

    def __enter__(self):
        """Context manager entry."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Atomic writer started: {self.temp_dir}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is None:
            # Success: commit
            try:
                self.commit()
            except Exception as e:
                logger.error(f"Commit failed: {e}")
                self.rollback()
                raise
        else:
            # Failure: rollback
            logger.error(f"Write failed: {exc_val}")
            self.rollback()

    def write_file(
        self,
        filename: str,
        data: Any,
        mime_type: Optional[str] = None
    ) -> Path:
        """
        Write file to temporary location.

        Args:
            filename: Relative filename
            data: Data to write (str, bytes, or dict/list for JSON)
            mime_type: MIME type for manifest

        Returns:
            Path to written file
        """
        filepath = self.temp_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Write based on type
        if isinstance(data, bytes):
            filepath.write_bytes(data)
        elif isinstance(data, str):
            filepath.write_text(data, encoding='utf-8')
        elif isinstance(data, (dict, list)):
            filepath.write_text(json.dumps(data, indent=2), encoding='utf-8')
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Compute checksum
        checksum = self._compute_checksum(filepath)

        # Add to manifest
        file_info = DatasetFile(
            filename=filename,
            size_bytes=filepath.stat().st_size,
            checksum_sha256=checksum,
            created_at=datetime.utcnow().isoformat(),
            mime_type=mime_type or self._guess_mime_type(filename)
        )
        self.files.append(file_info)

        logger.debug(f"Wrote file: {filename} ({file_info.size_bytes} bytes)")
        return filepath

    def set_metadata(self, key: str, value: Any):
        """Add metadata to manifest."""
        self.metadata[key] = value

    def commit(self):
        """
        Commit atomic write (rename temp -> final).

        This is atomic on most filesystems.
        """
        if not self.temp_dir.exists():
            raise RuntimeError("Nothing to commit")

        # Create manifest
        self._create_manifest()

        # Ensure final directory parent exists
        self.final_dir.parent.mkdir(parents=True, exist_ok=True)

        # Atomic rename
        logger.info(f"Committing: {self.temp_dir} -> {self.final_dir}")
        self.temp_dir.rename(self.final_dir)

        logger.info(f"Dataset committed: {self.final_dir}")

    def rollback(self):
        """
        Rollback (delete temporary directory).
        """
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info(f"Rolled back: {self.temp_dir}")

    def _create_manifest(self):
        """Create dataset manifest file."""
        # Get parent version if exists
        parent_version = self._get_latest_version()

        manifest = DatasetManifest(
            dataset_id=self.dataset_id,
            version=self.version,
            run_id=self.run_id,
            source=self.source,
            created_at=datetime.utcnow().isoformat(),
            files=self.files,
            metadata=self.metadata,
            parent_version=parent_version
        )

        manifest_file = self.temp_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest.to_dict(), indent=2))

        logger.info(f"Manifest created: {len(self.files)} files")

    def _get_latest_version(self) -> Optional[str]:
        """Get latest version of dataset."""
        dataset_dir = self.output_dir / self.dataset_id
        if not dataset_dir.exists():
            return None

        versions = sorted([
            d.name for d in dataset_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ], reverse=True)

        return versions[0] if versions else None

    def _compute_checksum(self, filepath: Path) -> str:
        """Compute SHA256 checksum."""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _guess_mime_type(self, filename: str) -> str:
        """Guess MIME type from filename."""
        ext = Path(filename).suffix.lower()
        mime_types = {
            '.json': 'application/json',
            '.csv': 'text/csv',
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.xml': 'application/xml',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
        }
        return mime_types.get(ext, 'application/octet-stream')


class DatasetVersionManager:
    """Manage dataset versions and cleanup."""

    def __init__(self, output_dir: Path):
        """Initialize version manager."""
        self.output_dir = output_dir

    def list_versions(self, dataset_id: str) -> List[str]:
        """List all versions of dataset."""
        dataset_dir = self.output_dir / dataset_id
        if not dataset_dir.exists():
            return []

        versions = sorted([
            d.name for d in dataset_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ], reverse=True)

        return versions

    def get_manifest(self, dataset_id: str, version: str) -> Optional[DatasetManifest]:
        """Load manifest for specific version."""
        manifest_file = self.output_dir / dataset_id / version / "manifest.json"
        if not manifest_file.exists():
            return None

        try:
            data = json.loads(manifest_file.read_text())
            return DatasetManifest(**data)
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            return None

    def cleanup_old_versions(self, dataset_id: str, keep_count: int = 5):
        """
        Keep only recent N versions, delete older ones.

        Args:
            dataset_id: Dataset to clean
            keep_count: Number of versions to keep
        """
        versions = self.list_versions(dataset_id)

        if len(versions) <= keep_count:
            return

        to_delete = versions[keep_count:]
        for version in to_delete:
            version_dir = self.output_dir / dataset_id / version
            try:
                shutil.rmtree(version_dir)
                logger.info(f"Deleted old version: {dataset_id}/{version}")
            except Exception as e:
                logger.error(f"Failed to delete version {version}: {e}")
