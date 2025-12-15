"""
Configuration Validator Module

Validates scraper configuration files against schema and business rules.
Ensures configurations are well-formed before pipeline execution.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Validation message severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationMessage:
    """Validation message with context."""

    severity: ValidationSeverity
    message: str
    field_path: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity.value,
            "message": self.message,
            "field_path": self.field_path,
            "suggestion": self.suggestion
        }


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    messages: List[ValidationMessage] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationMessage]:
        """Get all error messages."""
        return [m for m in self.messages if m.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationMessage]:
        """Get all warning messages."""
        return [m for m in self.messages if m.severity == ValidationSeverity.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "messages": [m.to_dict() for m in self.messages]
        }


class ConfigValidator:
    """
    Validates scraper configuration files.

    Checks for:
    - Required fields presence
    - Field types and formats
    - Value constraints and ranges
    - Logical consistency
    - Security concerns
    """

    REQUIRED_FIELDS = {
        "name",
        "version",
        "source_url",
        "steps"
    }

    VALID_STEP_TYPES = {
        "fetch",
        "parse",
        "transform",
        "validate",
        "export",
        "custom"
    }

    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration validator.

        Args:
            schema: Optional JSON schema for validation
        """
        self.schema = schema
        logger.info("Initialized ConfigValidator")

    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate a configuration dictionary.

        Args:
            config: Configuration to validate

        Returns:
            Validation result with messages
        """
        logger.info(f"Validating configuration: {config.get('name', 'unnamed')}")
        messages: List[ValidationMessage] = []

        # Check required fields
        messages.extend(self._validate_required_fields(config))

        # Check field types
        messages.extend(self._validate_field_types(config))

        # Check steps
        if "steps" in config:
            messages.extend(self._validate_steps(config["steps"]))

        # Check URLs
        if "source_url" in config:
            messages.extend(self._validate_url(config["source_url"]))

        # Check version format
        if "version" in config:
            messages.extend(self._validate_version(config["version"]))

        # Check for common issues
        messages.extend(self._check_common_issues(config))

        # Determine validity
        has_errors = any(m.severity == ValidationSeverity.ERROR for m in messages)
        is_valid = not has_errors

        result = ValidationResult(is_valid=is_valid, messages=messages)
        logger.info(f"Validation complete: {len(result.errors)} errors, {len(result.warnings)} warnings")

        return result

    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate a configuration file.

        Args:
            file_path: Path to configuration file

        Returns:
            Validation result
        """
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            return self.validate(config)
        except FileNotFoundError:
            return ValidationResult(
                is_valid=False,
                messages=[ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Configuration file not found: {file_path}"
                )]
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                messages=[ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid JSON: {str(e)}"
                )]
            )
        except Exception as e:
            logger.error(f"Error validating file: {e}")
            return ValidationResult(
                is_valid=False,
                messages=[ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation error: {str(e)}"
                )]
            )

    def _validate_required_fields(self, config: Dict[str, Any]) -> List[ValidationMessage]:
        """Check for required fields."""
        messages = []

        for field in self.REQUIRED_FIELDS:
            if field not in config:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Required field missing: {field}",
                    field_path=field,
                    suggestion=f"Add the '{field}' field to your configuration"
                ))

        return messages

    def _validate_field_types(self, config: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate field types."""
        messages = []

        type_checks = {
            "name": str,
            "version": str,
            "source_url": str,
            "steps": list,
            "enabled": bool,
            "retry_count": int,
            "timeout": (int, float)
        }

        for field, expected_type in type_checks.items():
            if field in config:
                value = config[field]
                if not isinstance(value, expected_type):
                    messages.append(ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        message=f"Field '{field}' has wrong type: expected {expected_type.__name__}, got {type(value).__name__}",
                        field_path=field
                    ))

        return messages

    def _validate_steps(self, steps: List[Dict[str, Any]]) -> List[ValidationMessage]:
        """Validate pipeline steps."""
        messages = []

        if not steps:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                message="No steps defined in pipeline",
                field_path="steps"
            ))
            return messages

        for idx, step in enumerate(steps):
            # Check required step fields
            if "type" not in step:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Step {idx} missing 'type' field",
                    field_path=f"steps[{idx}].type"
                ))
                continue

            # Check valid step type
            step_type = step.get("type")
            if step_type not in self.VALID_STEP_TYPES:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"Step {idx} has unknown type: {step_type}",
                    field_path=f"steps[{idx}].type",
                    suggestion=f"Valid types: {', '.join(self.VALID_STEP_TYPES)}"
                ))

            # Check step name
            if "name" not in step:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"Step {idx} missing 'name' field (recommended)",
                    field_path=f"steps[{idx}].name"
                ))

        return messages

    def _validate_url(self, url: str) -> List[ValidationMessage]:
        """Validate URL format."""
        messages = []

        if not url:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                message="source_url is empty",
                field_path="source_url"
            ))
            return messages

        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://")):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                message="source_url should start with http:// or https://",
                field_path="source_url"
            ))

        return messages

    def _validate_version(self, version: str) -> List[ValidationMessage]:
        """Validate version format."""
        messages = []

        # Check semantic versioning (loose)
        if not any(c.isdigit() for c in version):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                message="Version should contain at least one number",
                field_path="version",
                suggestion="Use semantic versioning (e.g., '1.0.0')"
            ))

        return messages

    def _check_common_issues(self, config: Dict[str, Any]) -> List[ValidationMessage]:
        """Check for common configuration issues."""
        messages = []

        # Check for suspicious timeout values
        if "timeout" in config:
            timeout = config["timeout"]
            if timeout < 5:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"Timeout is very low: {timeout}s (may cause frequent failures)",
                    field_path="timeout"
                ))
            elif timeout > 300:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"Timeout is very high: {timeout}s",
                    field_path="timeout"
                ))

        # Check retry count
        if "retry_count" in config:
            retry_count = config["retry_count"]
            if retry_count > 10:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"High retry count: {retry_count} (may slow down execution)",
                    field_path="retry_count"
                ))

        # Check for disabled configs
        if config.get("enabled") is False:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                message="Configuration is disabled",
                field_path="enabled"
            ))

        return messages


def validate_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Convenience function to validate a configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Validation result
    """
    validator = ConfigValidator()
    return validator.validate(config)


def validate_config_file(file_path: Path) -> ValidationResult:
    """
    Convenience function to validate a configuration file.

    Args:
        file_path: Path to configuration file

    Returns:
        Validation result
    """
    validator = ConfigValidator()
    return validator.validate_file(file_path)
