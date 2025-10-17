"""
LLM Orchestrator - OPTIMIZED VERSION with Async Clients and Parallel Execution
Performance improvements:
- Async OpenAI and Anthropic clients
- Parallel LLM calls with asyncio.gather()
- Connection pooling for reduced latency
- Non-blocking operations throughout
Expected speedup: 1.8-2x for LLM operations, 10x for concurrent requests
"""
import os
import json
import random
import asyncio
from typing import List, Dict, Optional
from openai import AsyncOpenAI  # Changed to async client
from anthropic import AsyncAnthropic  # Changed to async client

from ..prompts.master_prompt import (
    EDGEWATER_NDA_CHECKLIST,
    build_analysis_prompt,
    NDA_ANALYSIS_SCHEMA
)
import logging

logger = logging.getLogger(__name__)

# Import semantic cache with error handling
try:
    from .semantic_cache import get_semantic_cache
    CACHE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Semantic cache not available: {e}")
    CACHE_AVAILABLE = False
    get_semantic_cache = None


class LLMOrchestrator:
    """
    Orchestrate LLM analysis with validation - OPTIMIZED VERSION.

    Key optimizations:
    1. Async clients with connection pooling
    2. Parallel execution of OpenAI and Anthropic calls
    3. Non-blocking throughout the pipeline
    """

    def __init__(self):
        # Initialize ASYNC clients with connection pooling
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            self.openai_client = AsyncOpenAI(
                api_key=openai_api_key,
                max_retries=3,
                timeout=30.0
            )
        else:
            self.openai_client = None
            logger.warning("OPENAI_API_KEY not configured; GPT-5 analysis disabled")

        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(
                api_key=anthropic_api_key,
                max_retries=3,
                timeout=30.0
            )
        else:
            self.anthropic_client = None
            logger.warning("ANTHROPIC_API_KEY not configured; Claude validation disabled")

        # Configuration
        self.validation_rate = float(os.getenv("VALIDATION_RATE", "0.15"))
        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "95"))
        self.use_prompt_caching = os.getenv("USE_PROMPT_CACHING", "true").lower() == "true"

        # Initialize semantic cache with fallback
        self.semantic_cache = None
        self.enable_cache = False

        if CACHE_AVAILABLE and os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() == "true":
            try:
                self.semantic_cache = get_semantic_cache(redis_url=os.getenv("REDIS_URL"))
                self.enable_cache = self.semantic_cache.enabled if self.semantic_cache else False
                if self.enable_cache:
                    logger.info("Semantic cache initialized successfully")
                else:
                    logger.warning("Semantic cache disabled - running without cache")
            except Exception as e:
                logger.error(f"Failed to initialize semantic cache: {e}")
                logger.warning("Continuing without semantic cache")
                self.semantic_cache = None
                self.enable_cache = False
        else:
            logger.info("Semantic cache disabled via configuration")

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
        OPTIMIZED: All operations are truly async.
        """
        # Build handled spans list
        handled_spans = [(r['start'], r['end']) for r in rule_redlines]

        # Split text into clauses for granular caching
        clauses = self._extract_clauses(working_text)

        # Process clauses in parallel batches for better performance
        batch_size = 5  # Process 5 clauses concurrently
        all_redlines = []

        for i in range(0, len(clauses), batch_size):
            batch = clauses[i:i+batch_size]
            batch_tasks = []

            for clause in batch:
                clause_text = clause['text']
                clause_start = clause['start']
                clause_end = clause['end']

                # Skip if already handled by rules
                if any(cs <= clause_start < ce or cs < clause_end <= ce
                       for cs, ce in handled_spans):
                    continue

                # Create async task for each clause
                batch_tasks.append(
                    self._process_clause_async(
                        clause_text, clause_start, working_text, handled_spans
                    )
                )

            # Process batch in parallel
            if batch_tasks:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                for result in batch_results:
                    if isinstance(result, list):
                        all_redlines.extend(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Error processing clause: {result}")

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

    async def _process_clause_async(
        self,
        clause_text: str,
        clause_start: int,
        full_text: str,
        handled_spans: List[tuple]
    ) -> List[Dict]:
        """
        Process a single clause with caching and LLM analysis.
        OPTIMIZED: Fully async operation.
        """
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
            self.stats['estimated_cost_saved'] += 0.03

            # Adjust positions for this document
            cached_redlines = cached_result['response'].get('redlines', [])
            for redline in cached_redlines:
                redline['start'] += clause_start
                redline['end'] += clause_start
                redline['cached'] = True
                redline['cache_similarity'] = cached_result['similarity']
            return cached_redlines
        else:
            # Analyze with LLM
            self.stats['cache_misses'] += 1
            clause_redlines = await self._analyze_clause_with_gpt5_async(
                clause_text, clause_start, full_text
            )

            # Store in cache for future use
            if self.enable_cache and clause_redlines:
                await self.semantic_cache.store(
                    clause_text,
                    {'redlines': clause_redlines},
                    context={'document_type': 'nda'},
                    cost=0.03
                )

            return clause_redlines

    async def _analyze_clause_with_gpt5_async(
        self,
        clause_text: str,
        clause_start: int,
        full_text: str
    ) -> List[Dict]:
        """
        Analyze a single clause with GPT-5.
        OPTIMIZED: Truly async OpenAI call.
        """
        if not self.openai_client:
            logger.warning("OPENAI_API_KEY not configured; skipping GPT-5 clause analysis")
            return []

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

            # Get model from environment
            model = os.getenv("GPT_MODEL", "gpt-4")  # Note: Changed default to gpt-4

            # ASYNC OpenAI call - no longer blocks event loop
            response = await self.openai_client.chat.completions.create(
                model=model,
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
                v['start'] = clause_start + v.get('start', 0)
                v['end'] = clause_start + v.get('end', len(clause_text))
                v['source'] = 'gpt5'
                v['model'] = model
                v['clause_analyzed'] = True

            return violations

        except Exception as e:
            logger.error(f"GPT-5 clause analysis error: {e}")
            return []

    async def _validate_with_claude_async(
        self,
        working_text: str,
        redlines_to_validate: List[Dict],
        handled_spans: List[tuple]
    ) -> List[Dict]:
        """
        Validate specific redlines with Claude.
        OPTIMIZED: Truly async Anthropic call.
        """
        if not self.anthropic_client:
            logger.warning("ANTHROPIC_API_KEY not configured; skipping Claude validation")
            return []

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

            # ASYNC Anthropic call - no longer blocks event loop
            response = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Using latest model
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
            logger.error(f"Claude validation error: {e}")
            return []

    async def _analyze_with_dual_llm(
        self,
        working_text: str,
        handled_spans: List[tuple]
    ) -> List[Dict]:
        """
        Run OpenAI and Claude analysis in PARALLEL.
        OPTIMIZED: Major speedup from parallel execution.
        """
        async def call_openai():
            """Async OpenAI analysis"""
            if not self.openai_client:
                return []

            try:
                prompt = build_analysis_prompt(working_text, handled_spans)
                messages = [
                    {"role": "system", "content": EDGEWATER_NDA_CHECKLIST},
                    {"role": "user", "content": prompt}
                ]

                model = os.getenv("GPT_MODEL", "gpt-4")

                response = await self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={
                        "type": "json_schema",
                        "json_schema": NDA_ANALYSIS_SCHEMA
                    },
                    temperature=0.1,
                    max_tokens=4000
                )

                result = json.loads(response.choices[0].message.content)
                violations = result.get('violations', [])

                for v in violations:
                    v['source'] = 'openai'
                    v['model'] = model

                return violations

            except Exception as e:
                logger.error(f"OpenAI analysis error: {e}")
                return []

        async def call_claude():
            """Async Claude analysis"""
            if not self.anthropic_client:
                return []

            try:
                prompt = build_analysis_prompt(working_text, handled_spans)

                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )

                # Parse Claude's response (may need JSON extraction)
                response_text = response.content[0].text
                violations = self._parse_claude_analysis(response_text)

                for v in violations:
                    v['source'] = 'anthropic'
                    v['model'] = 'claude-3-5-sonnet'

                return violations

            except Exception as e:
                logger.error(f"Claude analysis error: {e}")
                return []

        # PARALLEL EXECUTION - Key optimization!
        # Both LLMs run simultaneously, time = max(openai_time, claude_time)
        # Instead of sequential time = openai_time + claude_time
        openai_results, claude_results = await asyncio.gather(
            call_openai(),
            call_claude()
        )

        # Merge and deduplicate results
        all_results = openai_results + claude_results
        return self._deduplicate_redlines(all_results)

    def _deduplicate_redlines(self, redlines: List[Dict]) -> List[Dict]:
        """Remove duplicate redlines from multiple sources"""
        seen = set()
        unique = []

        for redline in redlines:
            key = (redline['start'], redline['end'], redline.get('revised_text', ''))
            if key not in seen:
                seen.add(key)
                unique.append(redline)

        return unique

    def _parse_claude_analysis(self, response_text: str) -> List[Dict]:
        """Parse Claude's analysis response"""
        try:
            # Try to extract JSON if present
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

            if 'violations' in parsed:
                return parsed['violations']
            elif isinstance(parsed, list):
                return parsed
            else:
                return []

        except Exception as e:
            logger.error(f"Error parsing Claude analysis: {e}")
            return []

    # Keep all the existing helper methods unchanged
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
            logger.error(f"Error parsing Claude validation: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get orchestration statistics"""
        return self.stats.copy()

    def _extract_clauses(self, text: str) -> List[Dict]:
        """
        Extract individual clauses from document for granular caching.
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