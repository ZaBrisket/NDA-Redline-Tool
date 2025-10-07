"""
TrackChangesEngine - Generate Microsoft Word-compatible tracked revisions
Manipulates OXML (Open XML) directly to create w:del and w:ins elements
"""
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from lxml import etree
from datetime import datetime
from typing import List, Dict, Optional
from .text_indexer import WorkingTextIndexer, TextMapping
import uuid


class TrackChangesEngine:
    """
    Apply track changes at the OXML level for Word compatibility.

    Creates proper w:del and w:ins elements with:
    - Author attribution
    - Timestamps
    - Unique revision IDs
    - Preserved formatting
    """

    def __init__(self, author: str = "ndaOK"):
        self.author = author
        self.revision_id = 1
        self.timestamp = datetime.now().isoformat()

    def apply_deletion(self, paragraph, run, text_to_delete: str) -> bool:
        """
        Wrap run text in w:del element for track changes deletion.

        Args:
            paragraph: The paragraph containing the run
            run: The specific run to mark as deleted
            text_to_delete: The text to delete (for verification)

        Returns:
            bool: Success status
        """
        try:
            p_elem = paragraph._element
            r_elem = run._element

            # Create w:del element
            del_elem = parse_xml(
                f'<w:del xmlns:w="{qn("w")}" '
                f'w:id="{self.revision_id}" '
                f'w:author="{self.author}" '
                f'w:date="{self.timestamp}"/>'
            )

            # Find the run in the paragraph and wrap it
            run_index = None
            for i, child in enumerate(p_elem):
                if child == r_elem:
                    run_index = i
                    break

            if run_index is not None:
                # Remove the run from paragraph
                p_elem.remove(r_elem)

                # Add run to del element
                del_elem.append(r_elem)

                # Insert del element where run was
                p_elem.insert(run_index, del_elem)

                self.revision_id += 1
                return True

        except Exception as e:
            print(f"Error applying deletion: {e}")
            return False

        return False

    def apply_insertion(self, paragraph, position_run, new_text: str, insert_before: bool = False) -> bool:
        """
        Insert new text with w:ins element for track changes.

        Args:
            paragraph: The paragraph to insert into
            position_run: The run to use as position reference
            new_text: The text to insert
            insert_before: If True, insert before position_run; else after

        Returns:
            bool: Success status
        """
        try:
            p_elem = paragraph._element

            # Create new run with the text
            new_run = parse_xml(
                f'<w:r xmlns:w="{qn("w")}">'
                f'<w:t xml:space="preserve">{self._escape_xml(new_text)}</w:t>'
                f'</w:r>'
            )

            # Create w:ins element
            ins_elem = parse_xml(
                f'<w:ins xmlns:w="{qn("w")}" '
                f'w:id="{self.revision_id}" '
                f'w:author="{self.author}" '
                f'w:date="{self.timestamp}"/>'
            )

            # Add run to ins element
            ins_elem.append(new_run)

            # Find position and insert
            if position_run is not None:
                r_elem = position_run._element
                run_index = None

                for i, child in enumerate(p_elem):
                    if child == r_elem:
                        run_index = i
                        break

                if run_index is not None:
                    if insert_before:
                        p_elem.insert(run_index, ins_elem)
                    else:
                        p_elem.insert(run_index + 1, ins_elem)

                    self.revision_id += 1
                    return True
            else:
                # No position run, append to end
                p_elem.append(ins_elem)
                self.revision_id += 1
                return True

        except Exception as e:
            print(f"Error applying insertion: {e}")
            return False

        return False

    def apply_replacement(self, paragraph, run, old_text: str, new_text: str) -> bool:
        """
        Replace text by applying both deletion and insertion.

        This creates the typical "strikethrough old + underline new" effect
        that users see in Word track changes.
        """
        try:
            p_elem = paragraph._element
            r_elem = run._element

            # Find run index
            run_index = None
            for i, child in enumerate(p_elem):
                if child == r_elem:
                    run_index = i
                    break

            if run_index is None:
                return False

            # Create deletion element with original run
            del_elem = parse_xml(
                f'<w:del xmlns:w="{qn("w")}" '
                f'w:id="{self.revision_id}" '
                f'w:author="{self.author}" '
                f'w:date="{self.timestamp}"/>'
            )

            self.revision_id += 1

            # Create insertion element with new text
            new_run = parse_xml(
                f'<w:r xmlns:w="{qn("w")}">'
                f'<w:t xml:space="preserve">{self._escape_xml(new_text)}</w:t>'
                f'</w:r>'
            )

            ins_elem = parse_xml(
                f'<w:ins xmlns:w="{qn("w")}" '
                f'w:id="{self.revision_id}" '
                f'w:author="{self.author}" '
                f'w:date="{self.timestamp}"/>'
            )

            self.revision_id += 1

            # Remove original run
            p_elem.remove(r_elem)

            # Add run to del element
            del_elem.append(r_elem)

            # Add new run to ins element
            ins_elem.append(new_run)

            # Insert both elements
            p_elem.insert(run_index, del_elem)
            p_elem.insert(run_index + 1, ins_elem)

            return True

        except Exception as e:
            print(f"Error applying replacement: {e}")
            return False

    def apply_redline(self, doc: Document, indexer: WorkingTextIndexer, redline: Dict) -> bool:
        """
        Apply a single redline to the document using the indexer.

        Args:
            doc: The Word document
            indexer: WorkingTextIndexer with mappings
            redline: Dict with 'start', 'end', 'original_text', 'revised_text'

        Returns:
            bool: Success status
        """
        try:
            start = redline['start']
            end = redline['end']
            original_text = redline['original_text']
            revised_text = redline.get('revised_text', '')

            # Find the DOCX location(s) for this text span
            mappings = indexer.find_spans(start, end)

            if not mappings:
                print(f"No mappings found for span [{start}:{end}]")
                return False

            # Handle different cases
            if not revised_text or revised_text.strip() == '':
                # Pure deletion
                for mapping in mappings:
                    paragraph, run = indexer.get_paragraph_and_run(mapping)
                    if paragraph and run:
                        self.apply_deletion(paragraph, run, original_text)

            elif not original_text or original_text.strip() == '':
                # Pure insertion
                mapping = mappings[0]
                paragraph, run = indexer.get_paragraph_and_run(mapping)
                if paragraph:
                    self.apply_insertion(paragraph, run, revised_text, insert_before=False)

            else:
                # Replacement
                # For simplicity, apply to the first mapping
                mapping = mappings[0]
                paragraph, run = indexer.get_paragraph_and_run(mapping)
                if paragraph and run:
                    self.apply_replacement(paragraph, run, original_text, revised_text)

            return True

        except Exception as e:
            print(f"Error applying redline: {e}")
            return False

    def apply_all_redlines(self, doc: Document, indexer: WorkingTextIndexer, redlines: List[Dict]) -> int:
        """
        Apply multiple redlines to document.

        Args:
            doc: The Word document
            indexer: WorkingTextIndexer with mappings
            redlines: List of redline dicts

        Returns:
            int: Number of successfully applied redlines
        """
        # Sort redlines by position (reverse order to avoid index shifting)
        sorted_redlines = sorted(redlines, key=lambda r: r['start'], reverse=True)

        success_count = 0
        for redline in sorted_redlines:
            if self.apply_redline(doc, indexer, redline):
                success_count += 1

        return success_count

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape special XML characters"""
        if not text:
            return ""

        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')

        return text

    def enable_track_changes(self, doc: Document):
        """Enable track changes in document settings"""
        try:
            # Access document settings
            settings = doc.settings
            settings_elem = settings.element

            # Check if trackRevisions already exists
            track_revisions = settings_elem.find(qn('w:trackRevisions'))

            if track_revisions is None:
                # Add track changes setting
                track_elem = parse_xml(f'<w:trackRevisions xmlns:w="{qn("w")}"/>')
                settings_elem.append(track_elem)

        except Exception as e:
            print(f"Error enabling track changes: {e}")


class RedlineValidator:
    """Validate redlines before applying"""

    @staticmethod
    def validate_redline(redline: Dict, working_text: str) -> bool:
        """Check if a redline is valid"""
        required_fields = ['start', 'end', 'original_text']

        for field in required_fields:
            if field not in redline:
                return False

        start = redline['start']
        end = redline['end']

        # Check bounds
        if start < 0 or end > len(working_text):
            return False

        if start >= end:
            return False

        # Verify original text matches
        actual_text = working_text[start:end]
        expected_text = redline['original_text']

        # Normalize for comparison
        actual_norm = actual_text.strip().lower()
        expected_norm = expected_text.strip().lower()

        if actual_norm != expected_norm:
            # Allow fuzzy match within 20% difference
            from difflib import SequenceMatcher
            ratio = SequenceMatcher(None, actual_norm, expected_norm).ratio()
            if ratio < 0.8:
                print(f"Text mismatch: expected '{expected_text}' but found '{actual_text}'")
                return False

        return True

    @staticmethod
    def validate_all(redlines: List[Dict], working_text: str) -> List[Dict]:
        """Filter to only valid redlines"""
        valid = []

        for redline in redlines:
            if RedlineValidator.validate_redline(redline, working_text):
                valid.append(redline)
            else:
                print(f"Invalid redline skipped: {redline.get('clause_type', 'unknown')}")

        return valid
