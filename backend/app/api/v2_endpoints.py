"""
V2 API Endpoints for 4-Pass LLM Pipeline
Integrates with the new enforcement level system
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse
import asyncio
from datetime import datetime
import io

from ..orchestrators.llm_pipeline import LLMPipelineOrchestrator
from ..core.strictness_controller import EnforcementLevel
from ..models.schemas_v2 import (
    PipelineRequest,
    PipelineResult,
    BatchRequest,
    BatchResult,
    ExportRequest
)
from docx import Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["v2"])

# Initialize pipeline orchestrator (singleton)
_pipeline_instance = None

def get_pipeline() -> LLMPipelineOrchestrator:
    """Get or create pipeline instance"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = LLMPipelineOrchestrator()
    return _pipeline_instance


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    enforcement_level: Optional[str] = Form(None)
):
    """
    Analyze a single document with 4-pass pipeline

    Args:
        file: Document to analyze (DOCX, PDF, TXT)
        enforcement_level: Optional - Bloody, Balanced, or Lenient

    Returns:
        PipelineResult with violations and metadata
    """
    try:
        # Validate file type
        allowed_extensions = {'.docx', '.pdf', '.txt', '.md'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not supported. Use: {allowed_extensions}"
            )

        # Read file content
        content = await file.read()

        # Extract text based on file type
        if file_ext == '.docx':
            doc = Document(io.BytesIO(content))
            text = '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
        elif file_ext == '.pdf':
            # PDF extraction would go here
            raise HTTPException(status_code=501, detail="PDF support coming soon")
        else:
            text = content.decode('utf-8')

        # Get enforcement level
        if enforcement_level:
            try:
                level = EnforcementLevel.from_string(enforcement_level)
            except:
                level = EnforcementLevel.from_string(
                    os.getenv("ENFORCEMENT_LEVEL", "Balanced")
                )
        else:
            level = EnforcementLevel.from_string(
                os.getenv("ENFORCEMENT_LEVEL", "Balanced")
            )

        # Create pipeline request
        request = PipelineRequest(
            document_text=text,
            document_id=f"doc_{datetime.now().timestamp()}",
            enforcement_level=level.value,
            filename=file.filename
        )

        # Get pipeline instance
        pipeline = get_pipeline()

        # Execute pipeline
        result = await pipeline.execute_pipeline(request)

        # Return result
        return JSONResponse(content=result.dict())

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/batch")
async def analyze_batch(batch_request: BatchRequest):
    """
    Analyze multiple documents in parallel

    Args:
        batch_request: Batch of documents to process

    Returns:
        BatchResult with all results
    """
    try:
        pipeline = get_pipeline()

        # Process documents in parallel (respecting max_concurrent)
        tasks = []
        for doc_request in batch_request.documents:
            task = pipeline.execute_pipeline(doc_request)
            tasks.append(task)

        # Wait for all with concurrency limit
        max_concurrent = batch_request.max_concurrent
        results = []
        errors = []

        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    errors.append({
                        'document_id': batch_request.documents[i + idx].document_id,
                        'error': str(result)
                    })
                    if not batch_request.continue_on_error:
                        raise result
                else:
                    results.append(result)

        # Create batch result
        batch_result = BatchResult(
            total_documents=len(batch_request.documents),
            successful=len(results),
            failed=len(errors),
            results=results,
            errors=errors,
            total_time_ms=sum(r.total_processing_time_ms for r in results),
            average_time_ms=sum(r.total_processing_time_ms for r in results) / len(results) if results else 0
        )

        return JSONResponse(content=batch_result.dict())

    except Exception as e:
        logger.error(f"Batch analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modes")
async def get_enforcement_modes():
    """Get available enforcement modes and their descriptions"""
    return {
        "modes": {
            "Bloody": {
                "name": "Bloody",
                "description": "Zero tolerance - flags all issues including style and formatting",
                "severities": ["critical", "high", "moderate", "low", "advisory"]
            },
            "Balanced": {
                "name": "Balanced",
                "description": "Professional standard - focuses on material legal issues",
                "severities": ["critical", "high", "moderate"]
            },
            "Lenient": {
                "name": "Lenient",
                "description": "Business-friendly - only flags critical deal-breakers",
                "severities": ["critical"]
            }
        },
        "current": os.getenv("ENFORCEMENT_LEVEL", "Balanced")
    }


@router.post("/export/{document_id}")
async def export_results(
    document_id: str,
    export_request: ExportRequest
):
    """
    Export analysis results in various formats

    Args:
        document_id: ID of analyzed document
        export_request: Export configuration

    Returns:
        Exported file
    """
    try:
        # In production, would retrieve from cache/database
        # For now, return error
        raise HTTPException(
            status_code=501,
            detail="Export functionality requires result storage - coming soon"
        )

    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_pipeline_statistics():
    """Get pipeline performance statistics"""
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_statistics()

        # Add rule engine stats
        rule_stats = pipeline.rule_engine.get_statistics()
        stats['rule_engine'] = rule_stats

        return JSONResponse(content=stats)

    except Exception as e:
        logger.error(f"Statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/v2")
async def health_check_v2():
    """Enhanced health check for v2 pipeline"""
    try:
        pipeline = get_pipeline()

        # Check each component
        checks = {
            "api_keys": {
                "openai": bool(os.getenv("OPENAI_API_KEY")),
                "anthropic": bool(os.getenv("ANTHROPIC_API_KEY"))
            },
            "enforcement_level": os.getenv("ENFORCEMENT_LEVEL", "Balanced"),
            "cache_enabled": os.getenv("ENABLE_CACHE", "true").lower() == "true",
            "passes_enabled": {
                "pass_0": os.getenv("ENABLE_PASS_0", "true").lower() == "true",
                "pass_1": os.getenv("ENABLE_PASS_1", "true").lower() == "true",
                "pass_2": os.getenv("ENABLE_PASS_2", "true").lower() == "true",
                "pass_3": os.getenv("ENABLE_PASS_3", "true").lower() == "true",
                "pass_4": os.getenv("ENABLE_PASS_4", "true").lower() == "true"
            },
            "models_configured": {
                "gpt": os.getenv("GPT_MODEL", "gpt-5"),
                "sonnet": os.getenv("SONNET_MODEL", "claude-3-5-sonnet-20241022"),
                "opus": os.getenv("OPUS_MODEL", "claude-3-opus-20240229")
            }
        }

        # Overall status
        all_keys_present = all(checks["api_keys"].values())
        status = "healthy" if all_keys_present else "degraded"

        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "checks": checks
        }

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/test")
async def test_pipeline():
    """Test the pipeline with sample text"""
    try:
        sample_text = """
        This Non-Disclosure Agreement is entered into as of today.

        The obligations of the Receiving Party shall survive in perpetuity
        and continue indefinitely. The Receiving Party shall indemnify and
        hold harmless the Disclosing Party from any breach.

        This Agreement shall be governed by the laws of Singapore.
        """

        # Create request
        request = PipelineRequest(
            document_text=sample_text,
            document_id="test_doc",
            enforcement_level=os.getenv("ENFORCEMENT_LEVEL", "Balanced"),
            filename="test.txt"
        )

        # Execute
        pipeline = get_pipeline()
        result = await pipeline.execute_pipeline(request)

        return {
            "message": "Pipeline test successful",
            "violations_found": result.total_violations,
            "enforcement_level": result.enforcement_level,
            "passes_executed": [p.pass_name for p in result.pass_results if not p.skipped],
            "critical_issues": len([v for v in result.violations if v.severity == "critical"])
        }

    except Exception as e:
        logger.error(f"Test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))