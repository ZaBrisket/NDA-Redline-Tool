"""
Robust clause-to-text mapper with fuzzy matching
Handles conceptual clause descriptions from LLMs
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz
from rapidfuzz import process

logger = logging.getLogger(__name__)


class ClauseMapper:
    """
    Maps conceptual clause descriptions to specific text positions in documents.
    Uses fuzzy matching and anchor heuristics for robust mapping.
    """

    def __init__(self, confidence_threshold: float = 80.0):
        """
        Initialize the ClauseMapper.

        Args:
            confidence_threshold: Minimum confidence score (0-100) for accepting a match
        """
        self.confidence_threshold = confidence_threshold
        self.stats = {
            'total_attempts': 0,
            'successful_matches': 0,
            'fuzzy_matches': 0,
            'exact_matches': 0,
            'failed_matches': 0,
            'average_confidence': 0.0
        }

    def map_clause_to_position(
        self,
        clause_description: str,
        document_text: str,
        indexer=None
    ) -> Optional[Tuple[int, int, str, float]]:
        """
        Map a clause description to a position in the document.

        Args:
            clause_description: Description or partial text of the clause
            document_text: Full document text
            indexer: Optional WorkingTextIndexer for structural awareness

        Returns:
            Tuple of (start_pos, end_pos, matched_text, confidence) or None if not found
        """
        self.stats['total_attempts'] += 1

        if not clause_description or not document_text:
            self.stats['failed_matches'] += 1
            return None

        # Clean up the clause description
        clause_clean = clause_description.strip()

        # Strategy 1: Try exact match first
        exact_match = self._try_exact_match(clause_clean, document_text)
        if exact_match:
            self.stats['successful_matches'] += 1
            self.stats['exact_matches'] += 1
            return exact_match

        # Strategy 2: Try case-insensitive match
        case_insensitive_match = self._try_case_insensitive_match(clause_clean, document_text)
        if case_insensitive_match:
            self.stats['successful_matches'] += 1
            self.stats['exact_matches'] += 1
            return case_insensitive_match

        # Strategy 3: Extract key phrases and try fuzzy matching
        fuzzy_match = self._try_fuzzy_match(clause_clean, document_text)
        if fuzzy_match and fuzzy_match[3] >= self.confidence_threshold:
            self.stats['successful_matches'] += 1
            self.stats['fuzzy_matches'] += 1
            return fuzzy_match

        # Strategy 4: Try to find by clause title/header
        if indexer:
            header_match = self._try_header_match(clause_clean, document_text, indexer)
            if header_match:
                self.stats['successful_matches'] += 1
                self.stats['fuzzy_matches'] += 1
                return header_match

        # Strategy 5: Try partial match with first/last sentences
        anchor_match = self._try_anchor_match(clause_clean, document_text)
        if anchor_match and anchor_match[3] >= self.confidence_threshold:
            self.stats['successful_matches'] += 1
            self.stats['fuzzy_matches'] += 1
            return anchor_match

        self.stats['failed_matches'] += 1
        logger.warning(
            f"Could not map clause to document position",
            clause_preview=clause_clean[:100],
            strategies_tried=5
        )
        return None

    def _try_exact_match(self, clause: str, document: str) -> Optional[Tuple[int, int, str, float]]:
        """Try exact substring match"""
        pos = document.find(clause)
        if pos >= 0:
            return (pos, pos + len(clause), clause, 100.0)
        return None

    def _try_case_insensitive_match(self, clause: str, document: str) -> Optional[Tuple[int, int, str, float]]:
        """Try case-insensitive match"""
        doc_lower = document.lower()
        clause_lower = clause.lower()
        pos = doc_lower.find(clause_lower)
        if pos >= 0:
            actual_text = document[pos:pos + len(clause)]
            return (pos, pos + len(clause), actual_text, 95.0)
        return None

    def _try_fuzzy_match(self, clause: str, document: str) -> Optional[Tuple[int, int, str, float]]:
        """
        Try fuzzy matching using token sort ratio.
        Splits document into paragraphs and finds best match.
        """
        # Split document into paragraphs or reasonable chunks
        paragraphs = self._split_into_chunks(document)

        if not paragraphs:
            return None

        # Find the best matching paragraph
        best_match = process.extractOne(
            clause,
            paragraphs,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=self.confidence_threshold
        )

        if best_match:
            matched_text, confidence, idx = best_match
            # Find the position of this paragraph in the document
            pos = document.find(matched_text)
            if pos >= 0:
                return (pos, pos + len(matched_text), matched_text, confidence)

        return None

    def _try_header_match(self, clause: str, document: str, indexer) -> Optional[Tuple[int, int, str, float]]:
        """
        Try to match by clause title/header.
        Useful when LLM provides clause descriptions like "Non-Solicitation..."
        """
        # Extract potential header from clause description
        header_patterns = [
            r'^([A-Z][A-Za-z\s\-]+)[:.]',  # "Non-Solicitation:"
            r'^(\d+\.?\s*[A-Z][A-Za-z\s\-]+)',  # "1. Confidentiality"
            r'^([A-Z\s]+)[\s\-]',  # "CONFIDENTIALITY -"
        ]

        for pattern in header_patterns:
            match = re.match(pattern, clause)
            if match:
                header = match.group(1).strip()
                # Try to find this header in the document
                header_pos = self._find_header_position(header, document)
                if header_pos:
                    return header_pos

        return None

    def _try_anchor_match(self, clause: str, document: str) -> Optional[Tuple[int, int, str, float]]:
        """
        Try matching using first/last sentence anchors.
        Useful when clause description includes key phrases.
        """
        # Extract first 50-100 characters as anchor
        anchor_length = min(100, len(clause) // 2)
        if len(clause) > anchor_length:
            first_anchor = clause[:anchor_length]
            last_anchor = clause[-anchor_length:]

            # Try fuzzy match with anchors
            chunks = self._split_into_chunks(document, chunk_size=500)

            # Try first anchor
            best_match = process.extractOne(
                first_anchor,
                chunks,
                scorer=fuzz.partial_ratio,
                score_cutoff=70
            )

            if best_match:
                matched_text, confidence, idx = best_match
                pos = document.find(matched_text)
                if pos >= 0:
                    return (pos, pos + len(matched_text), matched_text, confidence)

            # Try last anchor
            best_match = process.extractOne(
                last_anchor,
                chunks,
                scorer=fuzz.partial_ratio,
                score_cutoff=70
            )

            if best_match:
                matched_text, confidence, idx = best_match
                pos = document.find(matched_text)
                if pos >= 0:
                    return (pos, pos + len(matched_text), matched_text, confidence)

        return None

    def _split_into_chunks(self, document: str, chunk_size: int = 300) -> List[str]:
        """
        Split document into manageable chunks for fuzzy matching.
        Tries to split on paragraph boundaries when possible.
        """
        # First try to split by paragraphs
        paragraphs = re.split(r'\n\n+', document)

        chunks = []
        for para in paragraphs:
            if len(para) <= chunk_size:
                if para.strip():  # Skip empty paragraphs
                    chunks.append(para)
            else:
                # Split large paragraphs into sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) <= chunk_size:
                        current_chunk += " " + sent if current_chunk else sent
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sent
                if current_chunk:
                    chunks.append(current_chunk)

        return chunks

    def _find_header_position(self, header: str, document: str) -> Optional[Tuple[int, int, str, float]]:
        """Find a header/title in the document with fuzzy matching"""
        # Look for the header with various formatting
        patterns = [
            f"{header}",
            f"{header}:",
            f"{header}.",
            f"{header} -",
            f"\\b{re.escape(header)}\\b"
        ]

        for pattern in patterns:
            matches = list(re.finditer(pattern, document, re.IGNORECASE))
            if matches:
                match = matches[0]
                # Find the end of this section (next header or paragraph break)
                section_end = self._find_section_end(document, match.end())
                section_text = document[match.start():section_end]
                return (match.start(), section_end, section_text, 90.0)

        return None

    def _find_section_end(self, document: str, start_pos: int) -> int:
        """Find the end of a section starting from a position"""
        # Look for next header or double newline
        next_header = re.search(
            r'\n\n+\d*\.?\s*[A-Z][A-Za-z\s\-]+[:.]',
            document[start_pos:]
        )

        if next_header:
            return start_pos + next_header.start()

        # Look for double newline
        next_break = document.find('\n\n', start_pos)
        if next_break >= 0:
            return next_break

        # Default to next 500 characters or end of document
        return min(start_pos + 500, len(document))

    def get_stats(self) -> Dict:
        """Get mapping statistics"""
        if self.stats['successful_matches'] > 0:
            self.stats['average_confidence'] = (
                self.stats['average_confidence'] / self.stats['successful_matches']
            )

        return {
            'total_attempts': self.stats['total_attempts'],
            'successful_matches': self.stats['successful_matches'],
            'success_rate': (
                self.stats['successful_matches'] / self.stats['total_attempts'] * 100
                if self.stats['total_attempts'] > 0 else 0
            ),
            'exact_matches': self.stats['exact_matches'],
            'fuzzy_matches': self.stats['fuzzy_matches'],
            'failed_matches': self.stats['failed_matches'],
            'average_confidence': self.stats['average_confidence']
        }

    def convert_redlines_with_mapping(
        self,
        claude_redlines: List[Dict],
        document_text: str,
        indexer=None
    ) -> Tuple[List[Dict], Dict]:
        """
        Convert Claude's conceptual redlines to document position format.

        Args:
            claude_redlines: List of redlines from Claude
            document_text: Full document text
            indexer: Optional WorkingTextIndexer

        Returns:
            Tuple of (converted_redlines, conversion_stats)
        """
        converted = []
        stats = {
            'total': len(claude_redlines),
            'converted': 0,
            'already_formatted': 0,
            'failed': 0,
            'confidence_scores': []
        }

        for redline in claude_redlines:
            # Check if already in correct format
            if all(key in redline for key in ['start', 'end', 'original_text']):
                converted.append(redline)
                stats['already_formatted'] += 1
                continue

            # Try to map the clause
            clause_text = redline.get('clause', '') or redline.get('original_text', '')

            if not clause_text:
                logger.warning("Redline missing clause text", redline=redline)
                stats['failed'] += 1
                continue

            # Use the mapper to find position
            match_result = self.map_clause_to_position(clause_text, document_text, indexer)

            if match_result:
                start, end, matched_text, confidence = match_result

                converted.append({
                    'start': start,
                    'end': end,
                    'original_text': matched_text,
                    'revised_text': redline.get('recommendation', '') or redline.get('revised_text', ''),
                    'severity': redline.get('severity', 'moderate'),
                    'explanation': redline.get('issue', '') or redline.get('explanation', ''),
                    'clause_type': redline.get('clause_type', 'llm_identified'),
                    'source': 'claude',
                    'confidence': confidence,
                    'original_confidence': redline.get('confidence', 85)
                })

                stats['converted'] += 1
                stats['confidence_scores'].append(confidence)

                logger.debug(
                    f"Successfully mapped clause to position",
                    confidence=confidence,
                    clause_preview=clause_text[:50]
                )
            else:
                logger.warning(
                    f"Failed to map clause to document position",
                    clause_preview=clause_text[:100]
                )
                stats['failed'] += 1

        # Calculate average confidence
        if stats['confidence_scores']:
            stats['average_confidence'] = sum(stats['confidence_scores']) / len(stats['confidence_scores'])
        else:
            stats['average_confidence'] = 0

        # Log summary
        logger.info(
            f"Clause mapping complete",
            total=stats['total'],
            converted=stats['converted'],
            already_formatted=stats['already_formatted'],
            failed=stats['failed'],
            average_confidence=stats['average_confidence']
        )

        return converted, stats