"""
Lightweight ML heuristics used by the scraper platform.
"""
from .failure_predictor import FailurePredictor
from .anomaly_predictor import AnomalyPredictor
from .content_classifier import ContentClassifier
from .extraction_scorer import ExtractionScorer
from .selector_suggester import SelectorSuggester

__all__ = [
    "FailurePredictor",
    "AnomalyPredictor",
    "ContentClassifier",
    "ExtractionScorer",
    "SelectorSuggester",
]

