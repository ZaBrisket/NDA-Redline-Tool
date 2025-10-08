"""
Reasonableness Scoring System
Scores provisions on a 0-100 scale to determine if redlines are needed
"""
from typing import Dict, Any, Tuple, Optional
from enum import Enum


class ProvisionImportance(Enum):
    """Importance levels for different provisions"""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class ReasonablenessScorer:
    """Score how reasonable existing terms are before applying redlines"""

    # Scoring thresholds (0-100 scale)
    REASONABLENESS_THRESHOLDS = {
        'confidentiality_term': {
            'ideal': (18, 24),  # months - score 100
            'acceptable': (12, 36),  # months - score 75
            'questionable': (6, 60),  # months - score 50
            'unreasonable': None  # everything else - score 25
        },
        'non_solicit_term': {
            'ideal': (6, 12),  # months - score 100
            'acceptable': (3, 24),  # months - score 75
            'questionable': (1, 36),  # months - score 50
            'unreasonable': None  # everything else - score 25
        },
        'geographic_scope': {
            'ideal': ['limited', 'business_areas_only', 'specific_states'],
            'acceptable': ['us_only', 'north_america'],
            'questionable': ['worldwide_with_limits'],
            'unreasonable': ['unlimited', 'worldwide_unrestricted']
        },
        'remedy': {
            'ideal': ['equitable_relief', 'specific_performance'],
            'acceptable': ['injunctive_relief', 'both_legal_and_equitable'],
            'questionable': ['liquidated_damages'],
            'unreasonable': ['punitive_damages', 'automatic_penalties']
        }
    }

    # Importance levels for different provision types
    PROVISION_IMPORTANCE = {
        'confidentiality_term': ProvisionImportance.HIGH,
        'governing_law': ProvisionImportance.MODERATE,
        'non_solicit_term': ProvisionImportance.MODERATE,
        'employee_solicitation': ProvisionImportance.MODERATE,
        'return_destruction': ProvisionImportance.LOW,
        'geographic_scope': ProvisionImportance.MODERATE,
        'remedy': ProvisionImportance.MODERATE,
        'arbitration': ProvisionImportance.LOW,
        'assignment': ProvisionImportance.LOW,
        'severability': ProvisionImportance.LOW
    }

    def score_provision(self, provision_type: str, value: Any, context: Dict = None) -> int:
        """
        Return score 0-100 for how reasonable a provision is

        Args:
            provision_type: Type of provision (e.g., 'confidentiality_term')
            value: The value to score (e.g., 24 for months)
            context: Optional context about the deal/document

        Returns:
            Score from 0-100 (100 = perfectly reasonable, 0 = completely unreasonable)
        """

        thresholds = self.REASONABLENESS_THRESHOLDS.get(provision_type)
        if not thresholds:
            return 50  # neutral score if we don't have criteria

        # For numeric values (durations in months)
        if isinstance(value, (int, float)):
            return self._score_numeric_provision(value, thresholds)

        # For categorical values (like geographic scope)
        elif isinstance(value, str):
            return self._score_categorical_provision(value, thresholds)

        return 50  # default neutral score

    def _score_numeric_provision(self, value: float, thresholds: Dict) -> int:
        """Score numeric provisions like term length"""

        if value is None:
            return 0

        # Check ideal range
        if 'ideal' in thresholds:
            min_ideal, max_ideal = thresholds['ideal']
            if min_ideal <= value <= max_ideal:
                return 100

        # Check acceptable range
        if 'acceptable' in thresholds:
            min_acc, max_acc = thresholds['acceptable']
            if min_acc <= value <= max_acc:
                return 75

        # Check questionable range
        if 'questionable' in thresholds:
            min_q, max_q = thresholds['questionable']
            if min_q <= value <= max_q:
                return 50

        # Outside all ranges = unreasonable
        return 25

    def _score_categorical_provision(self, value: str, thresholds: Dict) -> int:
        """Score categorical provisions like geographic scope"""

        value_lower = value.lower()

        # Check ideal
        if 'ideal' in thresholds:
            if any(ideal.lower() in value_lower for ideal in thresholds['ideal']):
                return 100

        # Check acceptable
        if 'acceptable' in thresholds:
            if any(acc.lower() in value_lower for acc in thresholds['acceptable']):
                return 75

        # Check questionable
        if 'questionable' in thresholds:
            if any(q.lower() in value_lower for q in thresholds['questionable']):
                return 50

        # Check unreasonable
        if 'unreasonable' in thresholds:
            if any(unr.lower() in value_lower for unr in thresholds['unreasonable']):
                return 25

        return 50  # default

    def should_redline(
        self,
        score: int,
        provision_type: str,
        strategy: str = 'balanced'
    ) -> Tuple[bool, str]:
        """
        Decide whether to redline based on score, importance, and strategy

        Args:
            score: Reasonableness score (0-100)
            provision_type: Type of provision
            strategy: Redlining strategy ('light', 'balanced', 'aggressive')

        Returns:
            Tuple of (should_redline: bool, reason: str)
        """

        importance = self.PROVISION_IMPORTANCE.get(
            provision_type,
            ProvisionImportance.MODERATE
        )

        # Define thresholds for each strategy
        strategy_thresholds = {
            'light': {
                ProvisionImportance.CRITICAL: 25,
                ProvisionImportance.HIGH: 15,
                ProvisionImportance.MODERATE: 5,
                ProvisionImportance.LOW: 0
            },
            'balanced': {
                ProvisionImportance.CRITICAL: 50,
                ProvisionImportance.HIGH: 35,
                ProvisionImportance.MODERATE: 20,
                ProvisionImportance.LOW: 5
            },
            'aggressive': {
                ProvisionImportance.CRITICAL: 75,
                ProvisionImportance.HIGH: 60,
                ProvisionImportance.MODERATE: 40,
                ProvisionImportance.LOW: 25
            }
        }

        threshold = strategy_thresholds.get(strategy, {}).get(
            importance,
            50  # default
        )

        should_apply = score < threshold

        if should_apply:
            if score < 25:
                reason = "Provision is unreasonable and must be changed"
            elif score < 50:
                reason = "Provision is questionable and should be improved"
            elif score < 75:
                reason = "Provision is acceptable but could be better"
            else:
                reason = "Minor improvement recommended"
        else:
            reason = f"Provision is already reasonable (score: {score}/100)"

        return should_apply, reason

    def score_document_overall(self, provision_scores: Dict[str, int]) -> Dict:
        """
        Calculate overall document reasonableness

        Args:
            provision_scores: Dict mapping provision_type to score

        Returns:
            Dict with overall stats
        """

        if not provision_scores:
            return {
                'overall_score': 0,
                'total_provisions': 0,
                'unreasonable_count': 0,
                'questionable_count': 0,
                'acceptable_count': 0,
                'ideal_count': 0
            }

        scores = list(provision_scores.values())
        avg_score = sum(scores) / len(scores)

        return {
            'overall_score': int(avg_score),
            'total_provisions': len(scores),
            'unreasonable_count': sum(1 for s in scores if s < 25),
            'questionable_count': sum(1 for s in scores if 25 <= s < 50),
            'acceptable_count': sum(1 for s in scores if 50 <= s < 75),
            'ideal_count': sum(1 for s in scores if s >= 75),
            'needs_major_revision': avg_score < 40,
            'needs_minor_revision': 40 <= avg_score < 60,
            'generally_acceptable': avg_score >= 60
        }

    def get_redline_priority(self, score: int, importance: str) -> int:
        """
        Calculate redline priority (higher = more important to address)

        Args:
            score: Reasonableness score
            importance: Provision importance level

        Returns:
            Priority score (0-100, higher = higher priority)
        """

        importance_weights = {
            'critical': 1.5,
            'high': 1.2,
            'moderate': 1.0,
            'low': 0.7
        }

        weight = importance_weights.get(importance, 1.0)

        # Lower reasonableness score = higher priority
        # But weight by importance
        base_priority = (100 - score)  # Invert score
        weighted_priority = base_priority * weight

        return min(100, int(weighted_priority))

    def compare_alternatives(
        self,
        current_score: int,
        proposed_score: int,
        effort_required: str = 'medium'
    ) -> Dict:
        """
        Compare current provision vs proposed change

        Args:
            current_score: Score of existing provision
            proposed_score: Score of proposed alternative
            effort_required: Estimated negotiation effort ('low', 'medium', 'high')

        Returns:
            Dict with recommendation
        """

        improvement = proposed_score - current_score

        effort_costs = {
            'low': 10,
            'medium': 20,
            'high': 35
        }

        cost = effort_costs.get(effort_required, 20)

        # ROI: improvement per unit of effort
        roi = improvement / cost if cost > 0 else 0

        worth_it = roi > 1.0  # Worth it if improvement > cost

        return {
            'current_score': current_score,
            'proposed_score': proposed_score,
            'improvement': improvement,
            'effort_required': effort_required,
            'roi': round(roi, 2),
            'recommendation': 'pursue' if worth_it else 'skip',
            'reason': self._get_recommendation_reason(improvement, cost, worth_it)
        }

    def _get_recommendation_reason(
        self,
        improvement: int,
        cost: int,
        worth_it: bool
    ) -> str:
        """Generate explanation for recommendation"""

        if worth_it:
            if improvement > 40:
                return "Significant improvement, worth pursuing"
            elif improvement > 20:
                return "Moderate improvement, good ROI"
            else:
                return "Marginal improvement but low effort"
        else:
            if improvement < 5:
                return "Minimal improvement, not worth the effort"
            elif cost > 30:
                return "Improvement doesn't justify high negotiation cost"
            else:
                return "Better to focus on more material issues"
