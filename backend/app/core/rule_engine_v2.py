"""
Enhanced Rule Engine v2 - Pass 0 Deterministic Rules
Works with rules_v2.yaml and StrictnessController
"""

import yaml
import re
import hashlib
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime
import logging
from collections import defaultdict

try:
    # Try absolute import for Railway deployment
    from backend.app.models.schemas_v2 import (
        ViolationSchema,
        RuleMatch,
        Severity,
        ViolationSource,
        ClauseType
    )
    from backend.app.core.strictness_controller import EnforcementLevel, StrictnessController
except ModuleNotFoundError:
    # Fall back to relative imports for local development
    from ..models.schemas_v2 import (
        ViolationSchema,
        RuleMatch,
        Severity,
        ViolationSource,
        ClauseType
    )
    from .strictness_controller import EnforcementLevel, StrictnessController

logger = logging.getLogger(__name__)


class RuleEngineV2:
    """
    Enhanced deterministic rule engine for Pass 0
    Features:
    - Enforcement level aware filtering
    - 35+ comprehensive patterns
    - No conditional logic (100% deterministic)
    - Performance optimization with compiled patterns
    """

    def __init__(self,
                 rules_path: Optional[str] = None,
                 enforcement_level: EnforcementLevel = EnforcementLevel.BALANCED):
        """Initialize rule engine with enforcement level"""

        # Load rules
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "models" / "rules_v2.yaml"

        with open(rules_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.metadata = config.get('metadata', {})
        self.all_rules = config.get('rules', [])
        self.processing_config = config.get('processing', {})

        # Initialize strictness controller
        self.strictness_controller = StrictnessController(enforcement_level)
        self.enforcement_level = enforcement_level

        # Filter rules by enforcement level
        self._filter_rules_by_enforcement()

        # Compile patterns
        self._compile_patterns()

        # Performance tracking
        self.stats = {
            'total_processed': 0,
            'total_matches': 0,
            'rule_hits': defaultdict(int)
        }

        logger.info(f"RuleEngineV2 initialized with {len(self.active_rules)} active rules for {enforcement_level.value} mode")

    def _filter_rules_by_enforcement(self):
        """Filter rules based on enforcement level"""
        self.active_rules = []

        for rule in self.all_rules:
            enforcement_levels = rule.get('enforcement_level', [])

            if self.enforcement_level.value in enforcement_levels:
                self.active_rules.append(rule)

        logger.info(f"Filtered {len(self.all_rules)} total rules to {len(self.active_rules)} for {self.enforcement_level.value}")

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        for rule in self.active_rules:
            if 'pattern' in rule:
                try:
                    rule['compiled_pattern'] = re.compile(
                        rule['pattern'],
                        re.IGNORECASE | re.MULTILINE
                    )
                except re.error as e:
                    logger.error(f"Failed to compile pattern for rule {rule.get('id')}: {e}")
                    rule['compiled_pattern'] = None

    def apply_rules(self,
                   working_text: str,
                   return_violations: bool = True) -> List[ViolationSchema]:
        """
        Apply deterministic rules to text (Pass 0)

        Args:
            working_text: Text to analyze
            return_violations: If True, return ViolationSchema objects

        Returns:
            List of violations found
        """
        self.stats['total_processed'] += 1
        violations = []

        # Apply each active rule
        for rule in self.active_rules:
            if not rule.get('compiled_pattern'):
                continue

            pattern = rule['compiled_pattern']

            # Find all matches
            for match in pattern.finditer(working_text):
                violation = self._create_violation(rule, match, working_text)
                if violation:
                    violations.append(violation)
                    self.stats['total_matches'] += 1
                    self.stats['rule_hits'][rule['id']] += 1

        # Deduplicate overlapping violations
        violations = self._deduplicate_violations(violations)

        # Apply final filtering from strictness controller
        violations = self.strictness_controller.filter_redlines(
            [v.dict() for v in violations]
        )

        # Convert back to ViolationSchema if needed
        if return_violations:
            final_violations = []
            for v in violations:
                final_violations.append(ViolationSchema(**v))
            return final_violations

        return violations

    def _create_violation(self,
                         rule: Dict,
                         match: re.Match,
                         working_text: str) -> Optional[ViolationSchema]:
        """Create a violation from a rule match"""

        action = rule.get('action', 'delete')
        start = match.start()
        end = match.end()
        original_text = match.group(0)

        # Generate revised text based on action
        revised_text = self._generate_revision(rule, match, action)

        # Check context requirements if any
        if not self._check_context_requirements(rule, start, end, working_text):
            return None

        # Create unique ID for this violation
        violation_id = self._generate_violation_id(rule['id'], start, original_text)

        # Determine clause type
        clause_type = self._map_rule_to_clause_type(rule.get('id', ''))

        violation = ViolationSchema(
            id=violation_id,
            clause_type=clause_type,
            rule_id=rule['id'],
            start=start,
            end=end,
            original_text=original_text,
            revised_text=revised_text,
            severity=Severity(rule.get('severity', 'moderate')),
            confidence=100.0,  # Deterministic rules are 100% confident
            source=ViolationSource.RULE,
            enforcement_levels=rule.get('enforcement_level', []),
            suppressed_in=self._get_suppressed_levels(rule),
            explanation=rule.get('explanation', ''),
            legal_risk=self._assess_legal_risk(rule),
            business_impact=self._assess_business_impact(rule)
        )

        return violation

    def _generate_revision(self,
                          rule: Dict,
                          match: re.Match,
                          action: str) -> str:
        """Generate revised text based on action"""

        original_text = match.group(0)

        if action == 'delete':
            return ""

        elif action == 'replace':
            replacement = rule.get('replacement', '')
            # Handle group references if any
            if replacement and match.groups():
                try:
                    return match.expand(replacement)
                except:
                    return replacement
            return replacement

        elif action == 'add_after':
            addition = rule.get('addition', '')
            return f"{original_text} {addition}"

        elif action == 'add_inline':
            addition = rule.get('addition', '')
            return f"{original_text.rstrip()} {addition}"

        elif action == 'suggest':
            return rule.get('suggestion', original_text)

        return original_text

    def _check_context_requirements(self,
                                   rule: Dict,
                                   start: int,
                                   end: int,
                                   working_text: str) -> bool:
        """Check if context requirements are met"""

        if 'context_required' not in rule:
            return True

        context_pattern = re.compile(rule['context_required'], re.IGNORECASE)

        # Get surrounding context (±200 chars)
        context_start = max(0, start - 200)
        context_end = min(len(working_text), end + 200)
        context = working_text[context_start:context_end]

        return bool(context_pattern.search(context))

    def _generate_violation_id(self,
                              rule_id: str,
                              position: int,
                              text: str) -> str:
        """Generate unique violation ID"""
        content = f"{rule_id}:{position}:{text[:50]}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _map_rule_to_clause_type(self, rule_id: str) -> ClauseType:
        """Map rule ID to clause type enum"""
        mappings = {
            'term': ClauseType.CONFIDENTIALITY_TERM,
            'governing': ClauseType.GOVERNING_LAW,
            'retention': ClauseType.DOCUMENT_RETENTION,
            'solicit': ClauseType.EMPLOYEE_SOLICITATION,
            'compete': ClauseType.NON_COMPETE,
            'injunctive': ClauseType.INJUNCTIVE_RELIEF,
            'represent': ClauseType.REPRESENTATIONS,
            'indemnif': ClauseType.INDEMNIFICATION,
            'assign': ClauseType.ASSIGNMENT,
            'jurisdiction': ClauseType.JURISDICTION,
            'survival': ClauseType.SURVIVAL,
            'purpose': ClauseType.PURPOSE_LIMITATION
        }

        for key, clause_type in mappings.items():
            if key in rule_id.lower():
                return clause_type

        return ClauseType.GENERAL

    def _get_suppressed_levels(self, rule: Dict) -> List[str]:
        """Get enforcement levels where this rule is suppressed"""
        all_levels = {"Bloody", "Balanced", "Lenient"}
        active_levels = set(rule.get('enforcement_level', []))
        return list(all_levels - active_levels)

    def _assess_legal_risk(self, rule: Dict) -> str:
        """Assess legal risk based on severity"""
        severity = rule.get('severity', 'moderate')

        risk_map = {
            'critical': "High legal risk - potential for significant liability or enforcement issues",
            'high': "Elevated legal risk - could impact enforceability or create obligations",
            'moderate': "Moderate legal risk - standard contractual concerns",
            'low': "Low legal risk - primarily business preference",
            'advisory': "Minimal legal risk - style or consistency issue"
        }

        return risk_map.get(severity, "Unknown risk level")

    def _assess_business_impact(self, rule: Dict) -> str:
        """Assess business impact based on rule type"""
        rule_id = rule.get('id', '')

        if 'term' in rule_id:
            return "Affects duration of confidentiality obligations"
        elif 'indemnif' in rule_id:
            return "Creates financial liability exposure"
        elif 'compete' in rule_id:
            return "Restricts business operations and competition"
        elif 'solicit' in rule_id:
            return "Limits hiring and recruitment activities"
        elif 'governing' in rule_id:
            return "Determines legal jurisdiction for disputes"
        else:
            return "Standard business operations impact"

    def _deduplicate_violations(self,
                               violations: List[ViolationSchema]) -> List[ViolationSchema]:
        """Remove overlapping violations, preferring higher severity"""

        if not violations:
            return []

        # Sort by position then severity
        severity_rank = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MODERATE: 3,
            Severity.LOW: 2,
            Severity.ADVISORY: 1
        }

        sorted_violations = sorted(
            violations,
            key=lambda v: (v.start, -severity_rank.get(v.severity, 0))
        )

        deduplicated = []
        last_end = -1

        for violation in sorted_violations:
            # Check for overlap
            if violation.start >= last_end:
                # No overlap, add this violation
                deduplicated.append(violation)
                last_end = violation.end
            else:
                # Overlap detected - higher severity already added
                logger.debug(f"Skipping overlapping violation {violation.id}")

        return deduplicated

    def get_confidence_score(self, violations: List[ViolationSchema]) -> float:
        """Calculate overall confidence score for rule matches"""

        if not violations:
            return 0.0

        # Rule matches are 100% confident
        # Score based on coverage and severity
        critical_count = sum(1 for v in violations if v.severity == Severity.CRITICAL)
        high_count = sum(1 for v in violations if v.severity == Severity.HIGH)

        # If we found critical issues, confidence is very high
        if critical_count > 0:
            return min(100.0, 95.0 + (critical_count * 2))

        # High severity issues also boost confidence
        if high_count > 0:
            return min(100.0, 85.0 + (high_count * 3))

        # Base confidence on total violations found
        return min(100.0, 70.0 + (len(violations) * 5))

    def get_statistics(self) -> Dict:
        """Get processing statistics"""
        return {
            'enforcement_level': self.enforcement_level.value,
            'active_rules': len(self.active_rules),
            'total_rules': len(self.all_rules),
            'documents_processed': self.stats['total_processed'],
            'total_matches': self.stats['total_matches'],
            'top_rules': self._get_top_rules(10),
            'average_matches_per_doc': (
                self.stats['total_matches'] / self.stats['total_processed']
                if self.stats['total_processed'] > 0 else 0
            )
        }

    def _get_top_rules(self, n: int = 10) -> List[Dict]:
        """Get top N most frequently matched rules"""
        sorted_rules = sorted(
            self.stats['rule_hits'].items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {'rule_id': rule_id, 'matches': count}
            for rule_id, count in sorted_rules[:n]
        ]

    def reset_statistics(self):
        """Reset processing statistics"""
        self.stats = {
            'total_processed': 0,
            'total_matches': 0,
            'rule_hits': defaultdict(int)
        }

    def validate_rules(self) -> Dict[str, List[str]]:
        """Validate rule configuration for issues"""
        issues = {
            'errors': [],
            'warnings': []
        }

        for rule in self.all_rules:
            # Check required fields
            if 'id' not in rule:
                issues['errors'].append(f"Rule missing 'id' field")
            if 'pattern' not in rule:
                issues['errors'].append(f"Rule {rule.get('id', '?')} missing 'pattern' field")
            if 'severity' not in rule:
                issues['warnings'].append(f"Rule {rule.get('id', '?')} missing 'severity' field")

            # Check pattern compilation
            if 'pattern' in rule:
                try:
                    re.compile(rule['pattern'])
                except re.error as e:
                    issues['errors'].append(f"Rule {rule.get('id', '?')} has invalid regex: {e}")

            # Check enforcement levels
            levels = rule.get('enforcement_level', [])
            valid_levels = {"Bloody", "Balanced", "Lenient"}
            for level in levels:
                if level not in valid_levels:
                    issues['warnings'].append(f"Rule {rule.get('id', '?')} has invalid enforcement level: {level}")

        return issues