"""
Strictness Controller for NDA Review System
Controls enforcement levels: Bloody, Balanced, Lenient
"""
from enum import Enum
from typing import List, Dict, Optional, Set
import logging

logger = logging.getLogger(__name__)


class EnforcementLevel(Enum):
    """Enforcement level enumeration"""
    BLOODY = "Bloody"      # All rules - zero tolerance
    BALANCED = "Balanced"  # Critical + High + Moderate
    LENIENT = "Lenient"   # Critical only

    @classmethod
    def from_string(cls, level: str) -> 'EnforcementLevel':
        """Create enforcement level from string"""
        try:
            return cls(level)
        except ValueError:
            logger.warning(f"Invalid enforcement level: {level}, defaulting to BALANCED")
            return cls.BALANCED


class StrictnessController:
    """Controls rule enforcement based on selected strictness level"""

    # Severity mappings for each enforcement level
    SEVERITY_FILTERS = {
        EnforcementLevel.BLOODY: ["critical", "high", "moderate", "low", "advisory"],
        EnforcementLevel.BALANCED: ["critical", "high", "moderate"],
        EnforcementLevel.LENIENT: ["critical"]
    }

    # Pass routing thresholds by enforcement level
    ROUTING_THRESHOLDS = {
        EnforcementLevel.BLOODY: {
            "skip_gpt5_confidence": 95,      # Skip GPT-5 if rules confidence >= 95%
            "opus_confidence_trigger": 85,    # Route to Opus if confidence < 85%
            "consensus_required": 85,         # Consensus threshold for caching
            "enable_pass_4": True             # Always run consistency sweep
        },
        EnforcementLevel.BALANCED: {
            "skip_gpt5_confidence": 98,      # Skip GPT-5 if rules confidence >= 98%
            "opus_confidence_trigger": 80,    # Route to Opus if confidence < 80%
            "consensus_required": 90,         # Higher consensus required
            "enable_pass_4": True             # Run consistency sweep
        },
        EnforcementLevel.LENIENT: {
            "skip_gpt5_confidence": 100,     # Only skip GPT-5 if 100% rule coverage
            "opus_confidence_trigger": 70,    # Only route criticals < 70%
            "consensus_required": 95,         # Highest consensus required
            "enable_pass_4": False            # Skip consistency sweep
        }
    }

    def __init__(self, level: EnforcementLevel):
        """Initialize controller with enforcement level"""
        self.level = level
        self.severity_filter = set(self.SEVERITY_FILTERS[level])
        self.thresholds = self.ROUTING_THRESHOLDS[level]
        logger.info(f"Initialized StrictnessController with level: {level.value}")

    def should_flag(self, severity: str) -> bool:
        """Check if a severity level should be flagged"""
        return severity.lower() in self.severity_filter

    def filter_redlines(self, redlines: List[Dict]) -> List[Dict]:
        """Filter redlines based on enforcement level"""
        filtered = [
            r for r in redlines
            if self.should_flag(r.get('severity', '').lower())
        ]
        logger.debug(f"Filtered {len(redlines)} redlines to {len(filtered)} based on {self.level.value}")
        return filtered

    def should_skip_llm_pass(self,
                            pass_number: int,
                            rule_confidence: float,
                            severity: Optional[str] = None) -> bool:
        """Determine if an LLM pass should be skipped"""

        # Pass 1 (GPT-5) - Skip if rule confidence is high enough
        if pass_number == 1:
            skip = rule_confidence >= self.thresholds["skip_gpt5_confidence"]
            if skip:
                logger.info(f"Skipping Pass 1 (GPT-5) - Rule confidence {rule_confidence}% >= {self.thresholds['skip_gpt5_confidence']}%")
            return skip

        # Pass 3 (Opus) - Skip if confidence is high or severity not critical
        if pass_number == 3:
            if self.level == EnforcementLevel.LENIENT and severity != "critical":
                logger.info("Skipping Pass 3 (Opus) - Lenient mode, non-critical severity")
                return True
            return False

        # Pass 4 (Consistency) - Skip in Lenient mode
        if pass_number == 4:
            skip = not self.thresholds["enable_pass_4"]
            if skip:
                logger.info("Skipping Pass 4 (Consistency) - Disabled for Lenient mode")
            return skip

        return False

    def should_route_to_opus(self,
                           confidence: float,
                           severity: str,
                           has_disagreement: bool = False) -> bool:
        """Determine if an item should be routed to Opus for adjudication"""

        # Always route if there's model disagreement on critical items
        if has_disagreement and severity == "critical":
            logger.debug("Routing to Opus - Model disagreement on critical item")
            return True

        # Route based on confidence threshold
        if confidence < self.thresholds["opus_confidence_trigger"]:
            # In Lenient mode, only route critical items
            if self.level == EnforcementLevel.LENIENT and severity != "critical":
                return False
            logger.debug(f"Routing to Opus - Confidence {confidence}% < {self.thresholds['opus_confidence_trigger']}%")
            return True

        return False

    def get_cache_eligibility(self,
                            consensus_score: float,
                            all_passes_complete: bool) -> bool:
        """Determine if a result is eligible for caching"""

        # Only cache if all required passes are complete
        if not all_passes_complete:
            return False

        # Check consensus threshold
        eligible = consensus_score >= self.thresholds["consensus_required"]
        if not eligible:
            logger.debug(f"Not cache eligible - Consensus {consensus_score}% < {self.thresholds['consensus_required']}%")

        return eligible

    def get_prompt_adjustments(self) -> Dict[str, str]:
        """Get prompt adjustments based on enforcement level"""

        if self.level == EnforcementLevel.BLOODY:
            return {
                "stance": "extremely strict",
                "threshold": "flag any potential issue",
                "guidance": "Apply zero tolerance. Flag all deviations from ideal terms.",
                "temperature": 0.1
            }
        elif self.level == EnforcementLevel.BALANCED:
            return {
                "stance": "professionally strict",
                "threshold": "flag material issues",
                "guidance": "Focus on substantive issues that impact rights and obligations.",
                "temperature": 0.2
            }
        else:  # LENIENT
            return {
                "stance": "pragmatically focused",
                "threshold": "flag only critical issues",
                "guidance": "Only flag items that pose significant legal or business risk.",
                "temperature": 0.3
            }

    def get_required_clauses(self) -> Set[str]:
        """Get required clauses based on enforcement level"""

        base_required = {
            "term_limit",
            "confidentiality_definition",
            "permitted_use"
        }

        if self.level == EnforcementLevel.BLOODY:
            return base_required | {
                "return_destruction",
                "no_warranty",
                "competition_safe_harbor",
                "non_solicit_carveouts",
                "governing_law",
                "no_indemnification"
            }
        elif self.level == EnforcementLevel.BALANCED:
            return base_required | {
                "return_destruction",
                "no_warranty",
                "non_solicit_carveouts",
                "governing_law"
            }
        else:  # LENIENT
            return base_required

    def get_banned_tokens(self) -> List[str]:
        """Get banned tokens/phrases based on enforcement level"""

        base_banned = [
            "perpetual",
            "indefinite",
            "evergreen",
            "in perpetuity",
            "forever"
        ]

        if self.level == EnforcementLevel.BLOODY:
            return base_banned + [
                "unlimited",
                "irrevocable",
                "absolute discretion",
                "sole discretion",
                "without limitation",
                "indemnify",
                "hold harmless",
                "defend"
            ]
        elif self.level == EnforcementLevel.BALANCED:
            return base_banned + [
                "unlimited",
                "indemnify",
                "hold harmless"
            ]
        else:  # LENIENT
            return base_banned

    def format_summary(self, redlines: List[Dict]) -> Dict[str, any]:
        """Format summary with enforcement level context"""

        # Count by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "moderate": 0,
            "low": 0,
            "advisory": 0
        }

        for r in redlines:
            severity = r.get('severity', '').lower()
            if severity in severity_counts:
                severity_counts[severity] += 1

        # Determine overall stance
        if severity_counts["critical"] > 0:
            stance = "REJECT - Critical issues found"
        elif severity_counts["high"] > 2:
            stance = "REJECT - Multiple high-severity issues"
        elif severity_counts["high"] > 0:
            stance = "CONDITIONAL - Requires negotiation"
        elif severity_counts["moderate"] > 3:
            stance = "CONDITIONAL - Several improvements needed"
        else:
            stance = "ACCEPTABLE - Minor improvements suggested"

        return {
            "enforcement_level": self.level.value,
            "stance": stance,
            "total_issues": len(redlines),
            "severity_breakdown": severity_counts,
            "filtered_by_level": self.level != EnforcementLevel.BLOODY,
            "thresholds_applied": self.thresholds
        }


class MultiModeController:
    """Controller for running multiple enforcement levels in parallel"""

    def __init__(self):
        """Initialize multi-mode controller"""
        self.controllers = {
            level: StrictnessController(level)
            for level in EnforcementLevel
        }

    def run_all_modes(self, redlines: List[Dict]) -> Dict[str, List[Dict]]:
        """Run all enforcement modes and return results"""

        results = {}
        for level, controller in self.controllers.items():
            filtered = controller.filter_redlines(redlines)
            results[level.value] = filtered
            logger.info(f"{level.value} mode: {len(filtered)} issues")

        return results

    def get_comparison_summary(self, results: Dict[str, List[Dict]]) -> Dict:
        """Generate comparison summary across modes"""

        return {
            "mode_comparison": {
                mode: {
                    "total_issues": len(issues),
                    "critical": sum(1 for i in issues if i.get('severity') == 'critical'),
                    "would_reject": any(i.get('severity') == 'critical' for i in issues)
                }
                for mode, issues in results.items()
            },
            "recommendation": self._get_recommendation(results)
        }

    def _get_recommendation(self, results: Dict[str, List[Dict]]) -> str:
        """Generate recommendation based on multi-mode analysis"""

        bloody_critical = sum(1 for i in results.get("Bloody", [])
                            if i.get('severity') == 'critical')
        balanced_critical = sum(1 for i in results.get("Balanced", [])
                              if i.get('severity') == 'critical')
        lenient_critical = sum(1 for i in results.get("Lenient", [])
                             if i.get('severity') == 'critical')

        if lenient_critical > 0:
            return "REJECT - Critical issues present even in Lenient mode"
        elif balanced_critical > 0:
            return "NEGOTIATE - Critical issues in Balanced mode, consider business context"
        elif bloody_critical > 0:
            return "REVIEW - Issues only in strict mode, likely acceptable"
        else:
            return "ACCEPT - No critical issues in any mode"