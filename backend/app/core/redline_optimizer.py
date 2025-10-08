"""
Smart Redline Filtering and Optimization
Reduces redline volume to focus on material issues
"""
from typing import List, Dict, Set, Tuple
from collections import defaultdict


class RedlineOptimizer:
    """Optimize redlines for maximum acceptance rate"""

    # Maximum redlines by strategy
    MAX_REDLINES = {
        'light': 5,
        'balanced': 15,
        'aggressive': 30,
        'comprehensive': 50  # For review only, not for actual submission
    }

    # Severity scores for sorting
    SEVERITY_SCORES = {
        'critical': 100,
        'high': 75,
        'moderate': 50,
        'low': 25
    }

    def filter_redlines(
        self,
        redlines: List[Dict],
        strategy: str = 'balanced',
        context: Dict = None
    ) -> List[Dict]:
        """
        Filter redlines to keep only the most important ones

        Args:
            redlines: List of all potential redlines
            strategy: Filtering strategy ('light', 'balanced', 'aggressive')
            context: Document context from ContextualAnalyzer

        Returns:
            Filtered list of redlines
        """

        if not redlines:
            return []

        # Step 1: Remove redundant redlines
        deduplicated = self._remove_redundant(redlines)

        # Step 2: Remove conflicting redlines (keep better one)
        resolved = self._resolve_conflicts(deduplicated)

        # Step 3: Sort by priority
        sorted_redlines = self._sort_by_priority(resolved)

        # Step 4: Apply strategy limit
        max_count = self.MAX_REDLINES.get(strategy, 15)
        limited = sorted_redlines[:max_count]

        # Step 5: Ensure critical issues are included
        final = self._ensure_critical_coverage(limited, sorted_redlines)

        return final

    def _remove_redundant(self, redlines: List[Dict]) -> List[Dict]:
        """Remove redlines that address the same issue"""

        seen_issues = set()
        unique_redlines = []

        for redline in redlines:
            # Create unique identifier for this issue
            issue_key = self._get_issue_key(redline)

            if issue_key not in seen_issues:
                unique_redlines.append(redline)
                seen_issues.add(issue_key)

        return unique_redlines

    def _get_issue_key(self, redline: Dict) -> Tuple:
        """Generate unique key for a redline issue"""

        clause_type = redline.get('clause_type', 'unknown')
        start = redline.get('start', 0)
        end = redline.get('end', 0)

        # Round to nearest 100 chars to catch overlaps
        start_bucket = (start // 100) * 100
        end_bucket = (end // 100) * 100

        return (clause_type, start_bucket, end_bucket)

    def _resolve_conflicts(self, redlines: List[Dict]) -> List[Dict]:
        """Resolve conflicting redlines by keeping the better one"""

        # Group overlapping redlines
        conflict_groups = self._find_overlapping_redlines(redlines)

        resolved = []
        processed = set()

        for group in conflict_groups:
            if len(group) == 1:
                # No conflict
                resolved.append(redlines[group[0]])
                processed.add(group[0])
            else:
                # Choose best redline from conflicting group
                best_idx = self._choose_best_redline([redlines[i] for i in group])
                resolved.append(redlines[group[best_idx]])
                processed.update(group)

        # Add non-conflicting redlines
        for idx, redline in enumerate(redlines):
            if idx not in processed:
                resolved.append(redline)

        return resolved

    def _find_overlapping_redlines(self, redlines: List[Dict]) -> List[List[int]]:
        """Find groups of overlapping redlines"""

        groups = []
        used = set()

        for i, redline1 in enumerate(redlines):
            if i in used:
                continue

            group = [i]
            start1 = redline1.get('start', 0)
            end1 = redline1.get('end', 0)

            for j, redline2 in enumerate(redlines[i+1:], i+1):
                if j in used:
                    continue

                start2 = redline2.get('start', 0)
                end2 = redline2.get('end', 0)

                # Check for overlap
                if not (end1 < start2 or end2 < start1):
                    group.append(j)
                    used.add(j)

            groups.append(group)
            used.add(i)

        return groups

    def _choose_best_redline(self, conflicting_redlines: List[Dict]) -> int:
        """Choose the best redline from conflicting options"""

        # Score each redline
        scores = []
        for redline in conflicting_redlines:
            score = self._calculate_redline_score(redline)
            scores.append(score)

        # Return index of best (highest score)
        return scores.index(max(scores))

    def _calculate_redline_score(self, redline: Dict) -> float:
        """Calculate overall score for a redline"""

        # Factors:
        # 1. Severity (weight: 0.4)
        severity = redline.get('severity', 'moderate')
        severity_score = self.SEVERITY_SCORES.get(severity, 50)

        # 2. Confidence (weight: 0.3)
        confidence = redline.get('confidence', 0.5) * 100

        # 3. Specificity - prefer specific over broad changes (weight: 0.2)
        text_length = len(redline.get('original_text', ''))
        specificity_score = 100 if text_length < 200 else (100 - min(text_length / 10, 80))

        # 4. Source - prefer rule-based over LLM (weight: 0.1)
        source = redline.get('source', 'llm')
        source_score = 100 if source == 'rule' else 80

        # Weighted sum
        total_score = (
            severity_score * 0.4 +
            confidence * 0.3 +
            specificity_score * 0.2 +
            source_score * 0.1
        )

        return total_score

    def _sort_by_priority(self, redlines: List[Dict]) -> List[Dict]:
        """Sort redlines by priority (most important first)"""

        def priority_key(redline):
            # Primary sort: severity
            severity = redline.get('severity', 'moderate')
            severity_score = self.SEVERITY_SCORES.get(severity, 50)

            # Secondary sort: confidence
            confidence = redline.get('confidence', 0.5)

            # Tertiary sort: text length (prefer specific changes)
            text_length = len(redline.get('original_text', ''))
            specificity = -min(text_length, 1000)  # Negative because we prefer shorter

            return (severity_score, confidence, specificity)

        return sorted(redlines, key=priority_key, reverse=True)

    def _ensure_critical_coverage(
        self,
        limited_redlines: List[Dict],
        all_sorted_redlines: List[Dict]
    ) -> List[Dict]:
        """Ensure all critical issues are included, even if over limit"""

        # Find all critical redlines
        critical_redlines = [
            r for r in all_sorted_redlines
            if r.get('severity') == 'critical'
        ]

        # Check if any critical redlines were excluded
        included_ids = {r.get('id') for r in limited_redlines}
        missing_critical = [
            r for r in critical_redlines
            if r.get('id') not in included_ids
        ]

        if missing_critical:
            # Add missing critical redlines
            return limited_redlines + missing_critical

        return limited_redlines

    def group_by_clause_type(self, redlines: List[Dict]) -> Dict[str, List[Dict]]:
        """Group redlines by clause type for organized presentation"""

        grouped = defaultdict(list)

        for redline in redlines:
            clause_type = redline.get('clause_type', 'other')
            grouped[clause_type].append(redline)

        return dict(grouped)

    def calculate_acceptance_probability(self, redlines: List[Dict]) -> float:
        """
        Estimate probability that opposing counsel will accept these redlines

        Based on:
        - Number of redlines (fewer = higher acceptance)
        - Severity mix (more moderate = higher acceptance)
        - Specificity (specific changes = higher acceptance)
        """

        if not redlines:
            return 1.0

        # Factor 1: Volume penalty (more redlines = lower acceptance)
        volume_factor = max(0.3, 1.0 - (len(redlines) / 30))

        # Factor 2: Severity mix
        severity_counts = defaultdict(int)
        for r in redlines:
            severity_counts[r.get('severity', 'moderate')] += 1

        total = len(redlines)
        severity_factor = (
            severity_counts['critical'] * 0.3 +
            severity_counts['high'] * 0.5 +
            severity_counts['moderate'] * 0.8 +
            severity_counts['low'] * 1.0
        ) / total if total > 0 else 0.5

        # Factor 3: Specificity (average text length)
        avg_length = sum(
            len(r.get('original_text', ''))
            for r in redlines
        ) / total if total > 0 else 0

        specificity_factor = max(0.3, 1.0 - (avg_length / 500))

        # Combined probability
        probability = (
            volume_factor * 0.4 +
            severity_factor * 0.4 +
            specificity_factor * 0.2
        )

        return round(probability, 2)

    def get_optimization_summary(
        self,
        original_count: int,
        filtered_count: int,
        acceptance_probability: float
    ) -> Dict:
        """Generate summary of optimization results"""

        reduction_pct = ((original_count - filtered_count) / original_count * 100) if original_count > 0 else 0

        return {
            'original_redline_count': original_count,
            'filtered_redline_count': filtered_count,
            'reduction_percentage': round(reduction_pct, 1),
            'acceptance_probability': acceptance_probability,
            'recommendation': self._get_strategy_recommendation(
                filtered_count,
                acceptance_probability
            )
        }

    def _get_strategy_recommendation(
        self,
        redline_count: int,
        acceptance_prob: float
    ) -> str:
        """Recommend strategy based on current state"""

        if redline_count <= 5 and acceptance_prob > 0.7:
            return "Excellent - focused on key issues with high acceptance probability"
        elif redline_count <= 15 and acceptance_prob > 0.5:
            return "Good balance - reasonable volume with decent acceptance odds"
        elif redline_count <= 30 and acceptance_prob > 0.3:
            return "Moderate - consider reducing further for better acceptance"
        else:
            return "Too aggressive - recommend using 'light' or 'balanced' strategy"
