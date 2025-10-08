"""
Pydantic models for API requests/responses and job state
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job processing states"""
    QUEUED = "queued"
    PARSING = "parsing"
    APPLYING_RULES = "applying_rules"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETE = "complete"
    ERROR = "error"


class RedlineSeverity(str, Enum):
    """Severity levels for redlines"""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class RedlineSource(str, Enum):
    """Source of redline"""
    RULE = "rule"
    GPT5 = "gpt5"
    CLAUDE = "claude"


class ProcessingStrategy(str, Enum):
    """Strategy for processing aggressiveness"""
    LIGHT = "light"  # 5 redlines max - only critical issues
    BALANCED = "balanced"  # 15 redlines max - critical + high priority
    AGGRESSIVE = "aggressive"  # 30 redlines max - all issues
    COMPREHENSIVE = "comprehensive"  # 50+ redlines - for review only


class DealSize(str, Enum):
    """Deal size categories"""
    SMALL = "small"  # <$10M
    MEDIUM = "medium"  # $10-100M
    LARGE = "large"  # $100M-1B
    MEGA = "mega"  # >$1B


class RelationshipType(str, Enum):
    """Relationship with counterparty"""
    NEW = "new"  # First time interaction
    EXISTING = "existing"  # Ongoing relationship
    STRATEGIC = "strategic"  # Key strategic partner
    PORTFOLIO = "portfolio"  # Portfolio company


class RiskTolerance(str, Enum):
    """Risk tolerance for this deal"""
    CONSERVATIVE = "conservative"  # Minimize all risks
    MODERATE = "moderate"  # Balance risk and deal momentum
    AGGRESSIVE = "aggressive"  # Prioritize deal closure


class DealContext(BaseModel):
    """Context about the deal to inform redlining strategy"""
    deal_size: Optional[DealSize] = Field(None, description="Estimated deal size")
    relationship_type: Optional[RelationshipType] = Field(None, description="Type of relationship with counterparty")
    industry: Optional[str] = Field(None, description="Industry sector (e.g., technology, healthcare, manufacturing)")
    risk_tolerance: Optional[RiskTolerance] = Field(RiskTolerance.MODERATE, description="Risk tolerance for this deal")
    timeline_pressure: Optional[bool] = Field(False, description="Whether there is timeline pressure to close quickly")
    notes: Optional[str] = Field(None, description="Additional context notes")

    def get_recommended_strategy(self) -> ProcessingStrategy:
        """Recommend processing strategy based on context"""

        # High-value deals or strategic relationships -> more thorough
        if self.deal_size in [DealSize.LARGE, DealSize.MEGA]:
            return ProcessingStrategy.BALANCED

        # Strategic partners -> lighter touch
        if self.relationship_type == RelationshipType.STRATEGIC:
            return ProcessingStrategy.LIGHT

        # Timeline pressure -> lighter touch
        if self.timeline_pressure:
            return ProcessingStrategy.LIGHT

        # Conservative risk tolerance -> more thorough
        if self.risk_tolerance == RiskTolerance.CONSERVATIVE:
            return ProcessingStrategy.AGGRESSIVE

        # Aggressive risk tolerance -> lighter touch
        if self.risk_tolerance == RiskTolerance.AGGRESSIVE:
            return ProcessingStrategy.LIGHT

        # Default to balanced
        return ProcessingStrategy.BALANCED


class RedlineModel(BaseModel):
    """A single redline/track change"""
    id: str = Field(description="Unique redline ID")
    rule_id: Optional[str] = Field(None, description="Rule ID if from RuleEngine")
    clause_type: str = Field(description="Type of clause")
    start: int = Field(description="Start position in working text")
    end: int = Field(description="End position in working text")
    original_text: str = Field(description="Original text to be changed")
    revised_text: str = Field(description="Replacement text")
    severity: RedlineSeverity = Field(description="Severity level")
    confidence: float = Field(ge=0, le=100, description="Confidence score")
    source: RedlineSource = Field(description="Source of redline")
    explanation: Optional[str] = Field(None, description="Reasoning for change")
    validated: bool = Field(default=False, description="Whether validated by Claude")
    user_decision: Optional[Literal["accept", "reject"]] = Field(None, description="User's decision")


class JobInfo(BaseModel):
    """Job information and state"""
    job_id: str
    filename: str
    status: JobStatus
    progress: float = Field(ge=0, le=100, description="Progress percentage")
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    # Results
    total_redlines: int = 0
    rule_redlines: int = 0
    llm_redlines: int = 0
    redlines: List[RedlineModel] = []

    # Output
    output_path: Optional[str] = None


class UploadRequest(BaseModel):
    """Request for document upload with optional context"""
    deal_context: Optional[DealContext] = Field(None, description="Optional deal context to inform redlining strategy")
    strategy_override: Optional[ProcessingStrategy] = Field(None, description="Optional strategy override (overrides context-based recommendation)")


class UploadResponse(BaseModel):
    """Response from document upload"""
    job_id: str
    filename: str
    status: str
    message: str
    strategy_used: Optional[ProcessingStrategy] = Field(None, description="Strategy that will be used for processing")


class RedlineDecision(BaseModel):
    """User decision on a redline"""
    redline_id: str
    decision: Literal["accept", "reject"]


class BatchDecision(BaseModel):
    """Batch decisions from user"""
    decisions: List[RedlineDecision]


class JobStatusResponse(BaseModel):
    """Job status update"""
    job_id: str
    status: JobStatus
    progress: float
    message: Optional[str] = None
    redlines: Optional[List[RedlineModel]] = None
    output_path: Optional[str] = None


class ProcessingStats(BaseModel):
    """Statistics about processing"""
    total_documents: int = 0
    successful: int = 0
    failed: int = 0
    avg_redlines_per_doc: float = 0
    avg_processing_time: float = 0

    # LLM stats
    gpt_calls: int = 0
    claude_calls: int = 0
    validations: int = 0
    conflicts: int = 0

    # Cost tracking
    estimated_cost_per_doc: float = 0


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    job_id: Optional[str] = None
