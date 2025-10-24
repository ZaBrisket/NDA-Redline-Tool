"""
RuleEngine - Apply deterministic pattern-based redlines
First pass before LLM analysis for guaranteed accuracy on known patterns
"""
import yaml
import re
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Apply deterministic rules extracted from training data.

    Rules are defined in rules.yaml with:
    - Pattern matching (regex)
    - Severity levels
    - Action types (delete, replace, add_after, add_inline)
    """

    def __init__(self, rules_path: Optional[str] = None):
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "models" / "rules.yaml"

        with open(rules_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            self.rules = config.get('rules', [])

        # Compile patterns for efficiency
        for rule in self.rules:
            if 'pattern' in rule:
                rule['compiled_pattern'] = re.compile(
                    rule['pattern'],
                    re.IGNORECASE | re.DOTALL
                )

    def apply_rules(self, working_text: str) -> List[Dict]:
        """
        Apply all rules to working text and return redlines.

        Returns:
            List of redline dicts with:
            - rule_id: str
            - clause_type: str
            - start: int
            - end: int
            - original_text: str
            - revised_text: str
            - severity: str
            - confidence: int (always 100 for rules)
            - source: str (always 'rule')
            - explanation: str
        """
        redlines = []

        # Log text sample for debugging
        text_sample = working_text[:500] if len(working_text) > 500 else working_text
        logger.info(f"RuleEngine: Processing document with {len(working_text)} chars")
        logger.debug(f"Text sample: {text_sample}")

        for rule in self.rules:
            if 'compiled_pattern' not in rule:
                logger.debug(f"Skipping rule {rule.get('id', 'unknown')} - no compiled pattern")
                continue

            pattern = rule['compiled_pattern']
            rule_id = rule.get('id', 'unknown')

            matches = list(pattern.finditer(working_text))
            if matches:
                logger.info(f"Rule '{rule_id}' found {len(matches)} matches")
            else:
                logger.debug(f"Rule '{rule_id}' found no matches (pattern: {rule.get('pattern', 'N/A')[:50]}...)")

            for match in matches:
                redline = self._create_redline(rule, match, working_text)
                if redline:
                    logger.debug(f"Created redline: {rule_id} at {match.start()}-{match.end()}: '{match.group(0)[:50]}...'")
                    redlines.append(redline)

        # Remove duplicates and overlaps
        original_count = len(redlines)
        redlines = self._deduplicate_redlines(redlines)

        if original_count != len(redlines):
            logger.info(f"Deduplicated {original_count} redlines to {len(redlines)}")

        logger.info(f"RuleEngine: Returning {len(redlines)} redlines total")
        return redlines

    def _create_redline(self, rule: Dict, match: re.Match, working_text: str) -> Optional[Dict]:
        """Create a redline from a rule match"""
        action = rule.get('action', 'delete')

        start = match.start()
        end = match.end()
        original_text = match.group(0)

        # Determine revised text based on action
        revised_text = ""

        if action == 'delete':
            revised_text = ""

        elif action == 'replace':
            revised_text = rule.get('replacement', '')
            # Handle group references in replacement
            if revised_text and match.groups():
                try:
                    revised_text = match.expand(revised_text)
                except:
                    pass

        elif action == 'add_after':
            # Keep original and add new text after
            revised_text = original_text + " " + rule.get('addition', '')

        elif action == 'add_inline':
            # Insert addition within the matched text
            addition = rule.get('addition', '')
            # Simple approach: add at the end of match
            revised_text = original_text.rstrip() + " " + addition

        # Check context requirements
        if 'context_required' in rule:
            context_pattern = re.compile(rule['context_required'], re.IGNORECASE)
            # Get surrounding context
            context_start = max(0, start - 200)
            context_end = min(len(working_text), end + 200)
            context = working_text[context_start:context_end]

            if not context_pattern.search(context):
                # Context requirement not met, skip this match
                return None

        redline = {
            'rule_id': rule['id'],
            'clause_type': rule['type'],
            'start': start,
            'end': end,
            'original_text': original_text,
            'revised_text': revised_text,
            'severity': rule.get('severity', 'moderate'),
            'confidence': 100,  # Deterministic rules always 100% confident
            'source': 'rule',
            'explanation': rule.get('explanation', ''),
            'action': action
        }

        return redline

    def _deduplicate_redlines(self, redlines: List[Dict]) -> List[Dict]:
        """Remove duplicate and overlapping redlines, preferring higher severity"""
        if not redlines:
            return []

        # Sort by start position
        sorted_redlines = sorted(redlines, key=lambda r: r['start'])

        # Severity ranking
        severity_rank = {
            'critical': 3,
            'high': 2,
            'moderate': 1,
            'low': 0
        }

        deduplicated = []
        last_end = -1

        for redline in sorted_redlines:
            # Check for overlap with previous redline
            if redline['start'] < last_end:
                # Overlap detected
                if deduplicated:
                    prev = deduplicated[-1]

                    # Keep the higher severity one
                    prev_severity = severity_rank.get(prev['severity'], 0)
                    curr_severity = severity_rank.get(redline['severity'], 0)

                    if curr_severity > prev_severity:
                        # Replace previous with current
                        deduplicated[-1] = redline
                        last_end = redline['end']
                    # else keep previous
            else:
                # No overlap, add this redline
                deduplicated.append(redline)
                last_end = redline['end']

        return deduplicated

    def get_rules_by_type(self, clause_type: str) -> List[Dict]:
        """Get all rules for a specific clause type"""
        return [r for r in self.rules if r.get('type') == clause_type]

    def get_critical_rules(self) -> List[Dict]:
        """Get all critical severity rules"""
        return [r for r in self.rules if r.get('severity') == 'critical']

    def summarize_rules(self) -> Dict:
        """Get summary statistics of loaded rules"""
        total = len(self.rules)
        by_severity = {}
        by_type = {}

        for rule in self.rules:
            severity = rule.get('severity', 'unknown')
            by_severity[severity] = by_severity.get(severity, 0) + 1

            clause_type = rule.get('type', 'unknown')
            by_type[clause_type] = by_type.get(clause_type, 0) + 1

        return {
            'total_rules': total,
            'by_severity': by_severity,
            'by_type': by_type
        }


class RuleConflictDetector:
    """Detect conflicts between rules"""

    @staticmethod
    def find_conflicts(redlines: List[Dict]) -> List[Dict]:
        """Find redlines that conflict with each other"""
        conflicts = []

        for i, r1 in enumerate(redlines):
            for r2 in redlines[i+1:]:
                # Check for overlap
                if r1['end'] > r2['start'] and r1['start'] < r2['end']:
                    conflicts.append({
                        'redline1': r1,
                        'redline2': r2,
                        'type': 'overlap',
                        'overlap_start': max(r1['start'], r2['start']),
                        'overlap_end': min(r1['end'], r2['end'])
                    })

        return conflicts


class RulePerformanceTracker:
    """Track rule performance across documents"""

    def __init__(self):
        self.rule_stats = {}

    def record_rule_match(self, rule_id: str, matched: bool, applied: bool):
        """Record whether a rule matched and was applied"""
        if rule_id not in self.rule_stats:
            self.rule_stats[rule_id] = {
                'matches': 0,
                'applied': 0,
                'skipped': 0
            }

        if matched:
            self.rule_stats[rule_id]['matches'] += 1

        if applied:
            self.rule_stats[rule_id]['applied'] += 1
        elif matched:
            self.rule_stats[rule_id]['skipped'] += 1

    def get_stats(self) -> Dict:
        """Get performance statistics"""
        return self.rule_stats

    def get_top_rules(self, n: int = 10) -> List[tuple]:
        """Get top N most frequently matching rules"""
        sorted_rules = sorted(
            self.rule_stats.items(),
            key=lambda x: x[1]['matches'],
            reverse=True
        )
        return sorted_rules[:n]
