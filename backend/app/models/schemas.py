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


class UploadResponse(BaseModel):
    """Response from document upload"""
    job_id: str
    filename: str
    status: str
    message: str


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
