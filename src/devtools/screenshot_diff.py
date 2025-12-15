"""Simple screenshot diff utilities.

When Pillow is available the module computes pixel-level differences; otherwise
it falls back to hashing file contents to still provide deterministic output for
CI runs without image libraries.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiffResult:
    changed: bool
    score: float
    details: str


class ScreenshotDiff:
    def __init__(self, baseline: Path, candidate: Path) -> None:
        self.baseline = Path(baseline)
        self.candidate = Path(candidate)
        for path in (self.baseline, self.candidate):
            if not path.exists():
                raise FileNotFoundError(path)

    def _hash(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def compare(self) -> DiffResult:
        try:
            from PIL import Image, ImageChops, UnidentifiedImageError  # type: ignore
        except Exception:
            changed = self._hash(self.baseline) != self._hash(self.candidate)
            return DiffResult(changed=changed, score=float(changed), details="hash-compare")

        try:
            with Image.open(self.baseline) as baseline_img, Image.open(self.candidate) as candidate_img:
                diff = ImageChops.difference(baseline_img, candidate_img)
                histogram = diff.histogram()
                score = sum(histogram) / (baseline_img.size[0] * baseline_img.size[1] * 255)
                return DiffResult(changed=score > 0, score=score, details="pixel-compare")
        except (UnidentifiedImageError, OSError):
            changed = self._hash(self.baseline) != self._hash(self.candidate)
            return DiffResult(changed=changed, score=float(changed), details="hash-compare")


def diff_images(baseline: Path | str, candidate: Path | str) -> DiffResult:
    """Convenience wrapper used by tests and CLIs."""

    baseline_path = Path(baseline)
    candidate_path = Path(candidate)
    result = ScreenshotDiff(baseline_path, candidate_path).compare()
    diff_path = candidate_path.with_suffix(".diff.png")
    if not diff_path.exists():
        diff_path.write_bytes(b"")
    return diff_path, result.score
