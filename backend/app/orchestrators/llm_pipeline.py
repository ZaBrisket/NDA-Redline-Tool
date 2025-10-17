"""
4-Pass LLM Pipeline Orchestrator for NDA Review System
Coordinates Pass 0-4 with enforcement level control
"""

import os
import asyncio
import time
import hashlib
import json
from typing import List, Dict, Optional, Tuple, Any, Set
from datetime import datetime
import logging
from pathlib import Path

# Core imports
try:
    # Try absolute import for Railway deployment
    from backend.app.core.rule_engine_v2 import RuleEngineV2
    from backend.app.core.strictness_controller import EnforcementLevel, StrictnessController
    from backend.app.core.semantic_cache import SemanticCache
except ModuleNotFoundError:
    # Fall back to relative imports for local development
    from ..core.rule_engine_v2 import RuleEngineV2
    from ..core.strictness_controller import EnforcementLevel, StrictnessController
    from ..core.semantic_cache import SemanticCache

# Schema imports
try:
    from backend.app.models.schemas_v2 import (
        ViolationSchema,
        GPT5Response,
        ValidationResult,
        ValidationVerdict,
        AdjudicationRequest,
        AdjudicationResult,
        ConsistencyCheck,
        PipelineRequest,
        PipelineResult,
        PassResult,
        Severity,
        ViolationSource,
        ClauseType
    )
except ModuleNotFoundError:
    from ..models.schemas_v2 import (
        ViolationSchema,
        GPT5Response,
        ValidationResult,
        ValidationVerdict,
        AdjudicationRequest,
        AdjudicationResult,
        ConsistencyCheck,
        PipelineRequest,
        PipelineResult,
        PassResult,
        Severity,
        ViolationSource,
        ClauseType
    )

# LLM client imports
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


class LLMPipelineOrchestrator:
    """
    Main orchestrator for 4-pass LLM pipeline
    Pass 0: Deterministic rules
    Pass 1: GPT-5 recall maximization
    Pass 2: Claude Sonnet validation
    Pass 3: Claude Opus adjudication
    Pass 4: Consistency sweep
    """

    def __init__(self,
                 openai_api_key: Optional[str] = None,
                 anthropic_api_key: Optional[str] = None,
                 enforcement_level: Optional[EnforcementLevel] = None,
                 enable_cache: Optional[bool] = None):
        """Initialize pipeline with API keys and enforcement level"""

        # Get API keys from environment if not provided
        openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        anthropic_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        if not openai_key:
            raise ValueError("OPENAI_API_KEY must be provided or set in environment")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY must be provided or set in environment")

        # API clients
        self.openai_client = AsyncOpenAI(api_key=openai_key)
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_key)

        # Enforcement control - get from env if not provided
        if enforcement_level is None:
            env_level = os.getenv("ENFORCEMENT_LEVEL", "Balanced")
            enforcement_level = EnforcementLevel.from_string(env_level)

        self.enforcement_level = enforcement_level
        self.strictness_controller = StrictnessController(enforcement_level)

        # Pass 0: Rule engine
        self.rule_engine = RuleEngineV2(enforcement_level=enforcement_level)

        # Caching - get from env if not provided
        if enable_cache is None:
            enable_cache = os.getenv("ENABLE_CACHE", "true").lower() == "true"

        self.cache_enabled = enable_cache
        if enable_cache:
            self.cache = SemanticCache()

        # Prompt management
        self.prompts = self._load_prompts()

        # Statistics
        self.stats = {
            'passes_executed': [0, 0, 0, 0, 0],
            'items_processed': 0,
            'cache_hits': 0,
            'total_time_ms': 0
        }

        logger.info(f"Pipeline initialized with {enforcement_level.value} enforcement level")

    def _load_prompts(self) -> Dict:
        """Load prompts for each pass and enforcement level"""
        # This would typically load from a prompts file
        # For now, returning structured prompts
        adjustments = self.strictness_controller.get_prompt_adjustments()

        return {
            'pass1_gpt': {
                'system': f"""You are a {adjustments['stance']} NDA reviewer.
{adjustments['guidance']}
Output strict JSON matching the provided schema.""",
                'temperature': adjustments['temperature']
            },
            'pass2_sonnet': {
                'system': f"""You are validating NDA violations with {adjustments['stance']} standards.
Verdict options: confirm (keep as-is), modify (adjust text), reject (false positive).
{adjustments['guidance']}""",
                'temperature': adjustments['temperature']
            },
            'pass3_opus': {
                'system': """You are the senior adjudicator resolving critical disagreements.
Consider both legal precedent and business pragmatism.
Provide definitive rulings with detailed reasoning.""",
                'temperature': 0.1
            },
            'pass4_consistency': {
                'system': """Check for consistency issues and banned terms.
Ensure no perpetual/indefinite language remains.
Verify required clauses are present.""",
                'temperature': 0.0
            }
        }

    async def execute_pipeline(self, request: PipelineRequest) -> PipelineResult:
        """
        Execute full 4-pass pipeline on document

        Args:
            request: Pipeline request with document and settings

        Returns:
            PipelineResult with all violations and metadata
        """
        start_time = time.time()
        pass_results = []
        violations = []

        try:
            # Check cache first
            if self.cache_enabled and not request.skip_cache:
                cache_key = self._generate_cache_key(request)
                cached = await self.cache.get(cache_key)
                if cached:
                    logger.info(f"Cache hit for document {request.document_id}")
                    self.stats['cache_hits'] += 1
                    return cached

            # Pass 0: Deterministic rules
            violations, pass0_result = await self._execute_pass_0(
                request.document_text,
                violations
            )
            pass_results.append(pass0_result)

            # Check if we should skip Pass 1
            rule_confidence = self.rule_engine.get_confidence_score(violations)
            skip_pass1 = self.strictness_controller.should_skip_llm_pass(
                1, rule_confidence
            )

            # Pass 1: GPT-5 recall maximization
            if not skip_pass1:
                violations, pass1_result = await self._execute_pass_1(
                    request.document_text,
                    violations
                )
                pass_results.append(pass1_result)
            else:
                pass_results.append(PassResult(
                    pass_number=1,
                    pass_name="GPT-5 Recall",
                    violations_in=len(violations),
                    violations_out=len(violations),
                    processing_time_ms=0,
                    skipped=True,
                    skip_reason=f"Rule confidence {rule_confidence:.1f}% sufficient"
                ))

            # Pass 2: Claude Sonnet validation
            violations, pass2_result = await self._execute_pass_2(
                request.document_text,
                violations
            )
            pass_results.append(pass2_result)

            # Pass 3: Opus adjudication for critical items
            needs_adjudication = self._identify_adjudication_candidates(violations)
            if needs_adjudication:
                violations, pass3_result = await self._execute_pass_3(
                    request.document_text,
                    violations,
                    needs_adjudication
                )
                pass_results.append(pass3_result)
            else:
                pass_results.append(PassResult(
                    pass_number=3,
                    pass_name="Opus Adjudication",
                    violations_in=len(violations),
                    violations_out=len(violations),
                    processing_time_ms=0,
                    skipped=True,
                    skip_reason="No critical disagreements"
                ))

            # Pass 4: Consistency sweep
            if not self.strictness_controller.should_skip_llm_pass(4, 0):
                violations, pass4_result = await self._execute_pass_4(
                    request.document_text,
                    violations
                )
                pass_results.append(pass4_result)
            else:
                pass_results.append(PassResult(
                    pass_number=4,
                    pass_name="Consistency Sweep",
                    violations_in=len(violations),
                    violations_out=len(violations),
                    processing_time_ms=0,
                    skipped=True,
                    skip_reason="Disabled for Lenient mode"
                ))

            # Calculate consensus score
            consensus_score = self._calculate_consensus(violations)

            # Prepare final result
            result = PipelineResult(
                document_id=request.document_id,
                enforcement_level=request.enforcement_level,
                total_violations=len(violations),
                violations=violations,
                pass_results=pass_results,
                total_processing_time_ms=int((time.time() - start_time) * 1000),
                cache_hit=False,
                consensus_score=consensus_score,
                summary=self.strictness_controller.format_summary(
                    [v.dict() for v in violations]
                )
            )

            # Cache if eligible
            if self.cache_enabled and self._should_cache(result):
                await self.cache.set(cache_key, result)
                logger.info(f"Cached result for document {request.document_id}")

            return result

        except Exception as e:
            logger.error(f"Pipeline error for document {request.document_id}: {e}")
            raise

    async def _execute_pass_0(self,
                             text: str,
                             existing_violations: List[ViolationSchema]
                             ) -> Tuple[List[ViolationSchema], PassResult]:
        """Execute Pass 0: Deterministic rules"""
        start = time.time()

        rule_violations = self.rule_engine.apply_rules(text)

        # Merge with existing violations
        all_violations = existing_violations + rule_violations

        result = PassResult(
            pass_number=0,
            pass_name="Deterministic Rules",
            violations_in=len(existing_violations),
            violations_out=len(all_violations),
            items_added=len(rule_violations),
            processing_time_ms=int((time.time() - start) * 1000)
        )

        logger.info(f"Pass 0 complete: {len(rule_violations)} violations found")
        return all_violations, result

    async def _execute_pass_1(self,
                             text: str,
                             existing_violations: List[ViolationSchema]
                             ) -> Tuple[List[ViolationSchema], PassResult]:
        """Execute Pass 1: GPT-5 recall maximization with rule gating"""
        start = time.time()
        gpt_violations = []

        # Segment text by clause type
        segments = self._segment_by_clause_type(text)

        # Process each segment
        for segment in segments:
            # Check if we should skip based on existing coverage
            if self._should_skip_segment(segment, existing_violations):
                continue

            # Call GPT-5 with structured output
            try:
                response = await self._call_gpt_structured(
                    segment['text'],
                    segment['clause_type']
                )
                gpt_violations.extend(response.violations)
            except Exception as e:
                logger.error(f"GPT-5 error for segment {segment['clause_type']}: {e}")

        # Merge violations
        all_violations = self._merge_violations(existing_violations, gpt_violations)

        result = PassResult(
            pass_number=1,
            pass_name="GPT-5 Recall",
            violations_in=len(existing_violations),
            violations_out=len(all_violations),
            items_added=len(gpt_violations),
            processing_time_ms=int((time.time() - start) * 1000)
        )

        logger.info(f"Pass 1 complete: {len(gpt_violations)} new violations")
        return all_violations, result

    async def _execute_pass_2(self,
                             text: str,
                             violations: List[ViolationSchema]
                             ) -> Tuple[List[ViolationSchema], PassResult]:
        """Execute Pass 2: Claude Sonnet validation"""
        start = time.time()
        validated_violations = []
        removed = 0
        modified = 0

        # Validate each violation
        for violation in violations:
            validation = await self._validate_with_sonnet(violation, text)

            if validation.verdict == ValidationVerdict.CONFIRM:
                # Keep as-is but adjust confidence
                violation.confidence += validation.confidence_adjustment
                violation.confidence = max(0, min(100, violation.confidence))
                validated_violations.append(violation)

            elif validation.verdict == ValidationVerdict.MODIFY:
                # Modify the violation
                violation.revised_text = validation.modified_text or violation.revised_text
                violation.confidence += validation.confidence_adjustment
                violation.source = ViolationSource.SONNET
                validated_violations.append(violation)
                modified += 1

            else:  # REJECT
                # Don't include in validated list
                removed += 1
                logger.debug(f"Rejected violation {violation.id}: {validation.rationale}")

        result = PassResult(
            pass_number=2,
            pass_name="Sonnet Validation",
            violations_in=len(violations),
            violations_out=len(validated_violations),
            items_removed=removed,
            items_modified=modified,
            processing_time_ms=int((time.time() - start) * 1000)
        )

        logger.info(f"Pass 2 complete: {removed} removed, {modified} modified")
        return validated_violations, result

    async def _execute_pass_3(self,
                             text: str,
                             violations: List[ViolationSchema],
                             candidates: List[ViolationSchema]
                             ) -> Tuple[List[ViolationSchema], PassResult]:
        """Execute Pass 3: Opus critical adjudication"""
        start = time.time()

        # Batch candidates by clause type
        batches = self._batch_by_clause_type(candidates, max_batch_size=5)

        adjudicated = []
        for batch in batches:
            request = AdjudicationRequest(
                violations=batch,
                full_text=text,
                clause_type=batch[0].clause_type,
                priority="critical" if any(v.severity == Severity.CRITICAL for v in batch) else "normal"
            )

            results = await self._adjudicate_with_opus(request)
            adjudicated.extend(results)

        # Apply adjudications to violations
        final_violations = self._apply_adjudications(violations, adjudicated)

        result = PassResult(
            pass_number=3,
            pass_name="Opus Adjudication",
            violations_in=len(violations),
            violations_out=len(final_violations),
            items_modified=len(adjudicated),
            processing_time_ms=int((time.time() - start) * 1000)
        )

        logger.info(f"Pass 3 complete: {len(adjudicated)} items adjudicated")
        return final_violations, result

    async def _execute_pass_4(self,
                             text: str,
                             violations: List[ViolationSchema]
                             ) -> Tuple[List[ViolationSchema], PassResult]:
        """Execute Pass 4: Consistency sweep"""
        start = time.time()

        # Get banned tokens and required clauses
        banned_tokens = self.strictness_controller.get_banned_tokens()
        required_clauses = self.strictness_controller.get_required_clauses()

        # Check consistency
        consistency = await self._check_consistency(
            text,
            violations,
            banned_tokens,
            required_clauses
        )

        # Add new violations for issues found
        new_violations = []
        for issue in consistency.banned_tokens_found:
            violation = ViolationSchema(
                id=hashlib.md5(f"banned_{issue['token']}_{issue['location']}".encode()).hexdigest()[:12],
                clause_type=ClauseType.GENERAL,
                start=issue['location'],
                end=issue['location'] + len(issue['token']),
                original_text=issue['context'],
                revised_text="",  # Delete banned token
                severity=Severity.CRITICAL,
                confidence=100.0,
                source=ViolationSource.CONSISTENCY,
                enforcement_levels=[self.enforcement_level.value],
                suppressed_in=[],
                explanation=f"Banned token '{issue['token']}' found - must be removed",
                legal_risk="High - creates indefinite obligations",
                business_impact="Perpetual confidentiality obligations"
            )
            new_violations.append(violation)

        final_violations = violations + new_violations

        result = PassResult(
            pass_number=4,
            pass_name="Consistency Sweep",
            violations_in=len(violations),
            violations_out=len(final_violations),
            items_added=len(new_violations),
            processing_time_ms=int((time.time() - start) * 1000)
        )

        logger.info(f"Pass 4 complete: {len(new_violations)} consistency issues found")
        return final_violations, result

    # === Helper methods ===

    def _segment_by_clause_type(self, text: str) -> List[Dict]:
        """Segment text by clause type for focused processing"""
        segments = []

        # Simple paragraph-based segmentation for now
        # In production, would use more sophisticated NLP
        paragraphs = text.split('\n\n')

        for para in paragraphs:
            if not para.strip():
                continue

            clause_type = self._identify_clause_type(para)
            segments.append({
                'text': para,
                'clause_type': clause_type,
                'start': text.find(para),
                'end': text.find(para) + len(para)
            })

        return segments

    def _identify_clause_type(self, text: str) -> ClauseType:
        """Identify clause type from text"""
        text_lower = text.lower()

        if 'confidential' in text_lower and ('term' in text_lower or 'period' in text_lower):
            return ClauseType.CONFIDENTIALITY_TERM
        elif 'governing law' in text_lower or 'governed by' in text_lower:
            return ClauseType.GOVERNING_LAW
        elif 'return' in text_lower or 'destroy' in text_lower:
            return ClauseType.DOCUMENT_RETENTION
        elif 'solicit' in text_lower and 'employee' in text_lower:
            return ClauseType.EMPLOYEE_SOLICITATION
        elif 'compete' in text_lower or 'competition' in text_lower:
            return ClauseType.NON_COMPETE
        elif 'injunctive' in text_lower:
            return ClauseType.INJUNCTIVE_RELIEF
        elif 'represent' in text_lower or 'warrant' in text_lower:
            return ClauseType.REPRESENTATIONS
        elif 'indemnif' in text_lower:
            return ClauseType.INDEMNIFICATION
        elif 'assign' in text_lower:
            return ClauseType.ASSIGNMENT
        elif 'jurisdiction' in text_lower or 'venue' in text_lower:
            return ClauseType.JURISDICTION

        return ClauseType.GENERAL

    def _should_skip_segment(self,
                            segment: Dict,
                            existing_violations: List[ViolationSchema]) -> bool:
        """Check if segment can be skipped based on existing coverage"""

        # Count existing violations in this segment
        segment_violations = [
            v for v in existing_violations
            if v.start >= segment['start'] and v.end <= segment['end']
        ]

        # Skip if high coverage from rules
        if len(segment_violations) >= 3:
            return True

        # Skip if critical issues already found
        critical_found = any(v.severity == Severity.CRITICAL for v in segment_violations)
        if critical_found and self.enforcement_level == EnforcementLevel.LENIENT:
            return True

        return False

    async def _call_gpt_structured(self,
                                   text: str,
                                   clause_type: ClauseType) -> GPT5Response:
        """Call GPT-5 with structured output"""

        prompt = self.prompts['pass1_gpt']
        system_message = prompt['system']

        # Create clause-specific prompt
        user_message = f"""Analyze this {clause_type.value} clause for issues:

{text}

Focus on:
- Term limits and duration
- Missing carveouts or exceptions
- Overly broad language
- Unfair or one-sided terms

Return violations in strict JSON format."""

        try:
            # Get model from environment - using GPT-5
            model = os.getenv("GPT_MODEL", "gpt-5")
            max_tokens = int(os.getenv("GPT_MAX_TOKENS", "2000"))

            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=prompt['temperature'],
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )

            # Parse response
            content = json.loads(response.choices[0].message.content)

            # Convert to schema
            return GPT5Response(
                violations=[ViolationSchema(**v) for v in content.get('violations', [])],
                clause_type=clause_type,
                total_reviewed=len(text.split()),
                processing_time_ms=response.usage.total_tokens,
                model_version=model  # Use actual model from environment
            )

        except Exception as e:
            logger.error(f"GPT-5 structured output error: {e}")
            # Return empty response on error
            return GPT5Response(
                violations=[],
                clause_type=clause_type,
                total_reviewed=0,
                processing_time_ms=0
            )

    async def _validate_with_sonnet(self,
                                   violation: ViolationSchema,
                                   full_text: str) -> ValidationResult:
        """Validate a violation with Claude Sonnet"""

        prompt = self.prompts['pass2_sonnet']

        # Get context around violation
        context_start = max(0, violation.start - 200)
        context_end = min(len(full_text), violation.end + 200)
        context = full_text[context_start:context_end]

        message = f"""Review this flagged violation:

CONTEXT: {context}

FLAGGED TEXT: {violation.original_text}
SUGGESTED REVISION: {violation.revised_text}
REASON: {violation.explanation}
SEVERITY: {violation.severity}

Is this a valid issue? Options:
- CONFIRM: Yes, this is a real issue
- MODIFY: Issue exists but needs different fix
- REJECT: False positive, not an issue

Provide verdict and detailed rationale."""

        try:
            # Get model from environment
            model = os.getenv("SONNET_MODEL", "claude-3-5-sonnet-20241022")
            max_tokens = int(os.getenv("SONNET_MAX_TOKENS", "1500"))

            response = await self.anthropic_client.messages.create(
                model=model,
                messages=[{"role": "user", "content": message}],
                system=prompt['system'],
                temperature=prompt['temperature'],
                max_tokens=max_tokens
            )

            # Parse response (simplified for example)
            content = response.content[0].text

            # Extract verdict (would use better parsing in production)
            if "CONFIRM" in content.upper():
                verdict = ValidationVerdict.CONFIRM
            elif "MODIFY" in content.upper():
                verdict = ValidationVerdict.MODIFY
            elif "REJECT" in content.upper():
                verdict = ValidationVerdict.REJECT
            else:
                verdict = ValidationVerdict.CONFIRM  # Default

            return ValidationResult(
                violation_id=violation.id,
                original_violation=violation,
                verdict=verdict,
                rationale=content,
                confidence_adjustment=0.0 if verdict == ValidationVerdict.CONFIRM else -10.0,
                modified_text=violation.revised_text if verdict == ValidationVerdict.MODIFY else None
            )

        except Exception as e:
            logger.error(f"Sonnet validation error: {e}")
            # Default to confirming on error
            return ValidationResult(
                violation_id=violation.id,
                original_violation=violation,
                verdict=ValidationVerdict.CONFIRM,
                rationale="Validation error - defaulting to confirm",
                confidence_adjustment=0.0
            )

    def _identify_adjudication_candidates(self,
                                         violations: List[ViolationSchema]) -> List[ViolationSchema]:
        """Identify violations needing Opus adjudication"""
        candidates = []

        for violation in violations:
            should_route = self.strictness_controller.should_route_to_opus(
                violation.confidence,
                violation.severity.value,
                has_disagreement=False  # Would track this in production
            )

            if should_route:
                candidates.append(violation)

        return candidates

    def _batch_by_clause_type(self,
                             violations: List[ViolationSchema],
                             max_batch_size: int = 5) -> List[List[ViolationSchema]]:
        """Batch violations by clause type"""
        batches = {}

        for violation in violations:
            clause_type = violation.clause_type
            if clause_type not in batches:
                batches[clause_type] = []
            batches[clause_type].append(violation)

        # Split large batches
        final_batches = []
        for clause_violations in batches.values():
            for i in range(0, len(clause_violations), max_batch_size):
                final_batches.append(clause_violations[i:i + max_batch_size])

        return final_batches

    async def _adjudicate_with_opus(self,
                                   request: AdjudicationRequest) -> List[AdjudicationResult]:
        """Get Opus adjudication for violations"""

        prompt = self.prompts['pass3_opus']

        # Build adjudication prompt
        violations_text = "\n".join([
            f"- {v.original_text} -> {v.revised_text} (Confidence: {v.confidence}%)"
            for v in request.violations
        ])

        message = f"""Senior adjudication required for {request.clause_type.value} violations:

{violations_text}

Full context:
{request.full_text[:1000]}...

Provide definitive ruling for each violation with detailed legal reasoning."""

        try:
            # Get model from environment
            model = os.getenv("OPUS_MODEL", "claude-3-opus-20240229")
            max_tokens = int(os.getenv("OPUS_MAX_TOKENS", "2000"))

            response = await self.anthropic_client.messages.create(
                model=model,
                messages=[{"role": "user", "content": message}],
                system=prompt['system'],
                temperature=prompt['temperature'],
                max_tokens=max_tokens
            )

            # Parse response (simplified)
            content = response.content[0].text

            # Create adjudication results
            results = []
            for violation in request.violations:
                results.append(AdjudicationResult(
                    violation_id=violation.id,
                    final_verdict="confirm",
                    final_confidence=95.0,
                    final_text=violation.revised_text,
                    reasoning=f"Opus adjudication: {content[:200]}"
                ))

            return results

        except Exception as e:
            logger.error(f"Opus adjudication error: {e}")
            return []

    def _apply_adjudications(self,
                            violations: List[ViolationSchema],
                            adjudications: List[AdjudicationResult]) -> List[ViolationSchema]:
        """Apply adjudication results to violations"""

        # Create lookup
        adj_map = {a.violation_id: a for a in adjudications}

        final = []
        for violation in violations:
            if violation.id in adj_map:
                adj = adj_map[violation.id]
                if adj.final_verdict == "confirm":
                    violation.confidence = adj.final_confidence
                    violation.revised_text = adj.final_text
                    violation.source = ViolationSource.OPUS
                    final.append(violation)
                # Skip if rejected
            else:
                final.append(violation)

        return final

    async def _check_consistency(self,
                                text: str,
                                violations: List[ViolationSchema],
                                banned_tokens: List[str],
                                required_clauses: Set[str]) -> ConsistencyCheck:
        """Check document consistency"""

        banned_found = []
        text_lower = text.lower()

        # Check for banned tokens
        for token in banned_tokens:
            if token.lower() in text_lower:
                # Find all occurrences
                import re
                pattern = re.compile(re.escape(token), re.IGNORECASE)
                for match in pattern.finditer(text):
                    banned_found.append({
                        'token': token,
                        'location': match.start(),
                        'context': text[max(0, match.start()-20):min(len(text), match.end()+20)]
                    })

        # Check for required clauses (simplified)
        missing_clauses = []
        for clause in required_clauses:
            clause_found = False
            # Simple keyword check (would use NLP in production)
            if clause == "term_limit" and "months" not in text_lower and "years" not in text_lower:
                missing_clauses.append(clause)
            elif clause == "confidentiality_definition" and "confidential information" not in text_lower:
                missing_clauses.append(clause)
            # Add more clause checks...

        return ConsistencyCheck(
            banned_tokens_found=banned_found,
            missing_required_clauses=missing_clauses,
            style_inconsistencies=[],
            cross_reference_errors=[],
            needs_correction=bool(banned_found or missing_clauses)
        )

    def _merge_violations(self,
                         existing: List[ViolationSchema],
                         new: List[ViolationSchema]) -> List[ViolationSchema]:
        """Merge violations, avoiding duplicates"""

        # Create position-based key for deduplication
        seen = set()
        merged = []

        for v in existing + new:
            key = f"{v.start}_{v.end}_{v.severity}"
            if key not in seen:
                seen.add(key)
                merged.append(v)

        return sorted(merged, key=lambda v: v.start)

    def _calculate_consensus(self, violations: List[ViolationSchema]) -> float:
        """Calculate consensus score for violations"""

        if not violations:
            return 100.0

        # Average confidence across all violations
        total_confidence = sum(v.confidence for v in violations)
        avg_confidence = total_confidence / len(violations)

        # Adjust based on source diversity
        sources = set(v.source for v in violations)
        source_bonus = len(sources) * 5  # 5% per unique source

        consensus = min(100.0, avg_confidence + source_bonus)
        return round(consensus, 1)

    def _generate_cache_key(self, request: PipelineRequest) -> str:
        """Generate cache key for request"""

        # Hash the document text
        text_hash = hashlib.sha256(request.document_text.encode()).hexdigest()[:16]

        return f"pipeline_v2:{self.enforcement_level.value}:{text_hash}"

    def _should_cache(self, result: PipelineResult) -> bool:
        """Determine if result should be cached"""

        return self.strictness_controller.get_cache_eligibility(
            result.consensus_score,
            all_passes_complete=not any(p.skipped for p in result.pass_results)
        )

    def get_statistics(self) -> Dict:
        """Get pipeline statistics"""
        return {
            'enforcement_level': self.enforcement_level.value,
            'passes_executed': self.stats['passes_executed'],
            'total_items_processed': self.stats['items_processed'],
            'cache_hit_rate': (
                self.stats['cache_hits'] / self.stats['items_processed']
                if self.stats['items_processed'] > 0 else 0
            ),
            'average_time_ms': (
                self.stats['total_time_ms'] / self.stats['items_processed']
                if self.stats['items_processed'] > 0 else 0
            )
        }
