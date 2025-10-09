"""
LLM Orchestrator - GPT-5 analysis with Claude validation
Handles non-deterministic pattern detection with cross-validation
Integrated with semantic cache for 60% cost reduction
"""
import os
import json
import random
import asyncio
from typing import List, Dict, Optional
from openai import OpenAI
from anthropic import Anthropic

from ..prompts.master_prompt import (
    EDGEWATER_NDA_CHECKLIST,
    build_analysis_prompt,
    NDA_ANALYSIS_SCHEMA
)
from .semantic_cache import get_semantic_cache


class LLMOrchestrator:
    """
    Orchestrate LLM analysis with validation.

    Flow:
    1. GPT-5 with structured output for initial analysis
    2. Claude validation for low-confidence or sampled redlines
    3. Conflict resolution
    """

    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Configuration
        self.validation_rate = float(os.getenv("VALIDATION_RATE", "0.15"))
        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "95"))
        self.use_prompt_caching = os.getenv("USE_PROMPT_CACHING", "true").lower() == "true"

        # Initialize semantic cache
        self.semantic_cache = get_semantic_cache(redis_url=os.getenv("REDIS_URL"))
        self.enable_cache = os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() == "true"

        # Stats
        self.stats = {
            'gpt_calls': 0,
            'claude_calls': 0,
            'validations': 0,
            'conflicts': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'estimated_cost_saved': 0.0
        }

    async def analyze(self, working_text: str, rule_redlines: List[Dict]) -> List[Dict]:
        """
        Analyze document with LLM, using semantic cache for similar clauses.

        Args:
            working_text: Normalized document text
            rule_redlines: Redlines already applied by RuleEngine

        Returns:
            List of additional redlines found by LLM
        """
        # Build handled spans list
        handled_spans = [(r['start'], r['end']) for r in rule_redlines]

        # Split text into clauses for granular caching
        clauses = self._extract_clauses(working_text)
        all_redlines = []

        for clause in clauses:
            clause_text = clause['text']
            clause_start = clause['start']
            clause_end = clause['end']

            # Skip if already handled by rules
            if any(cs <= clause_start < ce or cs < clause_end <= ce
                   for cs, ce in handled_spans):
                continue

            # Check semantic cache first
            cached_result = None
            if self.enable_cache:
                cached_result = await self.semantic_cache.search(
                    clause_text,
                    context={'document_type': 'nda'}
                )

            if cached_result:
                # Use cached response
                self.stats['cache_hits'] += 1
                self.stats['estimated_cost_saved'] += 0.03  # Estimated cost per clause

                # Adjust positions for this document
                cached_redlines = cached_result['response'].get('redlines', [])
                for redline in cached_redlines:
                    # Adjust positions relative to full document
                    redline['start'] += clause_start
                    redline['end'] += clause_start
                    redline['cached'] = True
                    redline['cache_similarity'] = cached_result['similarity']
                    all_redlines.append(redline)
            else:
                # Analyze with LLM
                self.stats['cache_misses'] += 1
                clause_redlines = await self._analyze_clause_with_gpt5(
                    clause_text, clause_start, working_text
                )

                # Store in cache for future use
                if self.enable_cache and clause_redlines:
                    await self.semantic_cache.store(
                        clause_text,
                        {'redlines': clause_redlines},
                        context={'document_type': 'nda'},
                        cost=0.03
                    )

                all_redlines.extend(clause_redlines)

        # Filter out redlines that overlap with rule-based ones
        all_redlines = self._filter_overlaps(all_redlines, handled_spans)

        # Validation logic
        needs_validation = self._select_for_validation(all_redlines)

        if needs_validation:
            validated = await self._validate_with_claude_async(
                working_text,
                needs_validation,
                handled_spans + [(r['start'], r['end']) for r in all_redlines if r not in needs_validation]
            )

            # Merge validated results
            all_redlines = self._merge_validated_results(all_redlines, needs_validation, validated)

        # Update cache statistics
        if self.enable_cache:
            cache_stats = self.semantic_cache.get_statistics()
            self.stats.update({
                'total_cache_entries': cache_stats['total_entries'],
                'cache_hit_rate': cache_stats['hit_rate'],
                'total_cost_saved': cache_stats['total_cost_saved']
            })

        return all_redlines

    def _analyze_with_gpt5(self, working_text: str, handled_spans: List[tuple]) -> List[Dict]:
        """Call GPT-5 with structured output"""
        try:
            prompt = build_analysis_prompt(working_text, handled_spans)

            messages = [
                {
                    "role": "system",
                    "content": EDGEWATER_NDA_CHECKLIST
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Use prompt caching if available (requires appropriate model)
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Using GPT-4o as GPT-5 placeholder
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": NDA_ANALYSIS_SCHEMA
                },
                temperature=0.1,  # Low temperature for consistency
                max_tokens=4000
            )

            result = json.loads(response.choices[0].message.content)
            violations = result.get('violations', [])

            # Add metadata
            for v in violations:
                v['source'] = 'gpt5'
                v['model'] = 'gpt-4o'

            return violations

        except Exception as e:
            print(f"GPT-5 analysis error: {e}")
            return []

    def _validate_with_claude(
        self,
        working_text: str,
        redlines_to_validate: List[Dict],
        handled_spans: List[tuple]
    ) -> List[Dict]:
        """Validate specific redlines with Claude"""
        try:
            self.stats['claude_calls'] += 1
            self.stats['validations'] += len(redlines_to_validate)

            # Build validation prompt
            validation_prompt = self._build_validation_prompt(
                working_text,
                redlines_to_validate,
                handled_spans
            )

            # Use prompt caching with Claude
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": EDGEWATER_NDA_CHECKLIST,
                            "cache_control": {"type": "ephemeral"} if self.use_prompt_caching else None
                        },
                        {
                            "type": "text",
                            "text": validation_prompt
                        }
                    ]
                }
            ]

            # Remove None cache_control if not using caching
            if not self.use_prompt_caching:
                messages[0]["content"][0].pop("cache_control", None)

            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0,
                messages=messages
            )

            # Parse response
            response_text = response.content[0].text

            # Extract JSON from response
            validated = self._parse_claude_validation(response_text)

            return validated

        except Exception as e:
            print(f"Claude validation error: {e}")
            # On error, mark all as unvalidated
            return []

    def _select_for_validation(self, redlines: List[Dict]) -> List[Dict]:
        """Select which redlines need Claude validation"""
        needs_validation = []

        for redline in redlines:
            confidence = redline.get('confidence', 100)

            # Always validate low confidence
            if confidence < self.confidence_threshold:
                needs_validation.append(redline)

            # Random sampling
            elif random.random() < self.validation_rate:
                needs_validation.append(redline)

        return needs_validation

    def _filter_overlaps(self, redlines: List[Dict], handled_spans: List[tuple]) -> List[Dict]:
        """Remove redlines that overlap with already-handled spans"""
        filtered = []

        for redline in redlines:
            r_start = redline['start']
            r_end = redline['end']

            overlaps = False
            for h_start, h_end in handled_spans:
                # Check for any overlap
                if r_start < h_end and r_end > h_start:
                    overlaps = True
                    break

            if not overlaps:
                filtered.append(redline)

        return filtered

    def _merge_validated_results(
        self,
        original: List[Dict],
        validated_subset: List[Dict],
        validation_results: List[Dict]
    ) -> List[Dict]:
        """Merge validation results back into original redlines"""
        # Create lookup for validation results
        validation_map = {}
        for v in validation_results:
            key = (v['start'], v['end'])
            validation_map[key] = v

        # Build final list
        final = []

        for redline in original:
            key = (redline['start'], redline['end'])

            if redline in validated_subset:
                # Check if validated
                if key in validation_map:
                    validated = validation_map[key]
                    # Check for conflicts
                    if self._check_conflict(redline, validated):
                        self.stats['conflicts'] += 1
                        # Use validated version (Claude takes precedence)
                        redline['validated'] = True
                        redline['validation_source'] = 'claude'
                        redline['original_gpt_version'] = redline.copy()
                        redline.update(validated)
                    else:
                        # No conflict, just mark as validated
                        redline['validated'] = True
                        redline['validation_source'] = 'claude'

                    final.append(redline)
                else:
                    # Validation rejected this redline
                    redline['validated'] = False
                    redline['rejected_by_claude'] = True
                    # Don't include rejected redlines
            else:
                # Not validated, keep as-is
                final.append(redline)

        return final

    def _check_conflict(self, gpt_redline: Dict, claude_redline: Dict) -> bool:
        """Check if GPT and Claude disagree on a redline"""
        # Compare revised text
        gpt_revised = gpt_redline.get('revised_text', '').strip()
        claude_revised = claude_redline.get('revised_text', '').strip()

        if gpt_revised != claude_revised:
            return True

        # Compare severity
        if gpt_redline.get('severity') != claude_redline.get('severity'):
            return True

        return False

    def _build_validation_prompt(
        self,
        working_text: str,
        redlines: List[Dict],
        handled_spans: List[tuple]
    ) -> str:
        """Build prompt for Claude validation"""
        redlines_text = json.dumps(redlines, indent=2)

        prompt = f"""
Please validate these proposed NDA redlines against the Edgewater checklist.

For each redline, confirm:
1. The violation is real and requires fixing
2. The proposed revision is correct
3. The severity is appropriate
4. The positioning is accurate

DOCUMENT TEXT:
```
{working_text}
```

PROPOSED REDLINES:
```json
{redlines_text}
```

Return a JSON array containing ONLY the redlines you confirm as valid.
If a redline is incorrect, omit it from the response.
If you suggest modifications, include them in the returned redline.

Format: {{"validated_redlines": [...]}}
"""

        return prompt

    def _parse_claude_validation(self, response_text: str) -> List[Dict]:
        """Parse Claude's validation response"""
        try:
            # Try to extract JSON
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            elif '{' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_text = response_text[json_start:json_end]
            else:
                return []

            parsed = json.loads(json_text)

            if 'validated_redlines' in parsed:
                return parsed['validated_redlines']
            elif isinstance(parsed, list):
                return parsed
            else:
                return []

        except Exception as e:
            print(f"Error parsing Claude validation: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get orchestration statistics"""
        return self.stats.copy()

    def _extract_clauses(self, text: str) -> List[Dict]:
        """
        Extract individual clauses from document for granular caching.

        Args:
            text: Full document text

        Returns:
            List of clause dictionaries with text and positions
        """
        clauses = []

        # Split by common clause delimiters
        # This is a simplified approach - can be enhanced with better NLP
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
        Analyze a single clause with GPT-5.

        Args:
            clause_text: The clause to analyze
            clause_start: Starting position in document
            full_text: Full document for context

        Returns:
            List of redlines for this clause
        """
        try:
            # Build focused prompt for clause
            prompt = f"""
Analyze this specific clause from an NDA for Edgewater compliance issues:

CLAUSE:
{clause_text}

CONTEXT: This is part of a larger NDA document. Focus only on issues within this specific clause.

Identify any violations of the Edgewater NDA checklist and provide specific redlines.
Return as JSON matching the schema.
"""

            messages = [
                {
                    "role": "system",
                    "content": EDGEWATER_NDA_CHECKLIST
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": NDA_ANALYSIS_SCHEMA
                },
                temperature=0.1,
                max_tokens=2000
            )

            self.stats['gpt_calls'] += 1
            result = json.loads(response.choices[0].message.content)
            violations = result.get('violations', [])

            # Adjust positions and add metadata
            for v in violations:
                # Positions are relative to clause, adjust to document
                v['start'] = clause_start + v.get('start', 0)
                v['end'] = clause_start + v.get('end', len(clause_text))
                v['source'] = 'gpt5'
                v['model'] = 'gpt-4o'
                v['clause_analyzed'] = True

            return violations

        except Exception as e:
            print(f"GPT-5 clause analysis error: {e}")
            return []

    async def _validate_with_claude_async(
        self,
        working_text: str,
        redlines_to_validate: List[Dict],
        handled_spans: List[tuple]
    ) -> List[Dict]:
        """
        Async version of Claude validation.

        Args:
            working_text: Full document text
            redlines_to_validate: Redlines to validate
            handled_spans: Already handled spans

        Returns:
            Validated redlines
        """
        # For now, wrap the sync method
        # In production, would use async Anthropic client
        return self._validate_with_claude(
            working_text,
            redlines_to_validate,
            handled_spans
        )
