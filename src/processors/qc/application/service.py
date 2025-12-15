"""
QC Service Application Layer.

This module implements the application logic for QC processing,
coordinating between domain entities and infrastructure adapters.
"""

from typing import Iterable, List, Optional, Sequence
from src.processors.qc.domain.rules import (
    QCRecordValidator, 
    QCResultEvaluator, 
    QCRuleResult, 
    QCConfiguration,
    Record,
    SeverityLevel
)

class DefaultResultEvaluator(QCResultEvaluator):
    """Default implementation for evaluating QC results."""
    
    def __init__(self, config: QCConfiguration):
        self.config = config
    
    def should_pass(self, results: list[QCRuleResult]) -> bool:
        """Determine if the overall QC check should pass based on results."""
        for result in results:
            if result.severity == SeverityLevel.ERROR and not result.passed:
                return False
            if self.config.fail_on_warning and result.severity == SeverityLevel.WARNING and not result.passed:
                return False
        return True


class QCService:
    """Main application service for quality control processing."""
    
    def __init__(
        self, 
        validators: Sequence[QCRecordValidator],
        evaluator: Optional[QCResultEvaluator] = None,
        config: Optional[QCConfiguration] = None
    ):
        self.validators = list(validators)
        self.evaluator = evaluator or DefaultResultEvaluator(config or QCConfiguration())
        self.config = config or QCConfiguration()
    
    def validate_record(self, record: Record) -> tuple[bool, list[QCRuleResult]]:
        """
        Validate a single record against all configured validators.
        
        Returns:
            Tuple of (overall_pass, individual_results)
        """
        results: List[QCRuleResult] = []
        
        for validator in self.validators:
            result = validator.validate(record)
            results.append(result)
            
            # Early exit if configured
            if self.config.stop_on_first_error and not result.passed and result.severity == SeverityLevel.ERROR:
                break
        
        overall_pass = self.evaluator.should_pass(results)
        return overall_pass, results
    
    def validate_batch(
        self, 
        records: Iterable[Record]
    ) -> tuple[list[Record], list[Record], list[list[QCRuleResult]]]:
        """
        Validate a batch of records.
        
        Returns:
            Tuple of (passed_records, failed_records, all_results)
        """
        passed_records: List[Record] = []
        failed_records: List[Record] = []
        all_results: List[List[QCRuleResult]] = []
        
        for record in records:
            overall_pass, results = self.validate_record(record)
            all_results.append(results)
            
            if overall_pass:
                passed_records.append(record)
            else:
                failed_records.append(record)
        
        return passed_records, failed_records, all_results