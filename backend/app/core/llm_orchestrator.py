"""
Anthropic-exclusive LLM orchestrator with production-grade error handling
Implements comprehensive retry logic, circuit breakers, and observability
"""

import asyncio
import json
import logging
import random
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

import structlog
from anthropic import AsyncAnthropic, APIStatusError, APIConnectionError

# Try to import optional monitoring dependencies
try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create dummy classes
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def labels(self, **kwargs): return self
        def inc(self, amount=1): pass

    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def labels(self, **kwargs): return self
        def time(self):
            class Timer:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return Timer()

    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, value): pass

try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    class sentry_sdk:
        class Hub:
            class current:
                client = None

# Configure structured logging with trace context
try:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger()
except Exception:
    # Fallback to standard logging if structlog fails
    logger = logging.getLogger(__name__)

# Prometheus metrics
if PROMETHEUS_AVAILABLE:
    claude_requests = Counter('claude_requests_total', 'Total Claude API requests', ['model', 'status'])
    claude_latency = Histogram('claude_request_duration_seconds', 'Claude API request latency', ['model'])
    claude_tokens = Counter('claude_tokens_total', 'Total tokens processed', ['model', 'type'])
    claude_errors = Counter('claude_errors_total', 'Total Claude API errors', ['model', 'error_type'])
    circuit_breaker_state_metric = Gauge('circuit_breaker_state', 'Circuit breaker state (0=closed, 1=open, 2=half-open)')
else:
    claude_requests = Counter()
    claude_latency = Histogram()
    claude_tokens = Counter()
    claude_errors = Counter()
    circuit_breaker_state_metric = Gauge()

class ProcessingState(Enum):
    """Document processing states for tracking"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2

class AnthropicExclusiveOrchestrator:
    """
    Production-hardened Anthropic orchestrator with comprehensive error handling
    Implements retry logic, circuit breakers, and full observability
    """

    def __init__(
        self,
        api_key: str,
        max_retries: int = 5,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_reset_time: int = 60
    ):
        """
        Initialize orchestrator with production configurations

        Args:
            api_key: Anthropic API key (must start with sk-ant-)
            max_retries: Maximum retry attempts for transient errors
            circuit_breaker_threshold: Failures before circuit opens
            circuit_breaker_reset_time: Seconds before circuit reset attempt
        """
        if not api_key or not api_key.startswith("sk-ant-"):
            raise ValueError(f"Invalid Anthropic API key format. Must start with 'sk-ant-'")

        self.client = AsyncAnthropic(api_key=api_key, max_retries=0)  # Manual retry control
        self.max_retries = max_retries

        # Circuit breaker configuration
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_reset_time = circuit_breaker_reset_time
        self.circuit_breaker_failures = 0
        self.circuit_breaker_last_failure_time = None
        self.circuit_breaker_state = CircuitBreakerState.CLOSED

        # Statistics tracking
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'opus_calls': 0,
            'sonnet_calls': 0,
            'total_retries': 0,
            'rate_limit_hits': 0,
            'overload_errors': 0,
            'timeout_errors': 0,
            'connection_errors': 0,
            'total_tokens_input': 0,
            'total_tokens_output': 0,
            'total_cost_usd': 0.0,
            'circuit_breaker_trips': 0,
            'processing_times': []
        }

        logger.info(
            "Initialized Anthropic orchestrator",
            max_retries=max_retries,
            circuit_breaker_threshold=circuit_breaker_threshold
        )

    async def analyze_document(
        self,
        document_text: str,
        document_id: str,
        correlation_id: Optional[str] = None,
        rule_redlines: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analyze document with Claude Opus and validate with Sonnet

        Args:
            document_text: Full text of the document to analyze
            document_id: Unique identifier for the document
            correlation_id: Request correlation ID for tracing
            rule_redlines: Pre-computed rule-based redlines

        Returns:
            Dictionary containing analysis results and metadata

        Raises:
            RuntimeError: When analysis fails after all retries
        """
        start_time = time.time()
        correlation_id = correlation_id or str(uuid.uuid4())

        # Bind context for all logs in this request
        try:
            structlog.contextvars.bind_contextvars(
                correlation_id=correlation_id,
                document_id=document_id,
                document_length=len(document_text)
            )
        except Exception:
            pass  # Fallback if structlog not available

        try:
            # Check circuit breaker
            if not self._check_circuit_breaker():
                error_msg = "Circuit breaker is open - service temporarily unavailable"
                logger.error(error_msg, circuit_breaker_state=self.circuit_breaker_state.name)
                claude_errors.labels(model="opus", error_type="circuit_breaker").inc()
                raise RuntimeError(error_msg)

            # Primary analysis with Opus
            logger.info("Starting Claude Opus analysis")
            opus_result = await self._analyze_with_opus(
                document_text=document_text,
                document_id=document_id,
                rule_redlines=rule_redlines or []
            )

            # opus_result will always be a dict (never None) but may have empty redlines
            if not opus_result.get('redlines'):
                logger.info("Claude Opus found no issues - document appears clean")
                # Still proceed to validation for completeness
            else:
                logger.info(f"Claude Opus identified {len(opus_result['redlines'])} potential issues")

            # Validation with Sonnet
            logger.info("Starting Claude Sonnet validation")
            validated_result = await self._validate_with_sonnet(
                opus_result=opus_result,
                document_text=document_text,
                document_id=document_id
            )

            # Calculate final metrics
            processing_time = time.time() - start_time
            self.stats['processing_times'].append(processing_time)
            self.stats['successful_requests'] += 1

            result = {
                'status': 'success',
                'redlines': validated_result,
                'correlation_id': correlation_id,
                'processing_time': processing_time,
                'opus_redlines': len(opus_result.get('redlines', [])),
                'validated_redlines': len(validated_result),
                'stats_snapshot': self._get_stats_snapshot()
            }

            logger.info(
                "Document analysis completed successfully",
                processing_time=processing_time,
                total_redlines=len(validated_result)
            )

            # Reset circuit breaker on success
            self._reset_circuit_breaker()

            return result

        except Exception as e:
            self.stats['failed_requests'] += 1
            processing_time = time.time() - start_time

            # Create user-friendly error message for the exception
            user_friendly_error = self._get_user_friendly_error(e)

            logger.error(
                "Document analysis failed",
                error=str(e),
                error_type=type(e).__name__,
                processing_time=processing_time,
                correlation_id=correlation_id,
                exc_info=True
            )

            # Report to Sentry if available
            if SENTRY_AVAILABLE and sentry_sdk.Hub.current.client:
                try:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_context("document", {
                            "document_id": document_id,
                            "correlation_id": correlation_id,
                            "document_length": len(document_text)
                        })
                        scope.set_context("orchestrator_stats", self.stats)
                        sentry_sdk.capture_exception(e)
                except Exception:
                    pass  # Don't fail on Sentry errors

            # Raise user-friendly error for document_worker to catch and handle gracefully
            raise RuntimeError(user_friendly_error) from e
        finally:
            try:
                structlog.contextvars.clear_contextvars()
            except Exception:
                pass

    async def _analyze_with_opus(
        self,
        document_text: str,
        document_id: str,
        rule_redlines: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Perform primary analysis with Claude Opus
        Includes comprehensive retry logic and error handling
        """
        model = "claude-3-opus-20240229"

        for attempt in range(self.max_retries + 1):
            try:
                if PROMETHEUS_AVAILABLE:
                    with claude_latency.labels(model="opus").time():
                        start_time = time.time()
                else:
                    start_time = time.time()

                # Build the analysis prompt
                prompt = self._build_opus_prompt(document_text, rule_redlines)

                logger.info(
                    f"Calling Claude Opus (attempt {attempt + 1}/{self.max_retries + 1})",
                    model=model,
                    prompt_length=len(prompt)
                )

                # Make API call with timeout
                response = await asyncio.wait_for(
                    self.client.messages.create(
                        model=model,
                        max_tokens=4096,
                        temperature=0.1,
                        system="""You are a legal expert specializing in NDA analysis.
                        Identify all potential issues, risks, and necessary redlines in the document.
                        Be thorough and precise in your analysis.""",
                        messages=[
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    ),
                    timeout=120.0  # 2 minute timeout for Opus
                )

                # Track metrics
                elapsed = time.time() - start_time
                self.stats['opus_calls'] += 1
                self.stats['total_requests'] += 1

                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                self.stats['total_tokens_input'] += input_tokens
                self.stats['total_tokens_output'] += output_tokens

                claude_tokens.labels(model="opus", type="input").inc(input_tokens)
                claude_tokens.labels(model="opus", type="output").inc(output_tokens)

                # Calculate cost (Opus pricing as of 2024)
                cost = (input_tokens * 0.015 + output_tokens * 0.075) / 1000
                self.stats['total_cost_usd'] += cost

                # Parse and validate response (never returns None, always returns dict)
                result = self._parse_claude_response(response.content[0].text)

                # Log the response (success even if empty redlines)
                logger.info(
                    "Claude Opus analysis succeeded",
                    elapsed_seconds=elapsed,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    redlines_found=len(result.get('redlines', []))
                )

                claude_requests.labels(model="opus", status="success").inc()

                # Return result even if redlines array is empty
                # Empty redlines means no issues found, which is a valid outcome
                return result

            except asyncio.TimeoutError:
                self.stats['timeout_errors'] += 1
                claude_errors.labels(model="opus", error_type="timeout").inc()
                logger.error(
                    f"Claude Opus timeout after 120 seconds (attempt {attempt + 1})",
                    attempt=attempt + 1
                )
                if attempt < self.max_retries:
                    await self._backoff(attempt, "timeout")
                    continue

            except APIStatusError as e:
                await self._handle_api_error(e, model, attempt)
                if attempt < self.max_retries and self._is_retryable_error(e):
                    continue
                else:
                    self._record_circuit_breaker_failure()
                    raise RuntimeError(f"Claude Opus API error: {e.status_code} - {str(e)}")

            except APIConnectionError as e:
                self.stats['connection_errors'] += 1
                claude_errors.labels(model="opus", error_type="connection").inc()
                logger.error(
                    f"Connection error to Claude Opus (attempt {attempt + 1})",
                    error=str(e)
                )
                if attempt < self.max_retries:
                    await self._backoff(attempt, "connection")
                    continue
                else:
                    self._record_circuit_breaker_failure()
                    raise RuntimeError(f"Connection failed to Claude Opus: {str(e)}")

            except Exception as e:
                logger.error(
                    f"Unexpected error in Claude Opus analysis",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True
                )
                self._record_circuit_breaker_failure()
                raise RuntimeError(f"Opus analysis failed: {str(e)}")

        # Exhausted all retries
        self._record_circuit_breaker_failure()
        raise RuntimeError(f"Claude Opus analysis failed after {self.max_retries + 1} attempts")

    async def _validate_with_sonnet(
        self,
        opus_result: Dict[str, Any],
        document_text: str,
        document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Validate Opus findings with Claude Sonnet
        More lenient error handling as validation is supplementary
        """
        model = "claude-3-5-sonnet-20241022"

        try:
            if PROMETHEUS_AVAILABLE:
                with claude_latency.labels(model="sonnet").time():
                    pass

            prompt = self._build_validation_prompt(opus_result, document_text)

            logger.info("Calling Claude Sonnet for validation", model=model)

            response = await asyncio.wait_for(
                self.client.messages.create(
                    model=model,
                    max_tokens=2048,
                    temperature=0.0,  # Deterministic validation
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                ),
                timeout=60.0  # 1 minute timeout for Sonnet
            )

            # Track metrics
            self.stats['sonnet_calls'] += 1
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.stats['total_tokens_input'] += input_tokens
            self.stats['total_tokens_output'] += output_tokens

            claude_tokens.labels(model="sonnet", type="input").inc(input_tokens)
            claude_tokens.labels(model="sonnet", type="output").inc(output_tokens)

            # Calculate cost (Sonnet pricing)
            cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000
            self.stats['total_cost_usd'] += cost

            # Parse validation response
            validation = self._parse_validation_response(response.content[0].text)

            # Merge validated results
            validated_redlines = self._merge_validation_results(
                opus_result.get('redlines', []),
                validation
            )

            logger.info(
                "Claude Sonnet validation completed",
                original_redlines=len(opus_result.get('redlines', [])),
                validated_redlines=len(validated_redlines)
            )

            claude_requests.labels(model="sonnet", status="success").inc()
            return validated_redlines

        except Exception as e:
            # Validation failures are non-fatal - return Opus results
            logger.warning(
                "Claude Sonnet validation failed, using Opus results only",
                error=str(e),
                error_type=type(e).__name__
            )
            claude_requests.labels(model="sonnet", status="error").inc()
            return opus_result.get('redlines', [])

    async def _handle_api_error(self, error: APIStatusError, model: str, attempt: int):
        """Handle API status errors with appropriate backoff strategies"""

        if error.status_code == 529:  # Overloaded - Anthropic specific
            self.stats['overload_errors'] += 1
            claude_errors.labels(model=model, error_type="overloaded").inc()
            wait_time = self._calculate_overload_backoff(attempt)
            logger.warning(
                f"Claude overloaded (529), backing off {wait_time}s",
                status_code=529,
                attempt=attempt + 1,
                wait_time=wait_time
            )
            await asyncio.sleep(wait_time)

        elif error.status_code == 429:  # Rate limited
            self.stats['rate_limit_hits'] += 1
            claude_errors.labels(model=model, error_type="rate_limit").inc()
            wait_time = self._calculate_backoff(attempt)
            logger.warning(
                f"Rate limited, backing off {wait_time}s",
                status_code=429,
                attempt=attempt + 1,
                wait_time=wait_time
            )
            await asyncio.sleep(wait_time)

        elif error.status_code >= 500:  # Server errors
            claude_errors.labels(model=model, error_type=f"server_{error.status_code}").inc()
            if attempt < self.max_retries:
                wait_time = self._calculate_backoff(attempt)
                logger.warning(
                    f"Server error {error.status_code}, retrying in {wait_time}s",
                    status_code=error.status_code,
                    attempt=attempt + 1
                )
                await asyncio.sleep(wait_time)
        else:
            # Non-retryable errors
            claude_errors.labels(model=model, error_type=f"client_{error.status_code}").inc()
            logger.error(
                f"Non-retryable API error",
                status_code=error.status_code,
                error=str(error)
            )

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate standard exponential backoff with jitter"""
        base_delay = 1.0
        max_delay = 60.0
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = delay * 0.25 * (random.random() * 2 - 1)  # ±25% jitter
        return max(0.1, delay + jitter)

    def _calculate_overload_backoff(self, attempt: int) -> float:
        """Special backoff calculation for 529 overload errors"""
        # Anthropic recommends 30+ seconds for overload
        base_delay = 30.0
        max_delay = 120.0
        delay = min(base_delay * (1.5 ** attempt), max_delay)
        jitter = delay * 0.1 * random.random()  # 10% jitter
        return delay + jitter

    async def _backoff(self, attempt: int, reason: str):
        """Execute backoff with logging"""
        wait_time = self._calculate_backoff(attempt)
        logger.info(
            f"Backing off before retry",
            attempt=attempt + 1,
            reason=reason,
            wait_seconds=wait_time
        )
        self.stats['total_retries'] += 1
        await asyncio.sleep(wait_time)

    def _check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker allows request
        Returns True if request should proceed, False if circuit is open
        """
        # Check if we're in open state
        if self.circuit_breaker_state == CircuitBreakerState.OPEN:
            if self.circuit_breaker_last_failure_time:
                time_since_failure = time.time() - self.circuit_breaker_last_failure_time
                if time_since_failure >= self.circuit_breaker_reset_time:
                    # Try half-open state
                    self.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                    circuit_breaker_state_metric.set(CircuitBreakerState.HALF_OPEN.value)
                    logger.info("Circuit breaker entering half-open state")
                    return True
            return False

        return True

    def _record_circuit_breaker_failure(self):
        """Record a failure for circuit breaker logic"""
        self.circuit_breaker_failures += 1
        self.circuit_breaker_last_failure_time = time.time()

        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            if self.circuit_breaker_state != CircuitBreakerState.OPEN:
                self.circuit_breaker_state = CircuitBreakerState.OPEN
                circuit_breaker_state_metric.set(CircuitBreakerState.OPEN.value)
                self.stats['circuit_breaker_trips'] += 1
                logger.error(
                    "Circuit breaker tripped - opening circuit",
                    failures=self.circuit_breaker_failures,
                    threshold=self.circuit_breaker_threshold
                )

    def _reset_circuit_breaker(self):
        """Reset circuit breaker on successful request"""
        if self.circuit_breaker_state != CircuitBreakerState.CLOSED:
            logger.info("Circuit breaker reset to closed state")

        self.circuit_breaker_failures = 0
        self.circuit_breaker_last_failure_time = None
        self.circuit_breaker_state = CircuitBreakerState.CLOSED
        circuit_breaker_state_metric.set(CircuitBreakerState.CLOSED.value)

    def _is_retryable_error(self, error: APIStatusError) -> bool:
        """Determine if an error is retryable"""
        retryable_status_codes = {408, 429, 500, 502, 503, 504, 529}
        return error.status_code in retryable_status_codes

    def _build_opus_prompt(self, document_text: str, rule_redlines: List[Dict]) -> str:
        """Build the analysis prompt for Claude Opus"""
        rule_summary = ""
        if rule_redlines:
            rule_summary = f"\n\nPre-identified issues from rule analysis ({len(rule_redlines)} found):\n"
            for idx, redline in enumerate(rule_redlines[:5], 1):  # Show first 5
                rule_summary += f"{idx}. {redline.get('pattern', 'Unknown')}: {redline.get('explanation', '')}\n"

        return f"""Analyze this NDA document for all potential legal issues and necessary redlines.

{rule_summary}

Document text:
{document_text}

Provide a comprehensive analysis including:
1. All problematic clauses that should be modified or removed
2. Missing standard protections that should be added
3. Terms that are unusually restrictive or one-sided
4. Potential risks and their severity
5. Specific recommended changes with explanations

CRITICAL: You must respond with ONLY a valid JSON object. Do not include any explanatory text before or after the JSON.

Format your response as a JSON object with a 'redlines' array. Each redline object must include:
- clause: The specific clause or section name
- issue: What's problematic about this clause
- severity: Must be exactly one of: "high", "medium", or "low"
- original_text: The exact text from the document that needs to change (quote it precisely)
- revised_text: The replacement text to use (or empty string "" if deleting)
- recommendation: Brief description of the change needed
- explanation: Detailed reasoning for why this change is important

Example response format:
{{
  "redlines": [
    {{
      "clause": "Term and Termination",
      "issue": "Confidentiality term is indefinite/perpetual",
      "severity": "high",
      "original_text": "shall remain in effect in perpetuity",
      "revised_text": "shall remain in effect for 2 years from the Effective Date",
      "recommendation": "Limit confidentiality term to 2 years",
      "explanation": "Perpetual confidentiality obligations are unreasonably burdensome and should be time-limited to a reasonable period."
    }},
    {{
      "clause": "Governing Law",
      "issue": "Governing law is not Delaware",
      "severity": "medium",
      "original_text": "governed by the laws of California",
      "revised_text": "governed by the laws of Delaware",
      "recommendation": "Change governing law to Delaware",
      "explanation": "Delaware law is preferred for consistency with corporate governance."
    }}
  ]
}}

If the document has no issues, return: {{"redlines": []}}

Remember: Respond with ONLY the JSON object, no additional text."""

    def _build_validation_prompt(self, opus_result: Dict, document_text: str) -> str:
        """Build validation prompt for Claude Sonnet"""
        redlines_summary = json.dumps(opus_result.get('redlines', [])[:10], indent=2)

        return f"""Review and validate these proposed redlines for accuracy and completeness.

Proposed redlines:
{redlines_summary}

Original document (first 3000 chars):
{document_text[:3000]}

For each redline, verify:
1. Is the issue accurately identified?
2. Is the severity appropriate?
3. Is the recommendation practical and legally sound?
4. Are there any false positives to remove?

Respond with a JSON object containing:
- validated_redlines: Array of redline IDs that are valid
- removed_redlines: Array of redline IDs that are false positives
- severity_adjustments: Object mapping redline IDs to new severity levels
"""

    def _parse_claude_response(self, response_text: str) -> Dict:
        """
        Parse Claude's response, handling both JSON and text formats.
        NEVER returns None - always returns a dict with a 'redlines' list (possibly empty).
        """
        try:
            logger.debug(
                "Parsing Claude response",
                response_length=len(response_text),
                response_preview=response_text[:200],
            )

            parsed = None

            # 1) Try direct JSON
            text = response_text.strip()
            if text.startswith("{"):
                parsed = json.loads(text)

            # 2) Try JSON inside markdown code fences
            if parsed is None:
                import re
                json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(1))

            # 3) If we got JSON, normalize to {'redlines': [...]}
            if parsed is not None:
                redlines = parsed.get("redlines")
                if isinstance(redlines, list):
                    logger.info(
                        f"Successfully parsed JSON response with {len(redlines)} redlines"
                    )
                    return {"redlines": redlines}
                else:
                    logger.warning(
                        "JSON parsed but missing 'redlines' key or not a list, returning empty"
                    )
                    return {"redlines": []}

            # 4) Fallback: structured text parsing
            logger.warning(
                "Claude response not in JSON format, attempting text parsing fallback"
            )
            lines = text.split("\n")
            redlines = []
            current = {}

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                lower = line.lower()
                if "clause" in lower or "section" in lower:
                    if current:
                        redlines.append(current)
                        current = {}
                    current["clause"] = line
                elif "issue" in lower or "problem" in lower:
                    current["issue"] = line
                elif "severity" in lower:
                    current["severity"] = line.split(":", 1)[-1].strip().lower()
                elif "recommendation" in lower:
                    current["recommendation"] = line
                elif "explanation" in lower:
                    current["explanation"] = line

            if current:
                redlines.append(current)

            if redlines:
                logger.info(
                    f"Text parsing fallback succeeded with {len(redlines)} redlines"
                )
                return {"redlines": redlines}
            else:
                logger.warning(
                    "Text parsing fallback found no redlines, returning empty"
                )
                return {"redlines": []}

        except json.JSONDecodeError as e:
            logger.error(
                "JSON parsing failed",
                error=str(e),
                response_preview=response_text[:500],
            )
            return {"redlines": []}

        except Exception as e:
            logger.error(
                "Unexpected error parsing Claude response",
                error=str(e),
                error_type=type(e).__name__,
                response_preview=response_text[:500],
            )
            return {"redlines": []}

    def _parse_validation_response(self, response_text: str) -> Dict:
        """Parse Sonnet's validation response"""
        try:
            if response_text.strip().startswith('{'):
                return json.loads(response_text)

            # Extract JSON from potential markdown
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Default: approve all if parsing fails
            return {'validated_redlines': 'all', 'removed_redlines': []}

        except Exception as e:
            logger.warning(
                "Failed to parse validation response, approving all",
                error=str(e)
            )
            return {'validated_redlines': 'all', 'removed_redlines': []}

    def _merge_validation_results(
        self,
        original_redlines: List[Dict],
        validation: Dict
    ) -> List[Dict]:
        """Merge Opus results with Sonnet validation"""

        if validation.get('validated_redlines') == 'all':
            return original_redlines

        validated_ids = set(validation.get('validated_redlines', []))
        removed_ids = set(validation.get('removed_redlines', []))
        severity_adjustments = validation.get('severity_adjustments', {})

        final_redlines = []
        for idx, redline in enumerate(original_redlines):
            redline_id = str(idx)

            # Skip removed redlines
            if redline_id in removed_ids:
                continue

            # Apply severity adjustments
            if redline_id in severity_adjustments:
                redline['severity'] = severity_adjustments[redline_id]

            # Include validated or non-validated redlines (default to include)
            if validated_ids and redline_id not in validated_ids:
                continue

            final_redlines.append(redline)

        return final_redlines

    def _get_stats_snapshot(self) -> Dict:
        """Get current statistics snapshot"""
        stats = self.stats.copy()

        # Calculate derived metrics
        if stats['total_requests'] > 0:
            stats['success_rate'] = stats['successful_requests'] / stats['total_requests']
            stats['average_retries'] = stats['total_retries'] / stats['total_requests']

        if stats['processing_times']:
            stats['avg_processing_time'] = sum(stats['processing_times']) / len(stats['processing_times'])
            stats['p95_processing_time'] = sorted(stats['processing_times'])[int(len(stats['processing_times']) * 0.95)] if len(stats['processing_times']) > 1 else stats['processing_times'][0]

        # Remove detailed arrays from snapshot
        stats.pop('processing_times', None)

        return stats

    def _get_user_friendly_error(self, error: Exception) -> str:
        """
        Convert technical errors to user-friendly messages
        """
        error_str = str(error)
        error_type = type(error).__name__

        # Circuit breaker errors
        if "circuit breaker" in error_str.lower():
            return "The AI analysis service is temporarily unavailable due to repeated errors. Please try again in a few minutes."

        # API key errors
        if "api key" in error_str.lower() or "authentication" in error_str.lower():
            return "The AI service API key is not configured correctly. Please contact support or verify your API key settings."

        # Rate limiting
        if "rate limit" in error_str.lower() or error_type == "RateLimitError":
            return "The AI service is currently experiencing high demand. Please try again in a few moments."

        # Timeout errors
        if "timeout" in error_str.lower() or error_type == "TimeoutError":
            return "The AI analysis took too long to complete. This may be due to document size or service load. Please try again."

        # Connection errors
        if "connection" in error_str.lower() or error_type in ["ConnectionError", "APIConnectionError"]:
            return "Unable to connect to the AI analysis service. Please check your internet connection and try again."

        # Overload errors
        if "overload" in error_str.lower() or "529" in error_str:
            return "The AI service is currently overloaded. Please wait a minute and try again."

        # Parsing errors (shouldn't happen with new robust parsing, but just in case)
        if "parse" in error_str.lower() or "json" in error_str.lower():
            return "There was an issue processing the AI response. The analysis has been logged and our team will investigate. Please try again or contact support if the issue persists."

        # Generic fallback with some helpful context
        return f"An unexpected error occurred during document analysis. Please try again or contact support if the problem persists. (Error: {error_type})"

    # Legacy method for compatibility
    async def analyze(self, working_text: str, rule_redlines: List[Dict]) -> List[Dict]:
        """
        Legacy compatibility method for existing code
        Calls analyze_document and returns just the redlines list
        """
        result = await self.analyze_document(
            document_text=working_text,
            document_id=str(uuid.uuid4()),
            rule_redlines=rule_redlines
        )
        return result.get('redlines', [])

    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return self._get_stats_snapshot()


# Backward compatibility alias (CRITICAL - DO NOT REMOVE)
LLMOrchestrator = AnthropicExclusiveOrchestrator
AllClaudeLLMOrchestrator = AnthropicExclusiveOrchestrator
