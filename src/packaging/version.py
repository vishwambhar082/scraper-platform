"""
Version management for the scraper platform.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

VERSION = "1.0.0"
BUILD_DATE = datetime.utcnow().isoformat()


@dataclass
class VersionInfo:
    """Version information structure."""
    major: int
    minor: int
    patch: int
    build: Optional[str] = None
    commit_hash: Optional[str] = None
    build_date: Optional[str] = None

    @classmethod
    def from_string(cls, version_str: str) -> 'VersionInfo':
        """Parse version string like '1.2.3' or '1.2.3-beta.1'."""
        parts = version_str.split('-')
        version_parts = parts[0].split('.')

        major = int(version_parts[0])
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        patch = int(version_parts[2]) if len(version_parts) > 2 else 0
        build = parts[1] if len(parts) > 1 else None

        return cls(major=major, minor=minor, patch=patch, build=build)

    def to_string(self) -> str:
        """Convert to version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.build:
            version += f"-{self.build}"
        return version

    def __str__(self) -> str:
        return self.to_string()

    def __lt__(self, other: 'VersionInfo') -> bool:
        """Compare versions."""
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch

    def __eq__(self, other: object) -> bool:
        """Check version equality."""
        if not isinstance(other, VersionInfo):
            return False
        return (self.major == other.major and
                self.minor == other.minor and
                self.patch == other.patch)


def get_version_info() -> VersionInfo:
    """Get current version information."""
    version_info = VersionInfo.from_string(VERSION)
    version_info.build_date = BUILD_DATE

    # Try to get git commit hash
    try:
        from pathlib import Path
        git_dir = Path(__file__).parent.parent.parent / '.git'
        if git_dir.exists():
            head_file = git_dir / 'HEAD'
            if head_file.exists():
                ref = head_file.read_text().strip()
                if ref.startswith('ref: '):
                    ref_path = git_dir / ref[5:]
                    if ref_path.exists():
                        version_info.commit_hash = ref_path.read_text().strip()[:8]
    except Exception:
        pass

    return version_info


def save_version_metadata(output_path: Path) -> None:
    """Save version metadata to JSON file."""
    version_info = get_version_info()
    metadata = {
        'version': version_info.to_string(),
        'major': version_info.major,
        'minor': version_info.minor,
        'patch': version_info.patch,
        'build': version_info.build,
        'commit_hash': version_info.commit_hash,
        'build_date': version_info.build_date,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=2))
