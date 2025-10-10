"""
FastAPI backend for NDA automated redlining
"""
import os
import sys
import logging
from pathlib import Path

# Configure logging before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, Response
import uuid
import asyncio
import json
from typing import Optional

from .models.schemas import (
    UploadResponse,
    JobStatusResponse,
    BatchDecision,
    JobStatus,
    ErrorResponse
)
from .workers.document_worker import job_queue
from .api import batch
from .core.telemetry import metrics_endpoint, get_performance_monitor
from .middleware.security import (
    SecurityMiddleware,
    limiter,
    apply_rate_limit,
    validate_file_upload,
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


# Create FastAPI app
app = FastAPI(
    title="NDA Automated Redlining API",
    description="Production-grade NDA review with Word track changes",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
enable_api_keys = os.getenv("ENABLE_API_KEYS", "false").lower() == "true"
app.add_middleware(SecurityMiddleware, enable_api_keys=enable_api_keys)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include batch API router
app.include_router(batch.router)

# Performance monitor
monitor = get_performance_monitor()

# Storage paths
STORAGE_PATH = Path("./storage")
UPLOAD_PATH = STORAGE_PATH / "uploads"
EXPORT_PATH = STORAGE_PATH / "exports"

# Ensure directories exist
UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
EXPORT_PATH.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Run startup checks and log system status"""
    logger.info("="*60)
    logger.info("NDA Automated Redlining - Starting Up")
    logger.info("="*60)

    # Check Python version
    logger.info(f"Python version: {sys.version}")

    # Check critical dependencies
    try:
        import sqlite3
        logger.info(f"✓ SQLite3 module available (version: {sqlite3.sqlite_version})")
    except ImportError as e:
        logger.error(f"✗ SQLite3 module NOT available: {e}")
        logger.warning("  Semantic cache will be disabled")

    # Check optional dependencies
    try:
        import numpy
        logger.info(f"✓ NumPy available (version: {numpy.__version__})")
    except ImportError:
        logger.warning("✗ NumPy NOT available - semantic cache disabled")

    try:
        import faiss
        logger.info(f"✓ FAISS available")
    except ImportError:
        logger.warning("✗ FAISS NOT available - semantic cache disabled")

    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"✓ SentenceTransformers available")
    except ImportError as e:
        logger.warning(f"✗ SentenceTransformers NOT available: {e}")

    # Check environment variables
    required_env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    for var in required_env_vars:
        if os.getenv(var):
            logger.info(f"✓ {var} configured")
        else:
            logger.error(f"✗ {var} NOT configured")

    # Log cache status
    cache_enabled = os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() == "true"
    logger.info(f"Semantic cache: {'enabled' if cache_enabled else 'disabled'} (via env)")

    logger.info("="*60)
    logger.info("Startup complete - Ready to accept requests")
    logger.info("="*60)


@app.get("/")
async def root():
    """Health check with dependency status"""
    # Check dependencies
    dependencies_status = {}

    try:
        import sqlite3
        dependencies_status['sqlite3'] = {'available': True, 'version': sqlite3.sqlite_version}
    except ImportError:
        dependencies_status['sqlite3'] = {'available': False, 'error': 'Import failed'}

    try:
        import numpy
        dependencies_status['numpy'] = {'available': True, 'version': numpy.__version__}
    except ImportError:
        dependencies_status['numpy'] = {'available': False}

    try:
        import faiss
        dependencies_status['faiss'] = {'available': True}
    except ImportError:
        dependencies_status['faiss'] = {'available': False}

    try:
        from sentence_transformers import SentenceTransformer
        dependencies_status['sentence_transformers'] = {'available': True}
    except ImportError:
        dependencies_status['sentence_transformers'] = {'available': False}

    # Check if cache is enabled
    cache_enabled = False
    try:
        from .core.semantic_cache import get_semantic_cache
        cache = get_semantic_cache()
        cache_enabled = cache.enabled if cache else False
    except:
        pass

    return {
        "service": "NDA Automated Redlining",
        "version": "1.0.0",
        "status": "operational",
        "cache_enabled": cache_enabled,
        "dependencies": dependencies_status,
        "warnings": [
            "Semantic cache disabled - LLM costs will be higher"
        ] if not cache_enabled else []
    }


@app.post("/api/upload", response_model=UploadResponse)
@apply_rate_limit("10 per minute")
@validate_file_upload(max_size_mb=50)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload an NDA document for processing.

    Returns job_id for tracking progress.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.docx'):
            raise HTTPException(
                status_code=400,
                detail="Only .docx files are supported"
            )

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Save uploaded file
        file_path = UPLOAD_PATH / f"{job_id}_{file.filename}"

        with file_path.open("wb") as f:
            content = await file.read()
            f.write(content)

        # Submit to job queue
        await job_queue.submit_job(job_id, str(file_path), file.filename)

        return UploadResponse(
            job_id=job_id,
            filename=file.filename,
            status="queued",
            message="Document uploaded and queued for processing"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get current status of a job"""
    job = job_queue.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        'job_id': job_id,
        'status': job['status'],
        'progress': job.get('progress', 0),
        'filename': job.get('filename'),
        'created_at': job['created_at'].isoformat() if job.get('created_at') else None,
        'updated_at': job['updated_at'].isoformat() if job.get('updated_at') else None
    }

    # Include results if complete
    if job.get('result'):
        response['redlines'] = job['result'].get('redlines', [])
        response['total_redlines'] = job['result'].get('total_redlines', 0)
        response['rule_redlines'] = job['result'].get('rule_redlines', 0)
        response['llm_redlines'] = job['result'].get('llm_redlines', 0)
        response['output_path'] = job['result'].get('output_path')

    if job.get('error_message'):
        response['error_message'] = job['error_message']

    return response


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    """
    Server-sent events for real-time job updates.

    Client connects to this endpoint to receive live status updates.
    """
    async def event_generator():
        """Generate SSE events"""
        last_status = None

        while True:
            job = job_queue.get_job_status(job_id)

            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            current_status = {
                'status': job['status'],
                'progress': job.get('progress', 0),
                'updated_at': job['updated_at'].isoformat() if job.get('updated_at') else None
            }

            # Only send if changed
            if current_status != last_status:
                yield f"data: {json.dumps(current_status)}\n\n"
                last_status = current_status

            # Check if job is complete or errored
            if job['status'] in [JobStatus.COMPLETE, JobStatus.ERROR]:
                if job.get('result'):
                    final_data = {
                        'status': job['status'],
                        'progress': 100,
                        'redlines': job['result'].get('redlines', []),
                        'total_redlines': job['result'].get('total_redlines', 0),
                        'output_path': job['result'].get('output_path')
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"

                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/jobs/{job_id}/decisions")
async def submit_decisions(job_id: str, decisions: BatchDecision):
    """
    Submit user decisions on redlines (accept/reject).

    Allows user to review and approve/reject each proposed change.
    """
    job = job_queue.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update decisions
    for decision in decisions.decisions:
        job_queue.update_redline_decision(
            job_id,
            decision.redline_id,
            decision.decision
        )

    return {"message": "Decisions recorded", "count": len(decisions.decisions)}


@app.get("/api/jobs/{job_id}/download")
async def download_redlined(job_id: str, final: bool = False):
    """
    Download the redlined document.

    Args:
        final: If True, export with only accepted changes
    """
    job = job_queue.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job['status'] != JobStatus.COMPLETE:
        raise HTTPException(status_code=400, detail="Job not complete")

    if final:
        # Export with only accepted changes
        output_path = await job_queue.export_final_document(job_id)
        filename_suffix = "final"
    else:
        # Original redlined document with all changes
        output_path = Path(job['result']['output_path'])
        filename_suffix = "redlined"

    if not output_path or not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{job['filename'].replace('.docx', '')}_{filename_suffix}.docx"
    )


@app.get("/api/stats")
async def get_stats():
    """Get processing statistics with performance metrics"""
    # Aggregate stats from all jobs
    jobs = job_queue.jobs.values()

    total = len(jobs)
    complete = sum(1 for j in jobs if j['status'] == JobStatus.COMPLETE)
    error = sum(1 for j in jobs if j['status'] == JobStatus.ERROR)

    total_redlines = 0
    for job in jobs:
        if job.get('result'):
            total_redlines += job['result'].get('total_redlines', 0)

    # Get performance metrics
    perf_metrics = await monitor.get_metrics_summary()

    return {
        'total_documents': total,
        'successful': complete,
        'failed': error,
        'total_redlines': total_redlines,
        'avg_redlines_per_doc': total_redlines / complete if complete > 0 else 0,
        'performance': perf_metrics
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return await metrics_endpoint()


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its files"""
    job = job_queue.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete files
    try:
        file_path = Path(job['file_path'])
        if file_path.exists():
            file_path.unlink()

        if job.get('result') and job['result'].get('output_path'):
            output_path = Path(job['result']['output_path'])
            if output_path.exists():
                output_path.unlink()

        # Remove from queue
        del job_queue.jobs[job_id]

        return {"message": "Job deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
