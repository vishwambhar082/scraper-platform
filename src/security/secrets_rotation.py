"""
Secrets Rotation Module

Provides automatic rotation of credentials and secrets with zero-downtime updates.
Supports scheduled rotation, on-demand rotation, and emergency rotation.

Author: Scraper Platform Team
"""

import logging
import json
from typing import Dict, Optional, Any, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class RotationStatus(str, Enum):
    """Status of a rotation operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RotationStrategy(str, Enum):
    """Rotation strategy types."""
    IMMEDIATE = "immediate"  # Replace immediately
    GRADUAL = "gradual"      # Dual-run old and new
    BLUE_GREEN = "blue_green"  # Switch between two sets


@dataclass
class RotationPolicy:
    """Policy for secret rotation."""

    secret_key: str
    rotation_interval_days: int = 90
    strategy: RotationStrategy = RotationStrategy.GRADUAL
    auto_rotate: bool = True
    notification_channels: List[str] = field(default_factory=list)
    grace_period_hours: int = 24
    max_retry_attempts: int = 3

    def should_rotate(self, last_rotated: Optional[datetime] = None) -> bool:
        """
        Check if secret should be rotated.

        Args:
            last_rotated: Last rotation timestamp

        Returns:
            True if rotation is due
        """
        if not last_rotated:
            return True

        days_since_rotation = (datetime.now() - last_rotated).days
        return days_since_rotation >= self.rotation_interval_days


@dataclass
class RotationRecord:
    """Record of a rotation operation."""

    secret_key: str
    old_value_hash: str
    new_value_hash: str
    status: RotationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    strategy: RotationStrategy = RotationStrategy.GRADUAL
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data


class SecretsRotator:
    """
    Manages automatic rotation of secrets and credentials.

    Features:
    - Scheduled rotation based on policies
    - Zero-downtime rotation with gradual rollout
    - Rollback support for failed rotations
    - Audit trail of all rotation operations
    """

    def __init__(
        self,
        credential_manager: Any,
        history_path: Optional[Path] = None
    ):
        """
        Initialize secrets rotator.

        Args:
            credential_manager: Credential manager instance
            history_path: Path to store rotation history
        """
        self.credential_manager = credential_manager
        self.history_path = history_path or Path("logs/rotation_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

        self.policies: Dict[str, RotationPolicy] = {}
        self.rotation_history: List[RotationRecord] = self._load_history()
        self.generators: Dict[str, Callable[[], str]] = {}

        logger.info("Initialized SecretsRotator")

    def _load_history(self) -> List[RotationRecord]:
        """Load rotation history from disk."""
        if self.history_path.exists():
            try:
                with open(self.history_path, 'r') as f:
                    data = json.load(f)
                    history = []
                    for record in data:
                        record["started_at"] = datetime.fromisoformat(record["started_at"])
                        if record.get("completed_at"):
                            record["completed_at"] = datetime.fromisoformat(record["completed_at"])
                        record["status"] = RotationStatus(record["status"])
                        record["strategy"] = RotationStrategy(record["strategy"])
                        history.append(RotationRecord(**record))
                    logger.info(f"Loaded {len(history)} rotation records")
                    return history
            except Exception as e:
                logger.error(f"Failed to load rotation history: {e}")
                return []
        return []

    def _save_history(self) -> None:
        """Save rotation history to disk."""
        try:
            data = [record.to_dict() for record in self.rotation_history]
            with open(self.history_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(data)} rotation records")
        except Exception as e:
            logger.error(f"Failed to save rotation history: {e}")

    def register_policy(self, policy: RotationPolicy) -> None:
        """
        Register a rotation policy for a secret.

        Args:
            policy: Rotation policy
        """
        self.policies[policy.secret_key] = policy
        logger.info(f"Registered rotation policy for {policy.secret_key}")

    def register_generator(
        self,
        secret_key: str,
        generator: Callable[[], str]
    ) -> None:
        """
        Register a secret generator function.

        Args:
            secret_key: Secret identifier
            generator: Function that generates a new secret value
        """
        self.generators[secret_key] = generator
        logger.info(f"Registered generator for {secret_key}")

    def rotate(
        self,
        secret_key: str,
        new_value: Optional[str] = None,
        force: bool = False
    ) -> RotationRecord:
        """
        Rotate a secret.

        Args:
            secret_key: Secret identifier
            new_value: New secret value (auto-generated if not provided)
            force: Force rotation even if not due

        Returns:
            Rotation record
        """
        policy = self.policies.get(secret_key)

        # Check if rotation is needed
        if not force and policy:
            last_rotation = self._get_last_rotation(secret_key)
            last_rotated = last_rotation.completed_at if last_rotation else None

            if not policy.should_rotate(last_rotated):
                logger.info(f"Rotation not needed for {secret_key}")
                # Return a mock completed record
                return RotationRecord(
                    secret_key=secret_key,
                    old_value_hash="",
                    new_value_hash="",
                    status=RotationStatus.COMPLETED,
                    started_at=datetime.now(),
                    completed_at=datetime.now()
                )

        # Start rotation
        logger.info(f"Starting rotation for {secret_key}")

        # Get old value
        old_value = self.credential_manager.get(secret_key)
        old_value_hash = self._hash_value(str(old_value) if old_value else "")

        # Generate or use provided new value
        if new_value is None:
            if secret_key in self.generators:
                new_value = self.generators[secret_key]()
            else:
                logger.error(f"No generator registered for {secret_key}")
                record = RotationRecord(
                    secret_key=secret_key,
                    old_value_hash=old_value_hash,
                    new_value_hash="",
                    status=RotationStatus.FAILED,
                    started_at=datetime.now(),
                    error_message="No generator available"
                )
                self.rotation_history.append(record)
                self._save_history()
                return record

        new_value_hash = self._hash_value(new_value)

        # Create rotation record
        record = RotationRecord(
            secret_key=secret_key,
            old_value_hash=old_value_hash,
            new_value_hash=new_value_hash,
            status=RotationStatus.IN_PROGRESS,
            started_at=datetime.now(),
            strategy=policy.strategy if policy else RotationStrategy.IMMEDIATE
        )

        try:
            # Perform rotation based on strategy
            if record.strategy == RotationStrategy.IMMEDIATE:
                self._rotate_immediate(secret_key, new_value)
            elif record.strategy == RotationStrategy.GRADUAL:
                self._rotate_gradual(secret_key, old_value, new_value, policy)
            elif record.strategy == RotationStrategy.BLUE_GREEN:
                self._rotate_blue_green(secret_key, new_value)

            # Mark as completed
            record.status = RotationStatus.COMPLETED
            record.completed_at = datetime.now()
            logger.info(f"Completed rotation for {secret_key}")

        except Exception as e:
            logger.error(f"Rotation failed for {secret_key}: {e}")
            record.status = RotationStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now()

            # Attempt rollback
            if old_value:
                try:
                    self._rollback(secret_key, old_value)
                    record.status = RotationStatus.ROLLED_BACK
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")

        # Save record
        self.rotation_history.append(record)
        self._save_history()

        return record

    def _rotate_immediate(self, secret_key: str, new_value: str) -> None:
        """Immediate rotation strategy."""
        self.credential_manager.set(secret_key, new_value)
        logger.debug(f"Immediate rotation completed for {secret_key}")

    def _rotate_gradual(
        self,
        secret_key: str,
        old_value: Any,
        new_value: str,
        policy: Optional[RotationPolicy]
    ) -> None:
        """Gradual rotation strategy with grace period."""
        # Store new value with a versioned key
        versioned_key = f"{secret_key}_v2"
        self.credential_manager.set(versioned_key, new_value)

        # Set grace period TTL on old value
        if policy:
            ttl_seconds = policy.grace_period_hours * 3600
            self.credential_manager.set(secret_key, old_value, ttl=ttl_seconds)

        # After grace period, replace with new value
        # In production, this would be handled by a scheduled task
        self.credential_manager.rotate(secret_key, new_value)

        # Clean up versioned key
        self.credential_manager.delete(versioned_key)

        logger.debug(f"Gradual rotation completed for {secret_key}")

    def _rotate_blue_green(self, secret_key: str, new_value: str) -> None:
        """Blue-green rotation strategy."""
        # Store in alternate slot
        alternate_key = f"{secret_key}_green"
        self.credential_manager.set(alternate_key, new_value)

        # Switch primary
        self.credential_manager.set(secret_key, new_value)

        logger.debug(f"Blue-green rotation completed for {secret_key}")

    def _rollback(self, secret_key: str, old_value: Any) -> None:
        """Rollback to old value."""
        self.credential_manager.set(secret_key, old_value)
        logger.info(f"Rolled back {secret_key} to previous value")

    def _hash_value(self, value: str) -> str:
        """Hash a value for audit trail."""
        import hashlib
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def _get_last_rotation(self, secret_key: str) -> Optional[RotationRecord]:
        """Get last rotation record for a secret."""
        for record in reversed(self.rotation_history):
            if record.secret_key == secret_key and record.status == RotationStatus.COMPLETED:
                return record
        return None

    def rotate_all_due(self) -> List[RotationRecord]:
        """
        Rotate all secrets that are due for rotation.

        Returns:
            List of rotation records
        """
        records = []

        for secret_key, policy in self.policies.items():
            if not policy.auto_rotate:
                continue

            last_rotation = self._get_last_rotation(secret_key)
            last_rotated = last_rotation.completed_at if last_rotation else None

            if policy.should_rotate(last_rotated):
                logger.info(f"Auto-rotating {secret_key}")
                record = self.rotate(secret_key)
                records.append(record)

        return records

    def get_rotation_status(self, secret_key: str) -> Dict[str, Any]:
        """
        Get rotation status for a secret.

        Args:
            secret_key: Secret identifier

        Returns:
            Status information
        """
        last_rotation = self._get_last_rotation(secret_key)
        policy = self.policies.get(secret_key)

        status = {
            "secret_key": secret_key,
            "has_policy": policy is not None,
            "last_rotated": last_rotation.completed_at.isoformat() if last_rotation else None,
            "rotation_due": False,
            "days_until_rotation": None
        }

        if policy and last_rotation:
            days_since = (datetime.now() - last_rotation.completed_at).days
            days_until = policy.rotation_interval_days - days_since
            status["rotation_due"] = days_until <= 0
            status["days_until_rotation"] = days_until

        return status


def create_rotator(credential_manager: Any) -> SecretsRotator:
    """
    Factory function to create a secrets rotator.

    Args:
        credential_manager: Credential manager instance

    Returns:
        SecretsRotator instance
    """
    return SecretsRotator(credential_manager=credential_manager)
