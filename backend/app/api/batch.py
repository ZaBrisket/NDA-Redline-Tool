"""
Batch Processing API for Multiple NDA Documents
Implements intelligent deduplication and streaming results for massive cost reduction
"""

import os
import json
import uuid
import asyncio
import hashlib
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import aiofiles
from docx import Document

from ..core.semantic_cache import get_semantic_cache
from ..core.text_indexer import WorkingTextIndexer
from ..core.rule_engine import RuleEngine
from ..core.llm_orchestrator import LLMOrchestrator
from ..workers.redis_job_queue import RedisJobQueue, JobPriority
from ..models.schemas import JobStatus

router = APIRouter(prefix="/api/batch", tags=["batch"])


class BatchProcessor:
    """
    Handles batch document processing with intelligent deduplication.
    Processes unique clauses once and applies results across all documents.
    """

    def __init__(self):
        self.semantic_cache = get_semantic_cache()
        self.rule_engine = RuleEngine()
        self.llm_orchestrator = LLMOrchestrator()
        self.storage_path = Path("./storage")
        self.max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "100"))

    async def process_batch(
        self,
        batch_id: str,
        file_paths: List[str],
        callback=None
    ) -> Dict[str, Any]:
        """
        Process multiple NDAs with clause deduplication.

        Args:
            batch_id: Unique batch identifier
            file_paths: List of document paths
            callback: Progress callback function

        Returns:
            Batch processing results
        """
        start_time = datetime.now()
        results = []
        total_clauses = 0
        unique_clauses = 0
        cache_hits = 0

        try:
            # Phase 1: Extract all clauses from all documents
            await self._update_callback(
                callback,
                batch_id,
                "extracting",
                0,
                f"Extracting clauses from {len(file_paths)} documents..."
            )

            all_clauses = []
            document_clauses_map = {}

            for idx, file_path in enumerate(file_paths):
                doc_clauses = await self._extract_document_clauses(file_path)
                all_clauses.extend(doc_clauses)
                document_clauses_map[file_path] = doc_clauses

                progress = (idx + 1) / len(file_paths) * 20
                await self._update_callback(
                    callback,
                    batch_id,
                    "extracting",
                    progress,
                    f"Extracted clauses from document {idx + 1}/{len(file_paths)}"
                )

            total_clauses = len(all_clauses)

            # Phase 2: Deduplicate clauses using semantic similarity
            await self._update_callback(
                callback,
                batch_id,
                "deduplicating",
                20,
                f"Deduplicating {total_clauses} clauses..."
            )

            unique_clause_map = await self._deduplicate_clauses(all_clauses)
            unique_clauses = len(unique_clause_map)

            await self._update_callback(
                callback,
                batch_id,
                "deduplicating",
                30,
                f"Found {unique_clauses} unique clauses (reduction: {100 - (unique_clauses/total_clauses*100):.1f}%)"
            )

            # Phase 3: Process unique clauses with caching
            await self._update_callback(
                callback,
                batch_id,
                "analyzing",
                30,
                f"Analyzing {unique_clauses} unique clauses..."
            )

            clause_results = {}

            for idx, (clause_hash, clause_data) in enumerate(unique_clause_map.items()):
                # Check cache first
                cached = await self.semantic_cache.search(
                    clause_data['text'],
                    context={'batch': batch_id}
                )

                if cached:
                    clause_results[clause_hash] = cached['response']
                    cache_hits += 1
                else:
                    # Process with LLM
                    result = await self._process_clause(clause_data)
                    clause_results[clause_hash] = result

                    # Store in cache
                    await self.semantic_cache.store(
                        clause_data['text'],
                        result,
                        context={'batch': batch_id},
                        cost=0.03
                    )

                progress = 30 + (idx + 1) / unique_clauses * 40
                await self._update_callback(
                    callback,
                    batch_id,
                    "analyzing",
                    progress,
                    f"Analyzed {idx + 1}/{unique_clauses} unique clauses (cache hits: {cache_hits})"
                )

            # Phase 4: Apply results to all documents
            await self._update_callback(
                callback,
                batch_id,
                "applying",
                70,
                "Applying analysis results to all documents..."
            )

            for idx, file_path in enumerate(file_paths):
                doc_result = await self._apply_results_to_document(
                    file_path,
                    document_clauses_map[file_path],
                    clause_results,
                    unique_clause_map
                )

                results.append(doc_result)

                progress = 70 + (idx + 1) / len(file_paths) * 30
                await self._update_callback(
                    callback,
                    batch_id,
                    "applying",
                    progress,
                    f"Processed document {idx + 1}/{len(file_paths)}"
                )

            # Calculate metrics
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # Calculate cost savings
            actual_cost = (unique_clauses - cache_hits) * 0.03
            without_dedup_cost = total_clauses * 0.03
            cost_saved = without_dedup_cost - actual_cost
            cost_reduction = (cost_saved / without_dedup_cost * 100) if without_dedup_cost > 0 else 0

            batch_result = {
                'batch_id': batch_id,
                'status': 'completed',
                'documents_processed': len(file_paths),
                'total_clauses': total_clauses,
                'unique_clauses': unique_clauses,
                'cache_hits': cache_hits,
                'deduplication_ratio': f"{100 - (unique_clauses/total_clauses*100):.1f}%",
                'cost_reduction': f"{cost_reduction:.1f}%",
                'actual_cost': f"${actual_cost:.2f}",
                'cost_saved': f"${cost_saved:.2f}",
                'processing_time': f"{processing_time:.2f}s",
                'results': results
            }

            await self._update_callback(
                callback,
                batch_id,
                "completed",
                100,
                f"Batch processing complete. Cost reduced by {cost_reduction:.1f}%"
            )

            return batch_result

        except Exception as e:
            await self._update_callback(
                callback,
                batch_id,
                "error",
                -1,
                f"Error: {str(e)}"
            )
            raise

    async def _extract_document_clauses(self, file_path: str) -> List[Dict]:
        """Extract clauses from a single document."""
        doc = Document(file_path)
        indexer = WorkingTextIndexer()
        indexer.build_index(doc)

        # Use LLM orchestrator's clause extraction
        clauses = self.llm_orchestrator._extract_clauses(indexer.working_text)

        # Add document reference
        for clause in clauses:
            clause['document'] = file_path
            clause['hash'] = hashlib.md5(clause['text'].encode()).hexdigest()

        return clauses

    async def _deduplicate_clauses(
        self,
        clauses: List[Dict]
    ) -> Dict[str, Dict]:
        """
        Deduplicate clauses using semantic similarity.

        Returns:
            Dictionary mapping clause hash to unique clause data
        """
        unique_clauses = {}
        processed_embeddings = []

        for clause in clauses:
            clause_text = clause['text']
            clause_hash = clause['hash']

            # Check if exact match exists
            if clause_hash in unique_clauses:
                # Add document reference
                unique_clauses[clause_hash]['documents'].append(clause['document'])
                continue

            # Check semantic similarity with existing clauses
            is_duplicate = False

            if processed_embeddings:
                embedding = await self.semantic_cache.get_embedding(clause_text)

                for existing_hash, existing_data in unique_clauses.items():
                    existing_embedding = existing_data.get('embedding')

                    if existing_embedding is not None:
                        # Calculate cosine similarity
                        similarity = float(embedding @ existing_embedding)

                        if similarity > 0.92:  # High similarity threshold
                            # Mark as duplicate
                            existing_data['documents'].append(clause['document'])
                            is_duplicate = True
                            break

            if not is_duplicate:
                # Add as unique clause
                embedding = await self.semantic_cache.get_embedding(clause_text)
                unique_clauses[clause_hash] = {
                    'text': clause_text,
                    'documents': [clause['document']],
                    'embedding': embedding,
                    'original_clause': clause
                }
                processed_embeddings.append(embedding)

        return unique_clauses

    async def _process_clause(self, clause_data: Dict) -> Dict:
        """Process a single unique clause with LLM."""
        clause_text = clause_data['text']

        # Apply rule engine first
        rule_redlines = self.rule_engine.apply_rules(clause_text)

        # LLM analysis
        llm_redlines = await self.llm_orchestrator._analyze_clause_with_gpt5(
            clause_text,
            0,
            clause_text
        )

        return {
            'rule_redlines': rule_redlines,
            'llm_redlines': llm_redlines,
            'total_redlines': len(rule_redlines) + len(llm_redlines)
        }

    async def _apply_results_to_document(
        self,
        file_path: str,
        doc_clauses: List[Dict],
        clause_results: Dict,
        unique_clause_map: Dict
    ) -> Dict:
        """Apply processing results to a document."""
        doc_name = Path(file_path).name
        all_redlines = []

        # Map results back to document positions
        for clause in doc_clauses:
            clause_hash = clause['hash']

            # Find corresponding result
            result = None
            for unique_hash, unique_data in unique_clause_map.items():
                if file_path in unique_data['documents']:
                    # Check if this clause matches
                    if clause_hash == unique_hash or \
                       await self._is_similar_clause(clause['text'], unique_data['text']):
                        result = clause_results.get(unique_hash)
                        break

            if result:
                # Adjust positions for document
                for redline in result.get('rule_redlines', []):
                    redline['start'] += clause['start']
                    redline['end'] += clause['start']
                    all_redlines.append(redline)

                for redline in result.get('llm_redlines', []):
                    redline['start'] += clause['start']
                    redline['end'] += clause['start']
                    all_redlines.append(redline)

        return {
            'document': doc_name,
            'file_path': file_path,
            'total_redlines': len(all_redlines),
            'redlines': all_redlines
        }

    async def _is_similar_clause(self, text1: str, text2: str) -> bool:
        """Check if two clauses are semantically similar."""
        if text1 == text2:
            return True

        embedding1 = await self.semantic_cache.get_embedding(text1)
        embedding2 = await self.semantic_cache.get_embedding(text2)

        similarity = float(embedding1 @ embedding2)
        return similarity > 0.92

    async def _update_callback(
        self,
        callback,
        batch_id: str,
        status: str,
        progress: float,
        message: str
    ):
        """Update batch processing status."""
        if callback:
            await callback({
                'batch_id': batch_id,
                'status': status,
                'progress': progress,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })


# Global batch processor instance
batch_processor = BatchProcessor()

# Batch tracking
batch_jobs: Dict[str, Dict] = {}


@router.post("/upload")
async def upload_batch(
    files: List[UploadFile] = File(...),
    priority: str = Query("standard", description="Job priority level"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload multiple NDA documents for batch processing.

    Accepts up to 100 documents and processes them with intelligent deduplication.
    Returns a batch_id for tracking progress.
    """
    # Validate batch size
    if len(files) > batch_processor.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum of {batch_processor.max_batch_size} documents"
        )

    # Validate file types
    for file in files:
        if not file.filename.endswith('.docx'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only .docx files are supported"
            )

    batch_id = str(uuid.uuid4())
    batch_path = batch_processor.storage_path / "batches" / batch_id
    batch_path.mkdir(parents=True, exist_ok=True)

    file_paths = []

    # Save uploaded files
    for file in files:
        file_path = batch_path / file.filename
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        file_paths.append(str(file_path))

    # Initialize batch job
    batch_job = {
        'batch_id': batch_id,
        'status': 'queued',
        'files': [f.filename for f in files],
        'file_count': len(files),
        'priority': priority,
        'created_at': datetime.now().isoformat(),
        'progress': 0,
        'result': None
    }

    batch_jobs[batch_id] = batch_job

    # Start processing in background
    background_tasks.add_task(
        process_batch_background,
        batch_id,
        file_paths
    )

    return {
        'batch_id': batch_id,
        'message': f"Batch processing started for {len(files)} documents",
        'status_url': f"/api/batch/status/{batch_id}",
        'stream_url': f"/api/batch/stream/{batch_id}"
    }


async def process_batch_background(batch_id: str, file_paths: List[str]):
    """Process batch in background."""
    async def update_callback(update):
        if batch_id in batch_jobs:
            batch_jobs[batch_id].update(update)

    try:
        result = await batch_processor.process_batch(
            batch_id,
            file_paths,
            update_callback
        )

        batch_jobs[batch_id]['result'] = result
        batch_jobs[batch_id]['status'] = 'completed'

    except Exception as e:
        batch_jobs[batch_id]['status'] = 'error'
        batch_jobs[batch_id]['error'] = str(e)


@router.get("/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get batch processing status."""
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch not found")

    return batch_jobs[batch_id]


@router.get("/stream/{batch_id}")
async def stream_batch_results(batch_id: str):
    """
    Stream batch processing results via Server-Sent Events.

    Returns results as they complete for each document.
    """
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch not found")

    async def event_generator():
        last_status = None

        while True:
            if batch_id in batch_jobs:
                batch = batch_jobs[batch_id]

                # Send update if status changed
                if batch.get('status') != last_status:
                    last_status = batch.get('status')

                    yield {
                        "event": "status",
                        "data": json.dumps({
                            'batch_id': batch_id,
                            'status': batch.get('status'),
                            'progress': batch.get('progress', 0),
                            'message': batch.get('message', '')
                        })
                    }

                # Send final result if completed
                if batch.get('status') == 'completed' and batch.get('result'):
                    yield {
                        "event": "complete",
                        "data": json.dumps(batch['result'])
                    }
                    break

                # Send error if failed
                if batch.get('status') == 'error':
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            'error': batch.get('error', 'Unknown error')
                        })
                    }
                    break

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.get("/stats")
async def get_batch_stats():
    """Get batch processing statistics."""
    cache_stats = batch_processor.semantic_cache.get_statistics()

    return {
        'active_batches': sum(1 for b in batch_jobs.values() if b['status'] == 'processing'),
        'completed_batches': sum(1 for b in batch_jobs.values() if b['status'] == 'completed'),
        'cache_stats': cache_stats,
        'total_cost_saved': cache_stats.get('total_cost_saved', 0)
    }