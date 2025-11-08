"""
Enhanced Schemas for NDA Review System v2
Structured Output contracts for 4-pass LLM pipeline
"""

from pydantic import BaseModel, Field, validator, model_validator
from typing import Literal, List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# =====================================================
# ENUMS AND CONSTANTS
# =====================================================

class Severity(str, Enum):
    """Severity levels for violations"""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    ADVISORY = "advisory"


class ViolationSource(str, Enum):
    """Source of violation detection"""
    RULE = "rule"           # Pass 0: Deterministic rules
    GPT5 = "gpt5"          # Pass 1: Claude Opus recall
    SONNET = "sonnet"      # Pass 2: Claude Sonnet validation
    OPUS = "opus"          # Pass 3: Claude Opus adjudication
    CONSISTENCY = "consistency"  # Pass 4: Consistency sweep


class ClauseType(str, Enum):
    """Types of clauses in NDAs"""
    CONFIDENTIALITY_TERM = "confidentiality_term"
    GOVERNING_LAW = "governing_law"
    DOCUMENT_RETENTION = "document_retention"
    EMPLOYEE_SOLICITATION = "employee_solicitation"
    NON_COMPETE = "non_compete"
    INJUNCTIVE_RELIEF = "injunctive_relief"
    REPRESENTATIONS = "representations"
    INDEMNIFICATION = "indemnification"
    ASSIGNMENT = "assignment"
    JURISDICTION = "jurisdiction"
    SURVIVAL = "survival"
    PURPOSE_LIMITATION = "purpose_limitation"
    GENERAL = "general"


class ValidationVerdict(str, Enum):
    """Validation verdicts for Pass 2"""
    CONFIRM = "confirm"    # Confirm the violation
    MODIFY = "modify"     # Modify the violation
    REJECT = "reject"     # Reject as false positive


# =====================================================
# CORE VIOLATION SCHEMA
# =====================================================

class ViolationSchema(BaseModel):
    """Core schema for violations - used across all passes"""

    # Identification
    id: str = Field(description="Unique identifier for this violation")
    clause_type: ClauseType
    rule_id: Optional[str] = Field(None, description="Rule ID if from deterministic rules")

    # Location in document
    start: int = Field(ge=0, description="Start character position")
    end: int = Field(ge=0, description="End character position")
    line_number: Optional[int] = Field(None, ge=1, description="Line number if available")
    paragraph: Optional[str] = Field(None, description="Paragraph/section reference")

    # Content
    original_text: str = Field(min_length=1, description="Original text flagged")
    revised_text: str = Field(description="Suggested revision")
    context: Optional[str] = Field(None, description="Surrounding context")

    # Classification
    severity: Severity
    confidence: float = Field(ge=0, le=100, description="Confidence percentage")
    source: ViolationSource

    # Enforcement
    enforcement_levels: List[str] = Field(description="Which enforcement levels flag this")
    suppressed_in: List[str] = Field(default_factory=list, description="Modes that suppress this")

    # Metadata
    explanation: str = Field(description="Human-readable explanation")
    legal_risk: Optional[str] = Field(None, description="Legal risk description")
    business_impact: Optional[str] = Field(None, description="Business impact description")

    @validator('confidence')
    def round_confidence(cls, v):
        """Round confidence to 1 decimal place"""
        return round(v, 1)

    @validator('enforcement_levels', 'suppressed_in')
    def validate_enforcement_levels(cls, v):
        """Ensure enforcement levels are valid"""
        valid = {"Bloody", "Balanced", "Lenient"}
        for level in v:
            if level not in valid:
                raise ValueError(f"Invalid enforcement level: {level}")
        return v

    class Config:
        use_enum_values = True


# =====================================================
# PASS-SPECIFIC SCHEMAS
# =====================================================

# Pass 0: Deterministic Rules
class RuleMatch(BaseModel):
    """Result from deterministic rule matching"""
    rule_id: str
    pattern: str
    matched_text: str
    action: Literal["replace", "delete", "add_after", "add_inline", "suggest"]
    replacement: Optional[str] = None
    confidence: float = Field(default=100.0, description="Rules have 100% confidence")


# Pass 1: Claude Opus Structured Output
class GPT5Response(BaseModel):
    """Structured response from Claude Opus (released August 2025)"""
    violations: List[ViolationSchema]
    clause_type: ClauseType
    total_reviewed: int = Field(ge=0)
    processing_time_ms: int = Field(ge=0)
    model_version: str = Field(default="claude-3-opus-20240229")  # Claude Opus default

    @model_validator(mode="after")
    def validate_violations(self):
        """Ensure all violations match clause type"""
        if not self.violations:
            return self

        coerced = []
        for violation in self.violations:
            if violation.clause_type == self.clause_type:
                coerced.append(violation)
            else:
                coerced.append(
                    violation.model_copy(update={"clause_type": self.clause_type})
                )
        self.violations = coerced
        return self


# Pass 2: Claude Sonnet Validation
class ValidationResult(BaseModel):
    """Result from Claude Sonnet validation"""
    violation_id: str
    original_violation: ViolationSchema
    verdict: ValidationVerdict
    rationale: str = Field(min_length=10, description="Detailed rationale")
    confidence_adjustment: float = Field(ge=-20, le=20, description="Confidence adjustment")
    modified_text: Optional[str] = Field(None, description="Modified suggestion if verdict is MODIFY")
    additional_context: Optional[str] = None
    false_positive_reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_modification(self):
        """Ensure modified_text exists when verdict is MODIFY"""
        if self.verdict == ValidationVerdict.MODIFY and not self.modified_text:
            raise ValueError("modified_text required when verdict is MODIFY")
        return self


# Pass 3: Claude Opus Adjudication
class AdjudicationRequest(BaseModel):
    """Request for Opus adjudication"""
    violations: List[ViolationSchema]
    full_text: str
    clause_type: ClauseType
    disagreement_reason: Optional[str] = None
    priority: Literal["critical", "high", "normal"] = "normal"


class AdjudicationResult(BaseModel):
    """Result from Opus adjudication"""
    violation_id: str
    final_verdict: Literal["confirm", "reject", "split"]
    final_confidence: float = Field(ge=0, le=100)
    final_text: str
    reasoning: str = Field(min_length=20)
    precedent_considered: Optional[str] = None
    minority_opinion: Optional[str] = None


# Pass 4: Consistency Sweep
class ConsistencyCheck(BaseModel):
    """Consistency check results"""
    banned_tokens_found: List[Dict[str, Any]]
    missing_required_clauses: List[str]
    style_inconsistencies: List[Dict[str, str]]
    cross_reference_errors: List[Dict[str, str]]
    needs_correction: bool

    class Config:
        json_schema_extra = {
            "example": {
                "banned_tokens_found": [
                    {"token": "perpetual", "location": 1234, "context": "...perpetual confidentiality..."}
                ],
                "missing_required_clauses": ["term_limit", "return_provision"],
                "style_inconsistencies": [
                    {"issue": "capitalization", "found": "confidential information", "expected": "Confidential Information"}
                ],
                "cross_reference_errors": [],
                "needs_correction": True
            }
        }


# =====================================================
# PIPELINE ORCHESTRATION SCHEMAS
# =====================================================

class PipelineRequest(BaseModel):
    """Request to process document through pipeline"""
    document_text: str
    document_id: str
    enforcement_level: Literal["Bloody", "Balanced", "Lenient"]
    filename: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    skip_cache: bool = Field(default=False)
    parallel_modes: bool = Field(default=False, description="Run all enforcement modes")


class PassResult(BaseModel):
    """Result from a single pass"""
    pass_number: int = Field(ge=0, le=4)
    pass_name: str
    violations_in: int
    violations_out: int
    items_added: int = 0
    items_removed: int = 0
    items_modified: int = 0
    processing_time_ms: int
    skipped: bool = False
    skip_reason: Optional[str] = None


class PipelineResult(BaseModel):
    """Final result from entire pipeline"""
    document_id: str
    enforcement_level: str
    total_violations: int
    violations: List[ViolationSchema]
    pass_results: List[PassResult]
    total_processing_time_ms: int
    cache_hit: bool = False
    consensus_score: float = Field(ge=0, le=100)
    summary: Dict[str, Any]

    @validator('consensus_score')
    def round_consensus(cls, v):
        """Round consensus to 1 decimal place"""
        return round(v, 1)


# =====================================================
# CACHING SCHEMAS
# =====================================================

class CacheKey(BaseModel):
    """Cache key for semantic caching"""
    ruleset_version: str
    prompt_version: str
    enforcement_level: str
    content_hash: str
    clause_type: Optional[ClauseType] = None


class CacheEntry(BaseModel):
    """Cache entry for validated results"""
    key: CacheKey
    violations: List[ViolationSchema]
    consensus_score: float
    timestamp: datetime
    hit_count: int = 0
    last_accessed: datetime
    embedding: Optional[List[float]] = Field(None, description="FAISS embedding")


# =====================================================
# BATCH PROCESSING SCHEMAS
# =====================================================

class BatchRequest(BaseModel):
    """Batch processing request"""
    documents: List[PipelineRequest]
    parallel: bool = Field(default=True)
    max_concurrent: int = Field(default=3, ge=1, le=10)
    continue_on_error: bool = Field(default=True)


class BatchResult(BaseModel):
    """Batch processing result"""
    total_documents: int
    successful: int
    failed: int
    results: List[PipelineResult]
    errors: List[Dict[str, str]]
    total_time_ms: int
    average_time_ms: float


# =====================================================
# MONITORING SCHEMAS
# =====================================================

class PassMetrics(BaseModel):
    """Metrics for each pass"""
    pass_name: str
    invocations: int
    skip_count: int
    average_time_ms: float
    p95_time_ms: float
    error_rate: float
    cache_hit_rate: float


class SystemMetrics(BaseModel):
    """Overall system metrics"""
    uptime_seconds: int
    documents_processed: int
    total_violations_found: int
    pass_metrics: List[PassMetrics]
    enforcement_level_distribution: Dict[str, int]
    average_consensus_score: float
    cache_size: int
    memory_usage_mb: float


# =====================================================
# ERROR SCHEMAS
# =====================================================

class PipelineError(BaseModel):
    """Error during pipeline processing"""
    error_type: str
    error_message: str
    pass_number: Optional[int] = None
    document_id: Optional[str] = None
    traceback: Optional[str] = None
    recoverable: bool = True


# =====================================================
# PROMPT MANAGEMENT SCHEMAS
# =====================================================

class PromptTemplate(BaseModel):
    """Template for LLM prompts"""
    pass_number: int
    model: str
    enforcement_level: str
    clause_type: Optional[ClauseType] = None
    template: str
    temperature: float = Field(ge=0, le=1)
    max_tokens: Optional[int] = None
    system_message: Optional[str] = None


# =====================================================
# EXPORT SCHEMAS
# =====================================================

class ExportRequest(BaseModel):
    """Request to export results"""
    format: Literal["docx", "pdf", "json", "markdown"]
    include_original: bool = True
    include_redlines: bool = True
    include_summary: bool = True
    track_changes: bool = True


class ExportResult(BaseModel):
    """Export result"""
    filename: str
    format: str
    size_bytes: int
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None

