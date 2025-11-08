"""
FastAPI backend for NDA automated redlining
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import uuid
import asyncio
import json
import os
from typing import Optional

from .models.schemas import (
    UploadResponse,
    JobStatusResponse,
    BatchDecision,
    JobStatus,
    ErrorResponse
)
from .workers.document_worker import job_queue

# Setup Railway-optimized logging FIRST
from .core.logger import setup_railway_logging, get_logger

# Configure logging with proper stream routing for Railway
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
setup_railway_logging(log_level)
logger = get_logger(__name__)

# Import V2 API router
try:
    from .api.v2_endpoints import router as v2_router
    V2_AVAILABLE = True
except ImportError as e:
    logger.warning(f"V2 endpoints not available: {e}")
    V2_AVAILABLE = False


# Import worker state management
from .core.state import worker_state

# Modern FastAPI lifespan context manager (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events using modern lifespan pattern
    Optimized for Gunicorn multi-worker deployments
    """
    worker_id = os.getpid()

    # Startup
    logger.info(
        "=== Worker Startup ===",
        extra={"extra_fields": {"worker_pid": worker_id}}
    )
    logger.info("Starting NDA Automated Redlining API worker")

    # Log environment info (once per worker)
    logger.info(
        "Worker environment",
        extra={"extra_fields": {
            "worker_pid": worker_id,
            "port": os.getenv('PORT', '8000'),
            "railway_env": os.getenv('RAILWAY_ENVIRONMENT_NAME', 'development'),
            "log_level": os.getenv('LOG_LEVEL', 'INFO')
        }}
    )

    # Initialize worker state with orchestrator
    api_key = os.getenv("ANTHROPIC_API_KEY")
    initialization_success = await worker_state.initialize(api_key)

    if initialization_success:
        # Store reference in app.state for backward compatibility
        app.state.orchestrator = worker_state.orchestrator
        logger.info(
            "Worker orchestrator initialized successfully",
            extra={"extra_fields": {"worker_pid": worker_id}}
        )
    else:
        # Degraded mode - service starts but API calls will fail
        app.state.orchestrator = None
        logger.warning(
            "Worker starting in degraded mode - ANTHROPIC_API_KEY not configured",
            extra={"extra_fields": {"worker_pid": worker_id}}
        )

    # Log configuration (once per worker)
    logger.info(
        "Worker configuration",
        extra={"extra_fields": {
            "worker_pid": worker_id,
            "max_file_size_mb": int(os.getenv('MAX_FILE_SIZE_MB', 50)),
            "retention_days": os.getenv('RETENTION_DAYS', 7),
            "validation_rate": os.getenv('VALIDATION_RATE', '0.15'),
            "confidence_threshold": os.getenv('CONFIDENCE_THRESHOLD', '95'),
            "orchestrator_ready": initialization_success
        }}
    )

    logger.info(
        "Worker startup complete",
        extra={"extra_fields": {"worker_pid": worker_id}}
    )

    yield  # Application runs here

    # Shutdown
    logger.info(
        "=== Worker Shutdown ===",
        extra={"extra_fields": {"worker_pid": worker_id}}
    )

    # Get worker stats before cleanup
    worker_stats = worker_state.get_stats()
    logger.info(
        "Worker statistics",
        extra={"extra_fields": worker_stats}
    )

    # Cleanup worker state
    await worker_state.cleanup()

    # Cleanup any pending jobs (only if this worker owns them)
    try:
        from .models.schemas import JobStatus
        pending_jobs = [job for job in job_queue.jobs.values() if job.get('status') == JobStatus.QUEUED]
        if pending_jobs:
            logger.warning(
                f"Cancelling {len(pending_jobs)} pending jobs on shutdown",
                extra={"extra_fields": {"worker_pid": worker_id}}
            )
            for job in pending_jobs:
                job['status'] = JobStatus.ERROR
                job['error_message'] = "Server shutdown before processing"

    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}")

    logger.info(
        "Worker shutdown complete",
        extra={"extra_fields": {"worker_pid": worker_id}}
    )


# Create FastAPI app with modern lifespan
app = FastAPI(
    title="NDA Automated Redlining API",
    description="All-Claude NDA review system with 100% validation (Claude Opus + Sonnet)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
# Parse allowed origins from environment variable
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8000"
).split(",")

# Clean up whitespace from origins
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]

# Validate origins
for origin in ALLOWED_ORIGINS:
    if origin == "*":
        logger.warning("WARNING: Using wildcard (*) for CORS origins with credentials is a security risk!")
        if os.getenv("ENVIRONMENT") == "production":
            raise ValueError("CORS wildcard origin not allowed in production with credentials enabled")

# CORS middleware with secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Explicit allowed origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],  # Only required methods
    allow_headers=["Content-Type", "Authorization"],  # Only required headers
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Register V2 API router if available
if V2_AVAILABLE:
    app.include_router(v2_router)
    logger.info("V2 API endpoints registered")

# Storage paths
STORAGE_PATH = Path("./storage")
UPLOAD_PATH = STORAGE_PATH / "uploads"
EXPORT_PATH = STORAGE_PATH / "exports"

# Ensure directories exist
UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
EXPORT_PATH.mkdir(parents=True, exist_ok=True)

# File upload configuration
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))  # 50MB default
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for streaming


# Dependency injection for orchestrator access
def get_orchestrator(request: Request):
    """
    Dependency injection to access orchestrator from app.state

    Raises:
        HTTPException: 503 if orchestrator not initialized
    """
    if not hasattr(request.app.state, "orchestrator"):
        raise HTTPException(
            status_code=503,
            detail="Service not ready - orchestrator not initialized"
        )

    if request.app.state.orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Service in degraded mode - ANTHROPIC_API_KEY not configured"
        )

    return request.app.state.orchestrator


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NDA Automated Redlining",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint for Railway deployment verification.

    Returns 200 if service is running (even in degraded mode).
    This allows Railway health checks to pass while still indicating configuration status.

    Checks:
    - Service is running
    - Worker state and orchestrator initialization
    - API key configuration status
    """
    from datetime import datetime

    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "architecture": "all-claude",
        "worker_pid": os.getpid(),
        "checks": {
            "service_running": True
        }
    }

    # Check worker state
    if worker_state.initialized:
        health_data["checks"]["orchestrator"] = "initialized"
        health_data["checks"]["api_key"] = "configured"
        health_data["worker_stats"] = worker_state.get_stats()
    elif hasattr(request.app.state, "orchestrator"):
        # Fallback to legacy check for compatibility
        if request.app.state.orchestrator is not None:
            health_data["checks"]["orchestrator"] = "initialized"
            health_data["checks"]["api_key"] = "configured"
        else:
            health_data["status"] = "degraded"
            health_data["checks"]["orchestrator"] = "not_initialized"
            health_data["checks"]["api_key"] = "not_configured"
            health_data["message"] = "Service in degraded mode - ANTHROPIC_API_KEY not configured. Configure in Railway dashboard."
    else:
        health_data["status"] = "degraded"
        health_data["checks"]["orchestrator"] = "missing"
        health_data["message"] = "Service starting up - orchestrator not yet initialized"

    return health_data


@app.get("/ready")
async def readiness_check(request: Request):
    """
    Kubernetes-style readiness check.

    Returns 200 only if service is fully operational with API keys configured.
    Returns 503 if in degraded mode without API keys.
    """
    if not hasattr(request.app.state, "orchestrator"):
        raise HTTPException(
            status_code=503,
            detail="Not ready - orchestrator not initialized"
        )

    if request.app.state.orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Not ready - API key not configured"
        )

    return {
        "status": "ready",
        "orchestrator": "initialized",
        "api_configured": True
    }


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename to prevent path traversal attacks and handle reserved names.

    Handles:
    - Path traversal attempts
    - Null bytes
    - Unsafe characters
    - Windows reserved names (COM1, LPT1, CON, PRN, AUX, NUL, etc.)
    - Length limits
    """
    # Remove path components
    filename = os.path.basename(filename)

    # Remove null bytes
    filename = filename.replace('\0', '')

    # Remove unsafe characters
    unsafe_chars = '<>:"|?*\\'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')

    # Check for Windows reserved names
    # Reserved names: CON, PRN, AUX, NUL, COM1-COM9, LPT1-LPT9
    # Can appear with or without extension (e.g., "CON" or "CON.txt")
    windows_reserved = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }

    name_without_ext = os.path.splitext(filename)[0].upper()
    if name_without_ext in windows_reserved:
        # Prefix with underscore to make it safe
        filename = f"safe_{filename}"

    # Limit length
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length-len(ext)] + ext

    # Prevent empty filenames
    if not filename or filename.strip() == '':
        filename = 'document.docx'

    return filename


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload an NDA document for processing with size limits and validation.

    Returns job_id for tracking progress.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.docx'):
            raise HTTPException(
                status_code=400,
                detail="Only .docx files are supported"
            )

        # Sanitize filename to prevent path traversal
        safe_filename = sanitize_filename(file.filename)

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Check file size before reading (seek to end and back)
        # Note: This is a workaround as file.file is a SpooledTemporaryFile
        try:
            # Read first 4 bytes to check DOCX magic (ZIP header)
            header = await file.read(4)
            if header != b'PK\x03\x04':
                raise HTTPException(
                    status_code=400,
                    detail="Invalid .docx file format (not a valid ZIP archive)"
                )

            # Reset file position
            await file.seek(0)

        except Exception as e:
            logger.error(f"Error checking file header: {e}")
            raise HTTPException(
                status_code=400,
                detail="Unable to read file header"
            )

        # Save uploaded file with streaming and size check
        file_path = UPLOAD_PATH / f"{job_id}_{safe_filename}"

        try:
            bytes_read = 0

            with file_path.open("wb") as f:
                # Stream file in chunks to avoid loading entire file in memory
                while True:
                    chunk = await file.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    bytes_read += len(chunk)

                    # Check size limit
                    if bytes_read > MAX_FILE_SIZE:
                        # Delete partially written file
                        f.close()
                        file_path.unlink()
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB, received {bytes_read/1024/1024:.1f}MB"
                        )

                    f.write(chunk)

            # Log file size
            logger.info(f"Uploaded file {job_id}: {bytes_read/1024/1024:.2f}MB")

            # Verify path is still within UPLOAD_PATH (defense in depth)
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(UPLOAD_PATH.resolve())):
                file_path.unlink()
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            # Clean up partial file if it exists
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Error saving file: {str(e)}"
            )

        # Submit to job queue
        await job_queue.submit_job(job_id, str(file_path), safe_filename)

        return UploadResponse(
            job_id=job_id,
            filename=safe_filename,
            status="queued",
            message="Document uploaded and queued for processing"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get current status of a job with proper validation"""
    job = job_queue.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Validate required fields exist
    if 'status' not in job:
        logger.error(f"Job {job_id} missing 'status' field: {list(job.keys())}")
        raise HTTPException(
            status_code=500,
            detail="Job data corrupted - missing status field"
        )

    # Safely build response with null checks
    response = {
        'job_id': job_id,
        'status': job.get('status', JobStatus.ERROR),  # Fallback to ERROR if somehow missing
        'progress': job.get('progress', 0),
        'filename': job.get('filename')
    }

    # Handle datetime fields safely
    if 'created_at' in job and job['created_at'] is not None:
        try:
            response['created_at'] = job['created_at'].isoformat()
        except (AttributeError, TypeError) as e:
            logger.warning(f"Invalid created_at for job {job_id}: {job['created_at']}")
            response['created_at'] = None
    else:
        response['created_at'] = None

    if 'updated_at' in job and job['updated_at'] is not None:
        try:
            response['updated_at'] = job['updated_at'].isoformat()
        except (AttributeError, TypeError) as e:
            logger.warning(f"Invalid updated_at for job {job_id}: {job['updated_at']}")
            response['updated_at'] = None
    else:
        response['updated_at'] = None

    # Include results if complete
    if job.get('result'):
        result = job['result']
        response['redlines'] = result.get('redlines', [])
        response['total_redlines'] = result.get('total_redlines', 0)
        response['rule_redlines'] = result.get('rule_redlines', 0)
        response['llm_redlines'] = result.get('llm_redlines', 0)
        response['output_path'] = result.get('output_path')

    # Include error message if present
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
    try:
        logger.info(f"Download request for job_id={job_id}, final={final}")

        job = job_queue.get_job_status(job_id)

        if not job:
            logger.error(f"Job not found: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        # Log detailed job status
        logger.info(f"Job {job_id} status: {job.get('status')}, "
                   f"filename: {job.get('filename')}, "
                   f"has_result: {bool(job.get('result'))}")

        if job.get('result'):
            result = job['result']
            logger.info(f"Job {job_id} redlines: total={result.get('total_redlines', 0)}, "
                       f"rule_based={result.get('rule_redlines', 0)}, "
                       f"llm={result.get('llm_redlines', 0)}")

        if job['status'] != JobStatus.COMPLETE:
            logger.error(f"Job {job_id} not complete. Status: {job.get('status')}, "
                        f"Error: {job.get('error', 'N/A')}")
            raise HTTPException(
                status_code=400,
                detail=f"Job not complete. Status: {job['status']}"
            )

        if final:
            # Export with only accepted changes
            logger.info(f"Exporting final document for job {job_id}")
            output_path = await job_queue.export_final_document(job_id)
            filename_suffix = "final"
        else:
            # Original redlined document with all changes
            if not job.get('result') or 'output_path' not in job['result']:
                logger.error(f"Job {job_id} missing result or output_path. Result keys: {list(job.get('result', {}).keys())}")
                raise HTTPException(
                    status_code=500,
                    detail="Job result missing output path"
                )

            output_path = Path(job['result']['output_path'])
            filename_suffix = "redlined"

        logger.info(f"Output path for job {job_id}: {output_path}, exists={output_path.exists() if output_path else False}")

        if not output_path or not output_path.exists():
            logger.error(f"Output file not found for job {job_id}: {output_path}")
            raise HTTPException(status_code=404, detail="Output file not found")

        logger.info(f"Serving file for job {job_id}: {output_path}")
        return FileResponse(
            path=str(output_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{job['filename'].replace('.docx', '')}_{filename_suffix}.docx"
        )

    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in download endpoint for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing download: {str(e)}"
        )


@app.get("/api/stats")
async def get_stats():
    """Get processing statistics"""
    # Aggregate stats from all jobs
    jobs = job_queue.jobs.values()

    total = len(jobs)
    complete = sum(1 for j in jobs if j['status'] == JobStatus.COMPLETE)
    error = sum(1 for j in jobs if j['status'] == JobStatus.ERROR)

    total_redlines = 0
    for job in jobs:
        if job.get('result'):
            total_redlines += job['result'].get('total_redlines', 0)

    return {
        'total_documents': total,
        'successful': complete,
        'failed': error,
        'total_redlines': total_redlines,
        'avg_redlines_per_doc': total_redlines / complete if complete > 0 else 0
    }


@app.post("/api/test/patterns")
async def test_patterns(sample_text: str):
    """
    Test pattern matching on sample text for debugging.

    This endpoint helps diagnose why patterns aren't matching.
    """
    from .core.rule_engine import RuleEngine

    # Initialize rule engine
    rule_engine = RuleEngine()

    # Apply rules to sample text
    logger.info(f"Testing patterns on text: {sample_text[:100]}...")
    redlines = rule_engine.apply_rules(sample_text)

    # Get detailed results
    results = {
        'input_text': sample_text,
        'text_length': len(sample_text),
        'total_rules': len(rule_engine.rules),
        'redlines_found': len(redlines),
        'redlines': redlines,
        'rules_tested': []
    }

    # Test each rule individually for debugging
    for rule in rule_engine.rules:
        if 'compiled_pattern' in rule:
            pattern = rule['compiled_pattern']
            matches = list(pattern.finditer(sample_text))

            rule_info = {
                'rule_id': rule.get('id', 'unknown'),
                'pattern': rule.get('pattern', ''),
                'matches_found': len(matches),
                'match_positions': [(m.start(), m.end(), m.group(0)) for m in matches[:3]]  # First 3 matches
            }
            results['rules_tested'].append(rule_info)

    return results


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
