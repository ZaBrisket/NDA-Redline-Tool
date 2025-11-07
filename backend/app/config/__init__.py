"""
Configuration module for NDA redline tool
"""

from .confidence_thresholds import (
    ConfidenceLevel,
    ProcessingAction,
    CONFIDENCE_THRESHOLDS,
    PATTERN_CONFIDENCE_MAP,
    calculate_redline_confidence,
    should_validate_high_confidence,
    get_confidence_explanation
)
from .settings import Settings

__all__ = [
    'Settings',
    'ConfidenceLevel',
    'ProcessingAction',
    'CONFIDENCE_THRESHOLDS',
    'PATTERN_CONFIDENCE_MAP',
    'calculate_redline_confidence',
    'should_validate_high_confidence',
    'get_confidence_explanation'
]