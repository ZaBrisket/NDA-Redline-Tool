"""
Contextual Intelligence Analyzer
Analyzes existing document terms to determine what's already reasonable
"""
import re
from typing import Dict, Optional, List, Tuple
from enum import Enum


class DocumentType(Enum):
    """Types of NDAs"""
    MUTUAL = "mutual"
    ONE_WAY = "one_way"
    MULTI_PARTY = "multi_party"


class ContextualAnalyzer:
    """Analyze document context before applying redline rules"""

    # Market standard ranges (in months)
    TERM_RANGES = {
        'ideal': (18, 24),
        'acceptable': (12, 36),
        'unreasonable_low': (0, 12),
        'unreasonable_high': (60, float('inf'))
    }

    NON_SOLICIT_RANGES = {
        'ideal': (6, 12),
        'acceptable': (3, 24),
        'unreasonable_low': (0, 3),
        'unreasonable_high': (36, float('inf'))
    }

    PREFERRED_JURISDICTIONS = [
        'Delaware', 'New York', 'California',
        'Texas', 'Illinois', 'Massachusetts'
    ]

    def analyze_existing_terms(self, working_text: str) -> Dict:
        """
        Identify what reasonable terms already exist in the document

        Returns dict with analysis of existing provisions
        """

        first_1000_chars = working_text[:1000].lower()

        existing_terms = {
            'term_length_months': self._extract_term_length(working_text),
            'governing_law': self._extract_governing_law(working_text),
            'has_retention_carveout': self._has_retention_exception(working_text),
            'non_solicit_exceptions': self._count_non_solicit_exceptions(working_text),
            'non_solicit_duration_months': self._extract_non_solicit_duration(working_text),
            'is_mutual': 'mutual' in first_1000_chars or 'each party' in first_1000_chars,
            'document_type': self._identify_nda_type(working_text),
            'has_return_provision': self._has_return_provision(working_text),
            'geographic_scope': self._extract_geographic_scope(working_text)
        }

        # Add reasonableness assessments
        existing_terms['term_is_reasonable'] = self._is_term_reasonable(
            existing_terms['term_length_months']
        )
        existing_terms['jurisdiction_is_reasonable'] = (
            existing_terms['governing_law'] in self.PREFERRED_JURISDICTIONS
        )
        existing_terms['non_solicit_is_reasonable'] = self._is_non_solicit_reasonable(
            existing_terms['non_solicit_duration_months']
        )

        return existing_terms

    def _extract_term_length(self, text: str) -> Optional[int]:
        """Extract existing confidentiality term in months"""

        # Pattern for years
        year_patterns = [
            r'(?:expire|term of|period of|for)\s+(?:a\s+period\s+of\s+)?(\d+)\s*years?',
            r'(\d+)\s*years?\s+(?:from|after|following)',
            r'(\d+)[-\s]*year\s+(?:term|period)',
        ]

        for pattern in year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                years = int(match.group(1))
                return years * 12  # Convert to months

        # Pattern for months
        month_patterns = [
            r'(?:expire|term of|period of|for)\s+(\d+)\s*months?',
            r'(\d+)\s*months?\s+(?:from|after|following)',
        ]

        for pattern in month_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        # Check for perpetual/indefinite (red flag)
        if re.search(r'\b(?:perpetual|indefinite|no\s+expir)', text, re.IGNORECASE):
            return 999  # Flag as unreasonably long

        return None

    def _extract_governing_law(self, text: str) -> Optional[str]:
        """Extract governing law jurisdiction"""

        patterns = [
            r'governed?\s+by\s+(?:the\s+)?laws?\s+of\s+(?:the\s+)?(?:State\s+of\s+)?(\w+)',
            r'laws?\s+of\s+(?:the\s+)?(?:State\s+of\s+)?(\w+)\s+(?:shall\s+)?govern',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                jurisdiction = match.group(1).strip()
                # Normalize common variations
                if jurisdiction.lower() in ['delaware', 'de']:
                    return 'Delaware'
                elif jurisdiction.lower() in ['new york', 'ny']:
                    return 'New York'
                elif jurisdiction.lower() in ['california', 'ca']:
                    return 'California'
                return jurisdiction.title()

        return None

    def _has_retention_exception(self, text: str) -> bool:
        """Check if document has reasonable retention exception"""

        retention_keywords = [
            r'retain.*?(?:copy|copies|record)',
            r'keep.*?(?:copy|copies|record)',
            r'file.*?retention',
            r'regulatory.*?requirement',
            r'legal.*?requirement',
            r'archival.*?(?:purpose|copy)'
        ]

        for keyword in retention_keywords:
            if re.search(keyword, text, re.IGNORECASE):
                return True

        return False

    def _count_non_solicit_exceptions(self, text: str) -> int:
        """Count number of non-solicitation exceptions present"""

        exceptions = {
            'general_advertising': r'general\s+(?:public\s+)?advertis',
            'employee_initiated': r'employee.*?initiat|initiat.*?employee',
            'prior_discussions': r'prior.*?(?:discuss|contact)|discuss.*?prior',
            'terminated_employees': r'(?:terminated|former).*?employee'
        }

        count = 0
        for exception_type, pattern in exceptions.items():
            if re.search(pattern, text, re.IGNORECASE):
                count += 1

        return count

    def _extract_non_solicit_duration(self, text: str) -> Optional[int]:
        """Extract non-solicitation duration in months"""

        # Look for non-solicit section
        non_solicit_section = re.search(
            r'(?:non[-\s]?solicitation|employee.*?solicitation).{0,500}',
            text,
            re.IGNORECASE | re.DOTALL
        )

        if not non_solicit_section:
            return None

        section_text = non_solicit_section.group(0)

        # Extract duration
        year_match = re.search(r'(\d+)\s*years?', section_text)
        if year_match:
            return int(year_match.group(1)) * 12

        month_match = re.search(r'(\d+)\s*months?', section_text)
        if month_match:
            return int(month_match.group(1))

        return None

    def _identify_nda_type(self, text: str) -> DocumentType:
        """Identify if NDA is mutual, one-way, or multi-party"""

        first_1000 = text[:1000].lower()

        if 'mutual' in first_1000 or 'each party' in first_1000:
            return DocumentType.MUTUAL
        elif 'three' in first_1000 or 'multiple part' in first_1000:
            return DocumentType.MULTI_PARTY
        else:
            return DocumentType.ONE_WAY

    def _has_return_provision(self, text: str) -> bool:
        """Check if document has return/destruction provision"""

        return_keywords = [
            r'return.*?(?:confidential|material)',
            r'destroy.*?(?:confidential|material)',
            r'(?:return|destruct).*?(?:upon|within).*?(?:request|termination)'
        ]

        for keyword in return_keywords:
            if re.search(keyword, text, re.IGNORECASE):
                return True

        return False

    def _extract_geographic_scope(self, text: str) -> Optional[str]:
        """Extract geographic scope of restrictions"""

        geo_patterns = [
            r'(?:within|in)\s+(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:where|in which)',
            r'geographic.*?(?:area|scope|region).*?(\w+(?:\s+\w+)?)',
        ]

        for pattern in geo_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Check for worldwide
        if re.search(r'\b(?:worldwide|globally|international)', text, re.IGNORECASE):
            return 'Worldwide'

        return None

    def _is_term_reasonable(self, term_months: Optional[int]) -> bool:
        """Determine if confidentiality term is reasonable"""

        if term_months is None:
            return False

        # Acceptable range: 12-36 months (1-3 years)
        acceptable_min, acceptable_max = self.TERM_RANGES['acceptable']
        return acceptable_min <= term_months <= acceptable_max

    def _is_non_solicit_reasonable(self, duration_months: Optional[int]) -> bool:
        """Determine if non-solicitation duration is reasonable"""

        if duration_months is None:
            return True  # No non-solicit is fine

        # Acceptable range: 3-24 months
        acceptable_min, acceptable_max = self.NON_SOLICIT_RANGES['acceptable']
        return acceptable_min <= duration_months <= acceptable_max

    def should_apply_rule(self, rule: Dict, context: Dict) -> bool:
        """
        Determine if a rule should be applied based on existing context

        Args:
            rule: The redline rule to potentially apply
            context: Analyzed context from analyze_existing_terms()

        Returns:
            True if rule should be applied, False if existing term is acceptable
        """

        rule_type = rule.get('type') or rule.get('clause_type')

        # Don't change reasonable confidentiality terms (12-36 months)
        if rule_type == 'confidentiality_term':
            if context.get('term_is_reasonable'):
                return False  # Term is already in acceptable range

        # Don't change if governing law is already a preferred jurisdiction
        if rule_type == 'governing_law':
            if context.get('jurisdiction_is_reasonable'):
                return False

        # Don't modify non-solicit if duration is already reasonable
        if rule_type == 'employee_solicitation':
            if context.get('non_solicit_is_reasonable'):
                # Only add missing exceptions, don't rewrite whole clause
                existing_exceptions = context.get('non_solicit_exceptions', 0)
                if existing_exceptions >= 2:  # Has at least 2 exceptions
                    return False

        # Don't add return provision if one already exists
        if rule_type == 'return_destruction':
            if context.get('has_return_provision'):
                return False

        # Don't add retention carveout if one already exists
        if rule_type == 'retention_exception':
            if context.get('has_retention_carveout'):
                return False

        return True  # Apply the rule

    def get_context_summary(self, context: Dict) -> str:
        """Generate human-readable summary of context analysis"""

        term_months = context.get('term_length_months')
        term_years = term_months / 12 if term_months else None

        summary_parts = []

        if term_years:
            reasonableness = "reasonable" if context.get('term_is_reasonable') else "unreasonable"
            summary_parts.append(f"Confidentiality term: {term_years:.1f} years ({reasonableness})")

        if context.get('governing_law'):
            summary_parts.append(f"Governing law: {context['governing_law']}")

        if context.get('is_mutual'):
            summary_parts.append("Type: Mutual NDA")

        non_solicit_exceptions = context.get('non_solicit_exceptions', 0)
        if non_solicit_exceptions > 0:
            summary_parts.append(f"Non-solicit exceptions: {non_solicit_exceptions}")

        return " | ".join(summary_parts) if summary_parts else "No key terms identified"
