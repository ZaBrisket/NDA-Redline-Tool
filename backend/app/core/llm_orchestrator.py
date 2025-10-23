"""
LLM Orchestrator - GPT-5 analysis with Claude validation
Handles non-deterministic pattern detection with cross-validation
"""
import os
import json
import random
import time
import logging
import re
import threading
from typing import List, Dict, Optional
from openai import OpenAI, RateLimitError, APIConnectionError, APITimeoutError
from anthropic import Anthropic, APIStatusError, APIConnectionError as AnthropicConnectionError

from ..prompts.master_prompt import (
    EDGEWATER_NDA_CHECKLIST,
    build_analysis_prompt,
    NDA_ANALYSIS_SCHEMA
)


class LLMOrchestrator:
    """
    Orchestrate LLM analysis with validation.

    Flow:
    1. GPT-5 with structured output for initial analysis
    2. Claude validation for low-confidence or sampled redlines
    3. Conflict resolution
    """

    # Class-level singleton clients for connection pooling
    _openai_client = None
    _anthropic_client = None
    _client_lock = threading.Lock()  # Thread-safe client initialization

    @classmethod
    def get_openai_client(cls) -> OpenAI:
        """Get or create singleton OpenAI client"""
        if cls._openai_client is None:
            with cls._client_lock:
                # Double-check pattern for thread safety
                if cls._openai_client is None:
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        raise ValueError("OPENAI_API_KEY not set")

                    cls._openai_client = OpenAI(
                        api_key=api_key,
                        timeout=30,  # 30 seconds timeout
                        max_retries=0  # We handle retries manually
                    )
                    logging.getLogger(__name__).info("Initialized OpenAI client singleton")

        return cls._openai_client

    @classmethod
    def get_anthropic_client(cls) -> Anthropic:
        """Get or create singleton Anthropic client"""
        if cls._anthropic_client is None:
            with cls._client_lock:
                # Double-check pattern for thread safety
                if cls._anthropic_client is None:
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        raise ValueError("ANTHROPIC_API_KEY not set")

                    cls._anthropic_client = Anthropic(
                        api_key=api_key,
                        timeout=30,  # 30 seconds timeout
                        max_retries=0  # We handle retries manually
                    )
                    logging.getLogger(__name__).info("Initialized Anthropic client singleton")

        return cls._anthropic_client

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize API clients using singletons
        self.request_timeout = 30  # 30 seconds timeout
        self.max_retries = 3
        self.retry_delay = 1  # Initial delay in seconds

        # Use singleton clients for connection pooling
        self.openai_client = self.get_openai_client()
        self.anthropic_client = self.get_anthropic_client()

        # Configuration
        self.validation_rate = float(os.getenv("VALIDATION_RATE", "0.15"))
        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "95"))
        self.use_prompt_caching = os.getenv("USE_PROMPT_CACHING", "true").lower() == "true"

        # Pricing (as of Jan 2025)
        self.GPT_INPUT_COST = 0.003 / 1000   # $0.003 per 1K input tokens
        self.GPT_OUTPUT_COST = 0.006 / 1000  # $0.006 per 1K output tokens
        self.CLAUDE_INPUT_COST = 0.003 / 1000  # $0.003 per 1K input tokens
        self.CLAUDE_OUTPUT_COST = 0.015 / 1000  # $0.015 per 1K output tokens

        # Stats with enhanced tracking
        self.stats = {
            'gpt_calls': 0,
            'gpt_tokens_input': 0,
            'gpt_tokens_output': 0,
            'gpt_rate_limits': 0,
            'gpt_timeouts': 0,
            'gpt_errors': 0,
            'claude_calls': 0,
            'claude_tokens_input': 0,
            'claude_tokens_output': 0,
            'claude_rate_limits': 0,
            'claude_errors': 0,
            'validations': 0,
            'conflicts': 0,
            'total_cost_usd': 0.0
        }

    def analyze(self, working_text: str, rule_redlines: List[Dict]) -> List[Dict]:
        """
        Analyze document with LLM, skipping already-handled spans.

        Args:
            working_text: Normalized document text
            rule_redlines: Redlines already applied by RuleEngine

        Returns:
            List of additional redlines found by LLM
        """
        # Build handled spans list
        handled_spans = [(r['start'], r['end']) for r in rule_redlines]

        # Call GPT-5
        gpt_redlines = self._analyze_with_gpt5(working_text, handled_spans)
        self.stats['gpt_calls'] += 1

        # Filter out redlines that overlap with rule-based ones
        gpt_redlines = self._filter_overlaps(gpt_redlines, handled_spans)

        # Validation logic
        needs_validation = self._select_for_validation(gpt_redlines)

        if needs_validation:
            validated = self._validate_with_claude(
                working_text,
                needs_validation,
                handled_spans + [(r['start'], r['end']) for r in gpt_redlines if r not in needs_validation]
            )

            # Merge validated results
            gpt_redlines = self._merge_validated_results(gpt_redlines, needs_validation, validated)

        return gpt_redlines

    def _analyze_with_gpt5(self, working_text: str, handled_spans: List[tuple]) -> List[Dict]:
        """Call GPT-5 with structured output, retry logic, and cost tracking"""
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

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                # Make API call
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

                # Track usage and costs
                if hasattr(response, 'usage'):
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    cost = (input_tokens * self.GPT_INPUT_COST) + (output_tokens * self.GPT_OUTPUT_COST)

                    self.stats['gpt_tokens_input'] += input_tokens
                    self.stats['gpt_tokens_output'] += output_tokens
                    self.stats['total_cost_usd'] += cost

                    self.logger.info(
                        f"GPT-4o call: {input_tokens} input, {output_tokens} output tokens, "
                        f"${cost:.4f} cost (total: ${self.stats['total_cost_usd']:.2f})"
                    )

                result = json.loads(response.choices[0].message.content)
                violations = result.get('violations', [])

                # Add metadata
                for v in violations:
                    v['source'] = 'gpt5'
                    v['model'] = 'gpt-4o'

                return violations

            except RateLimitError as e:
                self.stats['gpt_rate_limits'] += 1
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"GPT rate limited, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"GPT rate limit exceeded after {self.max_retries} attempts")
                    return []

            except APITimeoutError as e:
                self.stats['gpt_timeouts'] += 1
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"GPT timeout, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"GPT timeout after {self.max_retries} attempts")
                    return []

            except APIConnectionError as e:
                self.stats['gpt_errors'] += 1
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"GPT connection error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"GPT connection failed after {self.max_retries} attempts")
                    return []

            except Exception as e:
                self.stats['gpt_errors'] += 1
                self.logger.error(f"GPT-5 analysis error: {e}", exc_info=True)
                return []

        return []

    def _validate_with_claude(
        self,
        working_text: str,
        redlines_to_validate: List[Dict],
        handled_spans: List[tuple]
    ) -> List[Dict]:
        """Validate specific redlines with Claude with retry logic and cost tracking"""
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

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    temperature=0,
                    messages=messages
                )

                # Track usage and costs
                if hasattr(response, 'usage'):
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    cost = (input_tokens * self.CLAUDE_INPUT_COST) + (output_tokens * self.CLAUDE_OUTPUT_COST)

                    self.stats['claude_tokens_input'] += input_tokens
                    self.stats['claude_tokens_output'] += output_tokens
                    self.stats['total_cost_usd'] += cost

                    self.logger.info(
                        f"Claude call: {input_tokens} input, {output_tokens} output tokens, "
                        f"${cost:.4f} cost (total: ${self.stats['total_cost_usd']:.2f})"
                    )

                # Parse response
                response_text = response.content[0].text

                # Extract JSON from response
                validated = self._parse_claude_validation(response_text)

                return validated

            except APIStatusError as e:
                # Check if it's a rate limit error
                if hasattr(e, 'status_code') and e.status_code == 429:
                    self.stats['claude_rate_limits'] += 1
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        self.logger.warning(f"Claude rate limited, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"Claude rate limit exceeded after {self.max_retries} attempts")
                else:
                    self.stats['claude_errors'] += 1
                    self.logger.error(f"Claude API error: {e}")
                return []

            except AnthropicConnectionError as e:
                self.stats['claude_errors'] += 1
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"Claude connection error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"Claude connection failed after {self.max_retries} attempts")
                return []

            except Exception as e:
                self.stats['claude_errors'] += 1
                self.logger.error(f"Claude validation error: {e}", exc_info=True)
                return []

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
        """Parse Claude's validation response with improved error handling"""
        if not response_text:
            self.logger.warning("Empty response from Claude validation")
            return []

        try:
            # Method 1: Look for JSON code blocks
            json_blocks = re.findall(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
            if json_blocks:
                json_text = json_blocks[0].strip()
            else:
                # Method 2: Look for JSON-like structure
                # Find the outermost JSON object or array
                json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1)
                else:
                    # Method 3: Try to find any JSON starting with { or [
                    if '{' in response_text:
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        json_text = response_text[json_start:json_end]
                    elif '[' in response_text:
                        json_start = response_text.find('[')
                        json_end = response_text.rfind(']') + 1
                        json_text = response_text[json_start:json_end]
                    else:
                        self.logger.warning("No JSON structure found in Claude response")
                        self.logger.debug(f"Response text: {response_text[:500]}")
                        return []

            # Parse the JSON
            parsed = json.loads(json_text)

            # Validate structure and extract redlines
            if isinstance(parsed, dict):
                if 'validated_redlines' in parsed:
                    redlines = parsed['validated_redlines']
                elif 'redlines' in parsed:
                    redlines = parsed['redlines']
                else:
                    # If dict but no expected keys, might be a single redline
                    if all(k in parsed for k in ['start', 'end', 'original_text']):
                        redlines = [parsed]
                    else:
                        self.logger.warning(f"Unexpected JSON structure from Claude: {list(parsed.keys())}")
                        return []
            elif isinstance(parsed, list):
                redlines = parsed
            else:
                self.logger.warning(f"Unexpected JSON type from Claude: {type(parsed)}")
                return []

            # Validate each redline has required fields
            validated_redlines = []
            required_fields = {'start', 'end', 'original_text'}

            for i, redline in enumerate(redlines):
                if not isinstance(redline, dict):
                    self.logger.warning(f"Redline {i} is not a dict: {type(redline)}")
                    continue

                missing_fields = required_fields - set(redline.keys())
                if missing_fields:
                    self.logger.warning(f"Redline {i} missing fields: {missing_fields}")
                    continue

                # Validate field types
                try:
                    redline['start'] = int(redline['start'])
                    redline['end'] = int(redline['end'])
                    redline['original_text'] = str(redline['original_text'])

                    # Ensure start < end
                    if redline['start'] >= redline['end']:
                        self.logger.warning(f"Invalid redline positions: start={redline['start']}, end={redline['end']}")
                        continue

                    validated_redlines.append(redline)

                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Invalid field types in redline {i}: {e}")
                    continue

            self.logger.info(f"Successfully parsed {len(validated_redlines)} validated redlines from Claude")
            return validated_redlines

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Claude validation JSON: {e}")
            self.logger.debug(f"JSON text attempted: {json_text[:500] if 'json_text' in locals() else 'N/A'}")
            return []

        except Exception as e:
            self.logger.error(f"Unexpected error parsing Claude validation: {e}", exc_info=True)
            return []

    def get_stats(self) -> Dict:
        """Get orchestration statistics"""
        return self.stats.copy()
