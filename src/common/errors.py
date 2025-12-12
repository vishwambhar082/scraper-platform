"""
Enterprise-grade error handling framework for Scraper Platform.

This module provides a comprehensive error taxonomy with error codes,
categorization, and structured error handling.

Error Code Ranges:
    E1000-E1999: Configuration errors
    E2000-E2999: Network errors
    E3000-E3999: Parsing errors
    E4000-E4999: Validation errors
    E5000-E5999: Storage errors
    E6000-E6999: Agent errors
    E7000-E7999: Pipeline errors
    E8000-E8999: Authentication errors
    E9000-E9999: Resource errors
"""

from typing import Dict, Any, Optional
import logging

log = logging.getLogger(__name__)


# ============================================================================
# Base Error Classes
# ============================================================================

class ScraperError(Exception):
    """Base exception for all scraper errors."""

    error_code: Optional[str] = None
    category: str = "GENERAL"

    def __init__(self, message: str, error_code: Optional[str] = None, **context):
        """
        Initialize scraper error.

        Args:
            message: Error message
            error_code: Optional error code (e.g., "E2001")
            **context: Additional context for debugging
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.error_code
        self.context = context

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "category": self.category,
            "context": self.context
        }


# ============================================================================
# Configuration Errors (E1000-E1999)
# ============================================================================

class ConfigurationError(ScraperError):
    """Base class for configuration errors."""
    error_code = "E1000"
    category = "CONFIGURATION"


class InvalidConfigError(ConfigurationError):
    """Invalid configuration structure or values."""
    error_code = "E1001"


class MissingConfigError(ConfigurationError):
    """Required configuration missing."""
    error_code = "E1002"


class ConfigValidationError(ConfigurationError):
    """Configuration failed validation."""
    error_code = "E1003"


class EnvironmentError(ConfigurationError):
    """Environment configuration error."""
    error_code = "E1004"


# ============================================================================
# Network Errors (E2000-E2999)
# ============================================================================

class NetworkError(ScraperError):
    """Base class for network-related errors."""
    error_code = "E2000"
    category = "NETWORK"


class ConnectionError(NetworkError):
    """Connection failed."""
    error_code = "E2001"


class TimeoutError(NetworkError):
    """Request timed out."""
    error_code = "E2002"


class HTTPError(NetworkError):
    """HTTP error response."""
    error_code = "E2003"

    def __init__(self, message: str, status_code: Optional[int] = None, **context):
        super().__init__(message, **context)
        self.status_code = status_code


class RateLimitError(NetworkError):
    """Rate limit exceeded."""
    error_code = "E2004"


class ProxyError(NetworkError):
    """Proxy-related error."""
    error_code = "E2005"


class DNSError(NetworkError):
    """DNS resolution failed."""
    error_code = "E2006"


class SSLError(NetworkError):
    """SSL/TLS error."""
    error_code = "E2007"


# ============================================================================
# Parsing Errors (E3000-E3999)
# ============================================================================

class ParsingError(ScraperError):
    """Base class for parsing errors."""
    error_code = "E3000"
    category = "PARSING"


class SelectorError(ParsingError):
    """CSS/XPath selector error."""
    error_code = "E3001"


class ElementNotFoundError(ParsingError):
    """Required element not found."""
    error_code = "E3002"


class DataExtractionError(ParsingError):
    """Data extraction failed."""
    error_code = "E3003"


class SchemaChangeError(ParsingError):
    """Website schema/structure changed."""
    error_code = "E3004"


class HTMLParseError(ParsingError):
    """HTML parsing failed."""
    error_code = "E3005"


class JSONParseError(ParsingError):
    """JSON parsing failed."""
    error_code = "E3006"


# ============================================================================
# Validation Errors (E4000-E4999)
# ============================================================================

class ValidationError(ScraperError):
    """Base class for validation errors."""
    error_code = "E4000"
    category = "VALIDATION"


class DataValidationError(ValidationError):
    """Data validation failed."""
    error_code = "E4001"


class SchemaValidationError(ValidationError):
    """Schema validation failed."""
    error_code = "E4002"


class QualityCheckError(ValidationError):
    """Quality check failed."""
    error_code = "E4003"


class DuplicateDataError(ValidationError):
    """Duplicate data detected."""
    error_code = "E4004"


# ============================================================================
# Storage Errors (E5000-E5999)
# ============================================================================

class StorageError(ScraperError):
    """Base class for storage errors."""
    error_code = "E5000"
    category = "STORAGE"


class DatabaseError(StorageError):
    """Database operation failed."""
    error_code = "E5001"


class FileWriteError(StorageError):
    """File write operation failed."""
    error_code = "E5002"


class FileReadError(StorageError):
    """File read operation failed."""
    error_code = "E5003"


class DiskFullError(StorageError):
    """Disk space exhausted."""
    error_code = "E5004"


class PermissionError(StorageError):
    """Insufficient permissions."""
    error_code = "E5005"


# ============================================================================
# Agent Errors (E6000-E6999)
# ============================================================================

class AgentError(ScraperError):
    """Base class for agent errors."""
    error_code = "E6000"
    category = "AGENT"


class LLMError(AgentError):
    """LLM API error."""
    error_code = "E6001"


class RepairError(AgentError):
    """Auto-repair failed."""
    error_code = "E6002"


class SelectorGenerationError(AgentError):
    """Selector generation failed."""
    error_code = "E6003"


class AnomalyDetectedError(AgentError):
    """Anomaly detected by agent."""
    error_code = "E6004"


# ============================================================================
# Pipeline Errors (E7000-E7999)
# ============================================================================

class PipelineError(ScraperError):
    """Base class for pipeline errors."""
    error_code = "E7000"
    category = "PIPELINE"


class CompilationError(PipelineError):
    """Pipeline compilation failed."""
    error_code = "E7001"


class StepExecutionError(PipelineError):
    """Step execution failed."""
    error_code = "E7002"


class DependencyError(PipelineError):
    """Dependency resolution failed."""
    error_code = "E7003"


class CircularDependencyError(PipelineError):
    """Circular dependency detected."""
    error_code = "E7004"


# ============================================================================
# Authentication Errors (E8000-E8999)
# ============================================================================

class AuthenticationError(ScraperError):
    """Base class for authentication errors."""
    error_code = "E8000"
    category = "AUTHENTICATION"


class LoginError(AuthenticationError):
    """Login failed."""
    error_code = "E8001"


class SessionExpiredError(AuthenticationError):
    """Session expired."""
    error_code = "E8002"


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials."""
    error_code = "E8003"


class CaptchaError(AuthenticationError):
    """CAPTCHA challenge encountered."""
    error_code = "E8004"


# ============================================================================
# Resource Errors (E9000-E9999)
# ============================================================================

class ResourceError(ScraperError):
    """Base class for resource errors."""
    error_code = "E9000"
    category = "RESOURCE"


class BrowserPoolExhaustedError(ResourceError):
    """Browser pool exhausted."""
    error_code = "E9001"


class ProxyPoolExhaustedError(ResourceError):
    """Proxy pool exhausted."""
    error_code = "E9002"


class MemoryError(ResourceError):
    """Out of memory."""
    error_code = "E9003"


class QuotaExceededError(ResourceError):
    """API quota exceeded."""
    error_code = "E9004"


# ============================================================================
# Legacy Compatibility
# ============================================================================

# Keep original error classes for backward compatibility
class BlockedError(NetworkError):
    """Website blocked access (bot detection)."""
    error_code = "E2008"


class CircuitOpenError(ResourceError):
    """Circuit breaker is open."""
    error_code = "E9005"


# ============================================================================
# Error Registry
# ============================================================================

ERROR_REGISTRY: Dict[str, type] = {
    # Configuration errors
    "E1000": ConfigurationError,
    "E1001": InvalidConfigError,
    "E1002": MissingConfigError,
    "E1003": ConfigValidationError,
    "E1004": EnvironmentError,

    # Network errors
    "E2000": NetworkError,
    "E2001": ConnectionError,
    "E2002": TimeoutError,
    "E2003": HTTPError,
    "E2004": RateLimitError,
    "E2005": ProxyError,
    "E2006": DNSError,
    "E2007": SSLError,
    "E2008": BlockedError,

    # Parsing errors
    "E3000": ParsingError,
    "E3001": SelectorError,
    "E3002": ElementNotFoundError,
    "E3003": DataExtractionError,
    "E3004": SchemaChangeError,
    "E3005": HTMLParseError,
    "E3006": JSONParseError,

    # Validation errors
    "E4000": ValidationError,
    "E4001": DataValidationError,
    "E4002": SchemaValidationError,
    "E4003": QualityCheckError,
    "E4004": DuplicateDataError,

    # Storage errors
    "E5000": StorageError,
    "E5001": DatabaseError,
    "E5002": FileWriteError,
    "E5003": FileReadError,
    "E5004": DiskFullError,
    "E5005": PermissionError,

    # Agent errors
    "E6000": AgentError,
    "E6001": LLMError,
    "E6002": RepairError,
    "E6003": SelectorGenerationError,
    "E6004": AnomalyDetectedError,

    # Pipeline errors
    "E7000": PipelineError,
    "E7001": CompilationError,
    "E7002": StepExecutionError,
    "E7003": DependencyError,
    "E7004": CircularDependencyError,

    # Authentication errors
    "E8000": AuthenticationError,
    "E8001": LoginError,
    "E8002": SessionExpiredError,
    "E8003": InvalidCredentialsError,
    "E8004": CaptchaError,

    # Resource errors
    "E9000": ResourceError,
    "E9001": BrowserPoolExhaustedError,
    "E9002": ProxyPoolExhaustedError,
    "E9003": MemoryError,
    "E9004": QuotaExceededError,
    "E9005": CircuitOpenError,
}


def get_error_class(error_code: str) -> Optional[type]:
    """Get error class by error code."""
    return ERROR_REGISTRY.get(error_code)


def categorize_error(error: Exception) -> str:
    """Categorize an error by type."""
    if isinstance(error, ScraperError):
        return error.category
    elif isinstance(error, (ConnectionRefusedError, ConnectionAbortedError)):
        return "NETWORK"
    elif isinstance(error, (FileNotFoundError, IsADirectoryError)):
        return "STORAGE"
    elif isinstance(error, (ValueError, TypeError)):
        return "VALIDATION"
    else:
        return "UNKNOWN"
