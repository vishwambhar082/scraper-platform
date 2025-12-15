"""
Dataset manifest system for atomic writes.

Tracks file checksums and versions for data integrity.
"""

import logging
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    """File entry in manifest."""
    filename: str
    size_bytes: int
    checksum_sha256: str
    mime_type: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class DatasetManifest:
    """Dataset manifest with file metadata."""
    dataset_id: str
    version: str
    created_at: datetime
    pipeline_id: str
    source: str
    run_id: str
    files: List[FileEntry]
    metadata: Dict[str, Any]
    stats: Dict[str, Any]


class ManifestManager:
    """
    Manages dataset manifests for atomic writes.

    Features:
    - File checksums (SHA256)
    - Version tracking
    - Metadata storage
    """

    def __init__(self, output_dir: Path):
        """
        Initialize manifest manager.

        Args:
            output_dir: Base output directory
        """
        self.output_dir = output_dir

    def create_manifest(
        self,
        dataset_id: str,
        version: str,
        pipeline_id: str,
        source: str,
        run_id: str,
        files: List[FileEntry],
        metadata: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Any]] = None
    ) -> DatasetManifest:
        """
        Create dataset manifest.

        Args:
            dataset_id: Dataset identifier
            version: Dataset version
            pipeline_id: Pipeline identifier
            source: Data source
            run_id: Execution run ID
            files: List of file entries
            metadata: Optional metadata
            stats: Optional statistics

        Returns:
            Created manifest
        """
        manifest = DatasetManifest(
            dataset_id=dataset_id,
            version=version,
            created_at=datetime.utcnow(),
            pipeline_id=pipeline_id,
            source=source,
            run_id=run_id,
            files=files,
            metadata=metadata or {},
            stats=stats or {}
        )

        return manifest

    def save_manifest(self, manifest: DatasetManifest, manifest_dir: Path):
        """
        Save manifest to file.

        Args:
            manifest: Manifest to save
            manifest_dir: Directory to save manifest
        """
        manifest_dir.mkdir(parents=True, exist_ok=True)

        manifest_file = manifest_dir / "manifest.json"

        manifest_dict = {
            'dataset_id': manifest.dataset_id,
            'version': manifest.version,
            'created_at': manifest.created_at.isoformat(),
            'pipeline_id': manifest.pipeline_id,
            'source': manifest.source,
            'run_id': manifest.run_id,
            'files': [asdict(f) for f in manifest.files],
            'metadata': manifest.metadata,
            'stats': manifest.stats
        }

        manifest_file.write_text(json.dumps(manifest_dict, indent=2))
        logger.info(f"Manifest saved: {manifest_file}")

    def load_manifest(self, manifest_dir: Path) -> Optional[DatasetManifest]:
        """
        Load manifest from file.

        Args:
            manifest_dir: Directory containing manifest

        Returns:
            Loaded manifest or None if not found
        """
        manifest_file = manifest_dir / "manifest.json"

        if not manifest_file.exists():
            logger.warning(f"Manifest not found: {manifest_file}")
            return None

        data = json.loads(manifest_file.read_text())

        manifest = DatasetManifest(
            dataset_id=data['dataset_id'],
            version=data['version'],
            created_at=datetime.fromisoformat(data['created_at']),
            pipeline_id=data['pipeline_id'],
            source=data['source'],
            run_id=data['run_id'],
            files=[FileEntry(**f) for f in data['files']],
            metadata=data['metadata'],
            stats=data['stats']
        )

        return manifest

    def verify_files(self, manifest: DatasetManifest, data_dir: Path) -> Dict[str, bool]:
        """
        Verify file checksums against manifest.

        Args:
            manifest: Manifest to verify
            data_dir: Directory containing data files

        Returns:
            Dict mapping filename to verification status
        """
        results = {}

        for file_entry in manifest.files:
            filepath = data_dir / file_entry.filename

            if not filepath.exists():
                logger.warning(f"File missing: {filepath}")
                results[file_entry.filename] = False
                continue

            # Compute checksum
            checksum = self.compute_checksum(filepath)

            if checksum == file_entry.checksum_sha256:
                results[file_entry.filename] = True
            else:
                logger.error(f"Checksum mismatch: {filepath}")
                results[file_entry.filename] = False

        return results

    @staticmethod
    def compute_checksum(filepath: Path) -> str:
        """
        Compute SHA256 checksum of file.

        Args:
            filepath: Path to file

        Returns:
            Hexadecimal checksum
        """
        sha256 = hashlib.sha256()

        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    def list_versions(self, dataset_id: str) -> List[str]:
        """
        List all versions of dataset.

        Args:
            dataset_id: Dataset identifier

        Returns:
            List of version strings
        """
        dataset_dir = self.output_dir / dataset_id

        if not dataset_dir.exists():
            return []

        versions = []
        for version_dir in dataset_dir.iterdir():
            if version_dir.is_dir() and (version_dir / "manifest.json").exists():
                versions.append(version_dir.name)

        return sorted(versions)

    def get_latest_version(self, dataset_id: str) -> Optional[str]:
        """
        Get latest version of dataset.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Latest version string or None
        """
        versions = self.list_versions(dataset_id)
        return versions[-1] if versions else None
