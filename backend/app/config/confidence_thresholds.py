"""
Confidence thresholds and scoring configuration for NDA redline processing
Based on analysis of 789 patterns from 84 training NDAs
"""

from typing import Dict, List, Tuple
from enum import Enum

class ConfidenceLevel(Enum):
    """Confidence level categories for redline processing"""
    HIGH = "high"          # 95-100% - Auto-apply
    MEDIUM = "medium"      # 85-94% - Flag for review
    LOW = "low"            # <85% - Require validation

class ProcessingAction(Enum):
    """Actions based on confidence level"""
    AUTO_APPLY = "auto_apply"           # Apply without validation
    SUGGEST_REVIEW = "suggest_review"   # Flag for user review
    REQUIRE_VALIDATION = "require_validation"  # Must validate with Claude

# Confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "high_threshold": 95,     # Above this: auto-apply
    "medium_threshold": 85,   # Above this: suggest, below: validate
    "validation_sample_rate": 0.15,  # Sample 15% of high-confidence for validation
}

# Pattern confidence scores based on training data frequency
# Pattern ID -> (base_confidence, frequency_in_training)
PATTERN_CONFIDENCE_MAP: Dict[str, Tuple[float, int]] = {
    # CRITICAL PATTERNS - Highest confidence (found in 7+ instances)
    "term_limit_specific_years_to_18mo": (98, 14),
    "governing_law_change_delaware": (97, 14),
    "representatives_definition_expansion": (96, 12),
    "non_solicit_carveouts": (95, 9),
    "non_solicit_scope_to_key_executives": (94, 9),
    "disclosure_practical_permissibility": (93, 7),

    # HIGH CONFIDENCE PATTERNS (found in 4-6 instances)
    "retention_carveout": (92, 5),
    "competition_disclaimer": (91, 5),
    "entity_name_generic_to_edgewater": (90, 4),
    "best_efforts_to_commercially_reasonable": (90, 4),

    # MEDIUM CONFIDENCE PATTERNS (found in 2-3 instances)
    "remove_indemnification": (87, 3),
    "portfolio_company_affiliate_carveout": (86, 3),
    "allow_assignment": (85, 2),
    "return_destroy_option": (85, 2),

    # CONTEXT-DEPENDENT PATTERNS (require context validation)
    "remove_affiliate_references": (80, 2),  # Lower because context-sensitive
    "remove_affiliate_standalone": (80, 2),
    "entity_name_with_designation": (82, 2),
    "equity_financing_consent_carveout": (88, 3),

    # DEFAULT for unknown patterns
    "default": (75, 0)
}

# Clause type confidence modifiers
# Some clause types are more reliable than others
CLAUSE_TYPE_CONFIDENCE_MODIFIER = {
    "confidentiality_term": 1.05,      # Very consistent pattern
    "governing_law": 1.05,             # Clear pattern
    "representatives_definition": 1.03, # Well-defined
    "entity_name": 1.02,               # Straightforward
    "employee_solicitation": 1.0,      # Standard
    "document_retention": 1.0,         # Standard
    "legal_modifier": 0.98,            # Slightly variable
    "competition_clause": 0.97,        # Context-dependent
    "affiliate_clause": 0.95,          # Highly context-dependent
    "indemnification": 1.0,            # Clear pattern
    "broker_clause": 1.0,              # Clear pattern
    "representations": 0.98,           # Can vary
    "assignment": 0.97,                # Can vary
    "jurisdiction": 1.0,               # Clear pattern
    "injunctive_relief": 0.98,        # Can vary
    "remedies": 0.97                  # Can vary
}

# Context indicators that increase confidence
POSITIVE_CONTEXT_INDICATORS = [
    # Document type indicators
    ("mutual", "non-disclosure", 5),      # Mutual NDA
    ("confidentiality agreement", 5),      # Clear NDA
    ("proprietary information", 3),        # Related to confidentiality

    # Party indicators
    ("edgewater", 10),                    # Our party mentioned
    ("recipient", "disclosing", 5),       # Clear party definitions

    # Standard language
    ("shall survive", 3),                 # Standard survival language
    ("governing law", 3),                 # Standard governing law section
    ("return or destroy", 3),             # Standard return language
]

# Context indicators that decrease confidence (ambiguous language)
NEGATIVE_CONTEXT_INDICATORS = [
    ("except as", -5),                    # Exception clause
    ("unless otherwise", -5),             # Conditional language
    ("notwithstanding", -3),              # Override language
    ("subject to", -3),                   # Conditional
    ("provided however", -3),             # Exception
    ("may be modified", -5),              # Flexibility clause
]

def calculate_redline_confidence(
    rule_id: str,
    clause_type: str,
    text_context: str,
    pattern_match_quality: float = 1.0
) -> Tuple[float, ConfidenceLevel, ProcessingAction]:
    """
    Calculate confidence score for a redline based on multiple factors

    Args:
        rule_id: The rule that matched
        clause_type: Type of clause being redlined
        text_context: Surrounding text for context analysis
        pattern_match_quality: How well the pattern matched (0-1)

    Returns:
        Tuple of (confidence_score, confidence_level, recommended_action)
    """
    # Get base confidence from pattern map
    base_confidence, frequency = PATTERN_CONFIDENCE_MAP.get(
        rule_id,
        PATTERN_CONFIDENCE_MAP["default"]
    )

    # Apply clause type modifier
    clause_modifier = CLAUSE_TYPE_CONFIDENCE_MODIFIER.get(clause_type, 1.0)

    # Calculate context score
    context_score = 0
    text_lower = text_context.lower()

    # Check positive indicators
    for *terms, score in POSITIVE_CONTEXT_INDICATORS:
        if all(term in text_lower for term in terms):
            context_score += score

    # Check negative indicators
    for *terms, score in NEGATIVE_CONTEXT_INDICATORS:
        if all(term in text_lower for term in terms):
            context_score += score

    # Calculate final confidence
    confidence = base_confidence * clause_modifier * pattern_match_quality

    # Add context score (capped at +/- 10)
    context_score = max(-10, min(10, context_score))
    confidence += context_score

    # Boost for high-frequency patterns
    if frequency >= 10:
        confidence += 3
    elif frequency >= 5:
        confidence += 2
    elif frequency >= 3:
        confidence += 1

    # Ensure confidence is in valid range
    confidence = max(0, min(100, confidence))

    # Determine confidence level
    if confidence >= CONFIDENCE_THRESHOLDS["high_threshold"]:
        level = ConfidenceLevel.HIGH
        action = ProcessingAction.AUTO_APPLY
    elif confidence >= CONFIDENCE_THRESHOLDS["medium_threshold"]:
        level = ConfidenceLevel.MEDIUM
        action = ProcessingAction.SUGGEST_REVIEW
    else:
        level = ConfidenceLevel.LOW
        action = ProcessingAction.REQUIRE_VALIDATION

    return confidence, level, action

def should_validate_high_confidence(confidence: float) -> bool:
    """
    Determine if a high-confidence redline should still be validated
    Based on sampling rate for quality control

    Args:
        confidence: The confidence score

    Returns:
        True if should validate despite high confidence
    """
    import random

    if confidence >= CONFIDENCE_THRESHOLDS["high_threshold"]:
        # Sample 15% of high-confidence redlines for validation
        return random.random() < CONFIDENCE_THRESHOLDS["validation_sample_rate"]
    return False

def get_confidence_explanation(
    confidence: float,
    level: ConfidenceLevel
) -> str:
    """
    Get human-readable explanation of confidence score

    Args:
        confidence: The confidence score
        level: The confidence level

    Returns:
        Explanation string
    """
    explanations = {
        ConfidenceLevel.HIGH: f"High confidence ({confidence:.1f}%) - Pattern found in multiple training examples. Auto-applying redline.",
        ConfidenceLevel.MEDIUM: f"Medium confidence ({confidence:.1f}%) - Pattern recognized but may need review. Suggesting redline.",
        ConfidenceLevel.LOW: f"Low confidence ({confidence:.1f}%) - Uncertain pattern. Requiring validation."
    }

    return explanations.get(level, f"Confidence: {confidence:.1f}%")

# Export key functions and constants
__all__ = [
    'ConfidenceLevel',
    'ProcessingAction',
    'CONFIDENCE_THRESHOLDS',
    'PATTERN_CONFIDENCE_MAP',
    'calculate_redline_confidence',
    'should_validate_high_confidence',
    'get_confidence_explanation'
]