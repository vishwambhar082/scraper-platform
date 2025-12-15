"""
ETL Transformers Module

Collection of data transformation functions for ETL pipelines.
Provides common transformations like mapping, cleaning, normalization, and enrichment.

Author: Scraper Platform Team
"""

import logging
import re
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class FieldMapper:
    """
    Maps fields from source to destination schema.

    Supports nested fields, default values, and type conversion.
    """

    def __init__(self, field_mapping: Dict[str, str]):
        """
        Initialize field mapper.

        Args:
            field_mapping: Dictionary mapping source fields to destination fields
                          Format: {"dest_field": "source_field"}
        """
        self.field_mapping = field_mapping

    def transform(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform record by mapping fields.

        Args:
            record: Source record

        Returns:
            Mapped record
        """
        result = {}

        for dest_field, source_field in self.field_mapping.items():
            # Support nested field access with dot notation
            value = self._get_nested_value(record, source_field)
            if value is not None:
                result[dest_field] = value

        return result

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value


class DataCleaner:
    """
    Cleans and normalizes data fields.

    Handles trimming, case conversion, null removal, etc.
    """

    @staticmethod
    def trim_strings(record: Dict[str, Any]) -> Dict[str, Any]:
        """Trim whitespace from all string fields."""
        result = {}
        for key, value in record.items():
            if isinstance(value, str):
                result[key] = value.strip()
            else:
                result[key] = value
        return result

    @staticmethod
    def lowercase_fields(record: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """Convert specified fields to lowercase."""
        result = record.copy()
        for field in fields:
            if field in result and isinstance(result[field], str):
                result[field] = result[field].lower()
        return result

    @staticmethod
    def uppercase_fields(record: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """Convert specified fields to uppercase."""
        result = record.copy()
        for field in fields:
            if field in result and isinstance(result[field], str):
                result[field] = result[field].upper()
        return result

    @staticmethod
    def remove_nulls(record: Dict[str, Any]) -> Dict[str, Any]:
        """Remove fields with null/None values."""
        return {k: v for k, v in record.items() if v is not None}

    @staticmethod
    def remove_empty_strings(record: Dict[str, Any]) -> Dict[str, Any]:
        """Remove fields with empty string values."""
        return {k: v for k, v in record.items() if v != ""}

    @staticmethod
    def replace_nulls(record: Dict[str, Any], default: Any = "") -> Dict[str, Any]:
        """Replace null values with default."""
        result = {}
        for key, value in record.items():
            result[key] = value if value is not None else default
        return result


class TypeConverter:
    """
    Converts data types for fields.

    Handles string to int, float, date, etc.
    """

    @staticmethod
    def to_int(value: Any, default: int = 0) -> int:
        """Convert value to integer."""
        try:
            if isinstance(value, str):
                # Remove commas and whitespace
                value = value.replace(',', '').strip()
            return int(float(value))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        """Convert value to float."""
        try:
            if isinstance(value, str):
                value = value.replace(',', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def to_decimal(value: Any, default: Optional[Decimal] = None) -> Optional[Decimal]:
        """Convert value to Decimal."""
        try:
            if isinstance(value, str):
                value = value.replace(',', '').strip()
            return Decimal(str(value))
        except (ValueError, TypeError):
            return default or Decimal('0.00')

    @staticmethod
    def to_bool(value: Any, default: bool = False) -> bool:
        """Convert value to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes', 'y', 'on']
        return bool(value) if value is not None else default

    @staticmethod
    def to_date(
        value: Any,
        format: str = "%Y-%m-%d",
        default: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Convert value to datetime."""
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                return datetime.strptime(value, format)
            except ValueError:
                pass

        return default

    @staticmethod
    def convert_types(
        record: Dict[str, Any],
        type_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Convert field types based on mapping.

        Args:
            record: Input record
            type_mapping: Dictionary mapping field names to type names
                         Supported types: int, float, bool, str, date

        Returns:
            Record with converted types
        """
        result = record.copy()

        for field, target_type in type_mapping.items():
            if field not in result:
                continue

            value = result[field]

            if target_type == 'int':
                result[field] = TypeConverter.to_int(value)
            elif target_type == 'float':
                result[field] = TypeConverter.to_float(value)
            elif target_type == 'bool':
                result[field] = TypeConverter.to_bool(value)
            elif target_type == 'str':
                result[field] = str(value) if value is not None else ""
            elif target_type == 'date':
                result[field] = TypeConverter.to_date(value)

        return result


class ValueNormalizer:
    """
    Normalizes values according to business rules.

    Handles phone numbers, emails, addresses, etc.
    """

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number to standard format."""
        if not phone:
            return ""

        # Remove all non-numeric characters
        digits = re.sub(r'\D', '', phone)

        # Format as (XXX) XXX-XXXX if 10 digits
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

        return digits

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email address."""
        if not email:
            return ""
        return email.lower().strip()

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL."""
        if not url:
            return ""

        url = url.strip().lower()

        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        return url

    @staticmethod
    def normalize_price(price: str) -> float:
        """Normalize price string to float."""
        if not price:
            return 0.0

        # Remove currency symbols and commas
        price = re.sub(r'[^\d.]', '', price)

        try:
            return float(price)
        except ValueError:
            return 0.0


class DataEnricher:
    """
    Enriches records with additional computed fields.
    """

    @staticmethod
    def add_timestamp(record: Dict[str, Any], field_name: str = "processed_at") -> Dict[str, Any]:
        """Add processing timestamp to record."""
        result = record.copy()
        result[field_name] = datetime.now().isoformat()
        return result

    @staticmethod
    def add_hash(record: Dict[str, Any], field_name: str = "record_hash") -> Dict[str, Any]:
        """Add hash of record for deduplication."""
        import hashlib
        import json

        result = record.copy()

        # Create deterministic hash
        record_str = json.dumps(record, sort_keys=True)
        hash_value = hashlib.md5(record_str.encode()).hexdigest()

        result[field_name] = hash_value
        return result

    @staticmethod
    def add_computed_field(
        record: Dict[str, Any],
        field_name: str,
        compute_func: Callable[[Dict[str, Any]], Any]
    ) -> Dict[str, Any]:
        """Add a computed field using a custom function."""
        result = record.copy()
        result[field_name] = compute_func(record)
        return result


class DataValidator:
    """
    Validates data against rules.
    """

    @staticmethod
    def is_email_valid(email: str) -> bool:
        """Validate email format."""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def is_phone_valid(phone: str) -> bool:
        """Validate phone number."""
        if not phone:
            return False
        digits = re.sub(r'\D', '', phone)
        return len(digits) >= 10

    @staticmethod
    def is_url_valid(url: str) -> bool:
        """Validate URL format."""
        if not url:
            return False
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url, re.IGNORECASE))

    @staticmethod
    def validate_required_fields(
        record: Dict[str, Any],
        required_fields: List[str]
    ) -> bool:
        """Check if all required fields are present and non-empty."""
        for field in required_fields:
            if field not in record or not record[field]:
                logger.warning(f"Missing required field: {field}")
                return False
        return True


class TransformationPipeline:
    """
    Chains multiple transformations together.
    """

    def __init__(self, name: str = "default"):
        """
        Initialize transformation pipeline.

        Args:
            name: Pipeline name
        """
        self.name = name
        self.transformations: List[Callable] = []

    def add(self, transformation: Callable) -> 'TransformationPipeline':
        """Add a transformation function."""
        self.transformations.append(transformation)
        return self

    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply all transformations to records.

        Args:
            records: Input records

        Returns:
            Transformed records
        """
        result = records

        for i, transformation in enumerate(self.transformations):
            try:
                result = [transformation(record) for record in result]
                logger.debug(f"Applied transformation {i+1}/{len(self.transformations)}")
            except Exception as e:
                logger.error(f"Transformation {i+1} failed: {e}")
                raise

        return result


def create_standard_pipeline() -> TransformationPipeline:
    """
    Create a standard transformation pipeline with common transformations.

    Returns:
        Pre-configured transformation pipeline
    """
    pipeline = TransformationPipeline(name="standard")

    # Standard transformations
    pipeline.add(DataCleaner.trim_strings)
    pipeline.add(DataCleaner.remove_empty_strings)
    pipeline.add(lambda r: DataEnricher.add_timestamp(r))

    return pipeline
