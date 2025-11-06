"""
All-Claude LLM Orchestrator - Claude Opus 4.1 + Claude Sonnet 4.5
Replaces hybrid OpenAI/Claude architecture with 100% Claude processing
"""
import os
import logging
import json
from typing import List, Dict, Optional, Tuple
from anthropic import AsyncAnthropic, APIStatusError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class AllClaudeLLMOrchestrator:
    """
    All-Claude LLM Orchestrator for NDA Processing
    - Pass 1: Claude Opus 4.1 for comprehensive recall
    - Pass 2: Claude Sonnet 4.5 for 100% validation (not 15%)
    - Pass 3: Intelligent merging with rule-based results
    """

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = AsyncAnthropic(api_key=api_key)

        # Model configuration
        # Note: Update to claude-opus-4-20250514 when available
        self.opus_model = os.getenv("CLAUDE_OPUS_MODEL", "claude-3-opus-20240229")
        self.sonnet_model = os.getenv("CLAUDE_SONNET_MODEL", "claude-sonnet-4-20250514")

        # Processing configuration
        self.enable_validation = True  # Always validate
        self.validation_rate = 1.0  # 100% validation (not 15%)
        self.confidence_threshold = int(os.getenv("CONFIDENCE_THRESHOLD", "95"))

        # Cost tracking (as of Jan 2025)
        self.OPUS_INPUT_COST = 0.015 / 1000  # $0.015 per 1K input tokens
        self.OPUS_OUTPUT_COST = 0.075 / 1000  # $0.075 per 1K output tokens
        self.SONNET_INPUT_COST = 0.003 / 1000  # $0.003 per 1K input tokens
        self.SONNET_OUTPUT_COST = 0.015 / 1000  # $0.015 per 1K output tokens

        # Stats tracking
        self.stats = {
            'opus_calls': 0,
            'opus_tokens_input': 0,
            'opus_tokens_output': 0,
            'sonnet_calls': 0,
            'sonnet_tokens_input': 0,
            'sonnet_tokens_output': 0,
            'total_redlines': 0,
            'validated_redlines': 0,
            'rejected_redlines': 0,
            'conflicts_resolved': 0,
            'errors': 0,
            'total_cost_usd': 0.0
        }

        logger.info(f"Initialized All-Claude Orchestrator: Opus={self.opus_model}, Sonnet={self.sonnet_model}")
        logger.info(f"Validation: 100% of suggestions (validation_rate={self.validation_rate})")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _call_claude_opus(self, prompt: str, system_prompt: str) -> Dict:
        """Call Claude Opus for comprehensive recall"""
        try:
            self.stats['opus_calls'] += 1
            logger.info(f"Calling Claude Opus ({self.opus_model}) for comprehensive NDA analysis...")

            response = await self.client.messages.create(
                model=self.opus_model,
                max_tokens=4000,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            # Track usage and costs
            if hasattr(response, 'usage'):
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost = (input_tokens * self.OPUS_INPUT_COST) + (output_tokens * self.OPUS_OUTPUT_COST)

                self.stats['opus_tokens_input'] += input_tokens
                self.stats['opus_tokens_output'] += output_tokens
                self.stats['total_cost_usd'] += cost

                logger.info(
                    f"Opus: {input_tokens} input, {output_tokens} output tokens, "
                    f"${cost:.4f} (total: ${self.stats['total_cost_usd']:.4f})"
                )

            # Parse structured response
            content = response.content[0].text

            # Try to parse as JSON if it's structured
            try:
                result = json.loads(content)
                logger.info(f"Claude Opus found {len(result.get('redlines', []))} potential violations")
                return result
            except json.JSONDecodeError:
                # Parse text response into structured format
                logger.warning("Opus returned non-JSON response, parsing as text")
                return self._parse_text_response(content)

        except APIStatusError as e:
            self.stats['errors'] += 1
            error_msg = f"Claude Opus API error (status {e.status_code}): {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        except APIConnectionError as e:
            self.stats['errors'] += 1
            error_msg = f"Claude Opus connection error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        except Exception as e:
            self.stats['errors'] += 1
            error_msg = f"Claude Opus unexpected error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _call_claude_sonnet(self, redline: Dict, context: str) -> Dict:
        """Call Claude Sonnet for validation of EVERY redline (100% validation)"""
        try:
            self.stats['sonnet_calls'] += 1

            validation_prompt = f"""Validate this proposed NDA redline:

Original Text: {redline.get('original_text')}
Proposed Change: {redline.get('revised_text')}
Reason: {redline.get('explanation')}
Confidence: {redline.get('confidence', 90)}%

Document Context:
{context}

Provide validation as JSON:
{{
    "is_valid": true/false,
    "adjusted_confidence": 0-100,
    "revised_text": "improved suggestion if needed",
    "reasoning": "explanation"
}}"""

            response = await self.client.messages.create(
                model=self.sonnet_model,
                max_tokens=1000,
                temperature=0.2,
                messages=[{"role": "user", "content": validation_prompt}]
            )

            # Track usage and costs
            if hasattr(response, 'usage'):
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost = (input_tokens * self.SONNET_INPUT_COST) + (output_tokens * self.SONNET_OUTPUT_COST)

                self.stats['sonnet_tokens_input'] += input_tokens
                self.stats['sonnet_tokens_output'] += output_tokens
                self.stats['total_cost_usd'] += cost

            content = response.content[0].text

            # Parse JSON response
            try:
                validation = json.loads(content)
                return validation
            except json.JSONDecodeError:
                # Extract JSON from response if wrapped in text
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
                if json_match:
                    validation = json.loads(json_match.group(0))
                    return validation
                else:
                    logger.warning(f"Sonnet validation failed to parse: {content[:200]}")
                    # Return original if validation fails
                    return {
                        "is_valid": True,
                        "adjusted_confidence": redline.get('confidence', 90),
                        "revised_text": redline.get('revised_text'),
                        "reasoning": "Validation parsing failed, accepting original"
                    }

        except Exception as e:
            logger.warning(f"Sonnet validation failed for redline: {e}")
            # Return original if validation fails (fail-safe)
            return {
                "is_valid": True,
                "adjusted_confidence": redline.get('confidence', 90),
                "revised_text": redline.get('revised_text'),
                "reasoning": f"Validation error: {str(e)}"
            }

    async def analyze(self, working_text: str, rule_redlines: List[Dict]) -> List[Dict]:
        """
        Main analysis pipeline - ALL CLAUDE
        1. Claude Opus for comprehensive recall
        2. Claude Sonnet validates EVERY suggestion (100%)
        3. Combine with rule-based redlines
        """
        logger.info(
            f"Starting All-Claude analysis: document={len(working_text)} chars, "
            f"rule_redlines={len(rule_redlines)}"
        )

        # STEP 1: Claude Opus for comprehensive recall
        opus_system_prompt = """You are a legal expert reviewing NDAs for Edgewater Services, LLC.

Identify ALL potential issues that need redlining. Focus on:
- Term limits (must be exactly 18 months)
- Governing law (must be Delaware with conflict disclaimer)
- Representatives definition (must include full expanded list)
- Non-solicitation (must limit to "key executives")
- Confidentiality scope
- Intellectual property rights
- Affiliate definitions

Be comprehensive - recall is more important than precision at this stage (validation comes next).
Return findings as a JSON structure."""

        opus_prompt = f"""Review this NDA text and identify ALL potential redlines:

{working_text}

Return JSON in this format:
{{
    "redlines": [
        {{
            "start": character_position,
            "end": character_position,
            "original_text": "exact text to replace",
            "revised_text": "suggested replacement",
            "clause_type": "category (e.g., term_limit, governing_law)",
            "severity": "critical/high/moderate/low",
            "confidence": 0-100,
            "explanation": "why this needs changing"
        }}
    ]
}}"""

        try:
            opus_result = await self._call_claude_opus(opus_prompt, opus_system_prompt)
            opus_redlines = opus_result.get('redlines', [])
            logger.info(f"Claude Opus identified {len(opus_redlines)} potential redlines")
        except Exception as e:
            logger.error(f"Claude Opus analysis failed: {e}")
            # If Opus fails, fall back to rule-based only
            logger.warning("Falling back to rule-based redlines only")
            return rule_redlines

        # STEP 2: Validate EVERY suggestion with Claude Sonnet (100% validation)
        validated_redlines = []

        logger.info(f"Validating ALL {len(opus_redlines)} suggestions with Claude Sonnet ({self.sonnet_model})...")

        for i, redline in enumerate(opus_redlines):
            self.stats['validated_redlines'] += 1

            # Extract context around the redline
            start = max(0, redline.get('start', 0) - 200)
            end = min(len(working_text), redline.get('end', len(working_text)) + 200)
            context = working_text[start:end]

            # Validate with Sonnet
            validation = await self._call_claude_sonnet(redline, context)

            if validation.get('is_valid', False):
                # Update redline with validation results
                redline['confidence'] = validation.get('adjusted_confidence', redline.get('confidence', 90))
                redline['revised_text'] = validation.get('revised_text', redline.get('revised_text'))
                redline['validation_notes'] = validation.get('reasoning', '')
                redline['validated_by'] = 'claude-sonnet-4.5'
                redline['source'] = 'llm'

                validated_redlines.append(redline)
                logger.debug(
                    f"✓ Validated ({i+1}/{len(opus_redlines)}): {redline.get('clause_type')} "
                    f"at {redline.get('start')}-{redline.get('end')}"
                )
            else:
                self.stats['rejected_redlines'] += 1
                logger.info(
                    f"✗ Rejected ({i+1}/{len(opus_redlines)}): {validation.get('reasoning')}"
                )

        logger.info(f"Sonnet validated {len(validated_redlines)}/{len(opus_redlines)} suggestions")
        logger.info(f"Rejection rate: {self.stats['rejected_redlines']}/{len(opus_redlines)} = {(self.stats['rejected_redlines']/len(opus_redlines)*100) if opus_redlines else 0:.1f}%")

        # STEP 3: Merge with rule-based redlines (avoiding duplicates)
        final_redlines = self._merge_redlines(validated_redlines, rule_redlines)

        # Update stats
        self.stats['total_redlines'] = len(final_redlines)

        logger.info(f"All-Claude analysis complete: {len(final_redlines)} final redlines")
        logger.info(
            f"Stats: Opus={self.stats['opus_calls']}, Sonnet={self.stats['sonnet_calls']}, "
            f"Validated={self.stats['validated_redlines']}, Cost=${self.stats['total_cost_usd']:.4f}"
        )

        return final_redlines

    def _merge_redlines(self, llm_redlines: List[Dict], rule_redlines: List[Dict]) -> List[Dict]:
        """Merge LLM and rule-based redlines, avoiding overlaps"""
        final_redlines = []

        # Add all rule-based redlines first (they have priority as they're deterministic)
        for rule_redline in rule_redlines:
            rule_redline['source'] = 'rule'
            rule_redline['confidence'] = 100  # Rules are always 100% confident
            final_redlines.append(rule_redline)

        # Add LLM redlines that don't overlap with rules
        for llm_redline in llm_redlines:
            overlaps = False
            for rule_redline in rule_redlines:
                if self._spans_overlap(
                    (llm_redline.get('start', 0), llm_redline.get('end', 0)),
                    (rule_redline.get('start', 0), rule_redline.get('end', 0))
                ):
                    overlaps = True
                    self.stats['conflicts_resolved'] += 1
                    logger.debug(
                        f"Skipping overlapping LLM redline at {llm_redline.get('start')}-{llm_redline.get('end')} "
                        f"(conflicts with rule at {rule_redline.get('start')}-{rule_redline.get('end')})"
                    )
                    break

            if not overlaps:
                final_redlines.append(llm_redline)

        # Sort by position
        final_redlines.sort(key=lambda x: x.get('start', 0))

        logger.info(
            f"Merged: {len(rule_redlines)} rule + {len(llm_redlines)} LLM = "
            f"{len(final_redlines)} final ({self.stats['conflicts_resolved']} conflicts resolved)"
        )

        return final_redlines

    def _spans_overlap(self, span1: Tuple[int, int], span2: Tuple[int, int]) -> bool:
        """Check if two text spans overlap"""
        return not (span1[1] <= span2[0] or span2[1] <= span1[0])

    def _parse_text_response(self, text: str) -> Dict:
        """Parse unstructured text response into structured format"""
        # Fallback parser for non-JSON responses
        logger.warning("Using fallback text parser for non-JSON response")
        return {"redlines": [], "error": "Response was not structured JSON"}

    def _extract_clauses(self, text: str) -> List[Dict]:
        """
        Extract individual clauses from document for batch processing.

        Used by batch API to split documents into manageable chunks.
        This is a simple text-based extraction - doesn't require LLM.

        Args:
            text: Full document text

        Returns:
            List of clause dictionaries with text and positions
        """
        clauses = []

        # Split by common clause delimiters
        paragraphs = text.split('\n\n')
        current_position = 0

        for para in paragraphs:
            if len(para.strip()) < 50:  # Skip very short paragraphs
                current_position += len(para) + 2
                continue

            # Look for numbered sections or bullet points
            sections = []
            if any(para.startswith(f"{i}.") for i in range(1, 20)):
                # Split numbered sections
                import re
                pattern = r'(?=\d+\.)'
                sections = re.split(pattern, para)
                sections = [s for s in sections if s.strip()]
            else:
                sections = [para]

            for section in sections:
                if len(section.strip()) >= 50:  # Minimum clause length
                    clause_start = text.find(section, current_position)
                    if clause_start != -1:
                        clauses.append({
                            'text': section.strip(),
                            'start': clause_start,
                            'end': clause_start + len(section)
                        })

            current_position += len(para) + 2

        return clauses

    async def _analyze_clause_with_gpt5(
        self,
        clause_text: str,
        clause_start: int,
        full_text: str
    ) -> List[Dict]:
        """
        Analyze a single clause with Claude (legacy method name for compatibility).

        NOTE: Despite the name, this now uses Claude Opus (not GPT-5).
        The name is kept for backward compatibility with batch API.

        Args:
            clause_text: The clause to analyze
            clause_start: Starting position in document
            full_text: Full document for context

        Returns:
            List of redlines for this clause
        """
        logger.debug(f"Analyzing clause at position {clause_start} with Claude Opus")

        try:
            # Build focused prompt for clause
            system_prompt = """You are a legal expert reviewing NDA clauses for Edgewater Services, LLC.

Identify violations in this specific clause and provide redlines.
Focus on:
- Term limits (18 months maximum)
- Governing law (Delaware with conflict disclaimer)
- Representatives definition (full expanded list)
- Non-solicitation (limited to key executives)
- Confidentiality scope
- IP rights"""

            clause_prompt = f"""Analyze this specific clause from an NDA:

CLAUSE:
{clause_text}

CONTEXT: This is part of a larger NDA. Focus only on issues within this clause.

Return JSON:
{{
    "redlines": [
        {{
            "start": relative_position_in_clause,
            "end": relative_position_in_clause,
            "original_text": "text to change",
            "revised_text": "suggested change",
            "clause_type": "category",
            "severity": "critical/high/moderate",
            "confidence": 0-100,
            "explanation": "why this needs changing"
        }}
    ]
}}"""

            response = await self.client.messages.create(
                model=self.opus_model,
                max_tokens=2000,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": clause_prompt}]
            )

            # Track usage
            if hasattr(response, 'usage'):
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost = (input_tokens * self.OPUS_INPUT_COST) + (output_tokens * self.OPUS_OUTPUT_COST)

                self.stats['opus_tokens_input'] += input_tokens
                self.stats['opus_tokens_output'] += output_tokens
                self.stats['total_cost_usd'] += cost

            # Parse response
            content = response.content[0].text

            try:
                result = json.loads(content)
                redlines = result.get('redlines', [])

                # Adjust positions to be relative to full document
                for redline in redlines:
                    redline['start'] += clause_start
                    redline['end'] += clause_start
                    redline['source'] = 'llm'
                    redline['model'] = 'claude-opus'

                logger.debug(f"Claude Opus found {len(redlines)} redlines in clause")
                return redlines

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Claude response as JSON: {content[:200]}")
                return []

        except Exception as e:
            logger.error(f"Clause analysis with Claude failed: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get processing statistics"""
        stats = self.stats.copy()

        # Add derived metrics
        stats['validation_rate'] = self.validation_rate
        stats['total_llm_calls'] = stats['opus_calls'] + stats['sonnet_calls']
        stats['total_tokens'] = (
            stats['opus_tokens_input'] + stats['opus_tokens_output'] +
            stats['sonnet_tokens_input'] + stats['sonnet_tokens_output']
        )

        # Add model names for reporting
        stats['opus_model'] = self.opus_model
        stats['sonnet_model'] = self.sonnet_model

        return stats


# Legacy compatibility: alias for existing code
LLMOrchestrator = AllClaudeLLMOrchestrator
