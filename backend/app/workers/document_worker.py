"""
Document processing worker
Handles async NDA processing pipeline
"""
import asyncio
import json
import uuid
import os
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from docx import Document
import logging

from ..core.text_indexer import WorkingTextIndexer
from ..core.rule_engine import RuleEngine
from ..core.llm_orchestrator import LLMOrchestrator
from ..core.docx_engine import TrackChangesEngine, RedlineValidator
from ..models.schemas import JobStatus, RedlineModel, RedlineSeverity, RedlineSource
from ..models.checklist_rules import get_rule_explanation


class DocumentProcessor:
    """
    Process a single NDA document through the pipeline:
    1. Parse DOCX and build index
    2. Apply deterministic rules
    3. LLM analysis with validation
    4. Generate redlined document
    """

    def __init__(self, storage_path: str = "./storage", orchestrator=None):
        self.storage_path = Path(storage_path)
        self.rule_engine = RuleEngine()
        # Lazy initialization - orchestrator will be initialized on first use
        self._llm_orchestrator = orchestrator
        self._orchestrator_initialized = orchestrator is not None

    @property
    def llm_orchestrator(self):
        """Lazy-load orchestrator with proper API key"""
        if not self._orchestrator_initialized:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not configured. "
                    "Set environment variable or pass orchestrator to DocumentProcessor"
                )
            # Import here to avoid circular dependencies
            from ..core.llm_orchestrator import LLMOrchestrator
            self._llm_orchestrator = LLMOrchestrator(api_key=api_key)
            self._orchestrator_initialized = True
            logging.getLogger(__name__).info("Initialized LLM orchestrator in DocumentProcessor")
        return self._llm_orchestrator

    async def process_document(
        self,
        job_id: str,
        file_path: str,
        status_callback=None
    ) -> Dict:
        """
        Process a document through the full pipeline.

        Args:
            job_id: Unique job identifier
            file_path: Path to uploaded DOCX
            status_callback: Async callback for status updates

        Returns:
            Dict with processing results
        """
        try:
            # Update status: parsing
            await self._update_status(status_callback, JobStatus.PARSING, 10)

            # 1. Parse DOCX
            doc = Document(file_path)
            indexer = WorkingTextIndexer()
            indexer.build_index(doc)

            working_text = indexer.working_text
            logging.getLogger(__name__).info(f"Job {job_id}: Parsed document, extracted {len(working_text)} characters")

            # Save working text for debugging
            working_text_path = self.storage_path / "working" / f"{job_id}.txt"
            working_text_path.parent.mkdir(parents=True, exist_ok=True)
            working_text_path.write_text(working_text, encoding='utf-8')

            # Update status: analyzing with ALL-CLAUDE orchestrator
            await self._update_status(status_callback, JobStatus.ANALYZING, 30)

            # 2. ALL-CLAUDE ANALYSIS
            # Step 1: Apply deterministic rules FIRST
            logging.getLogger(__name__).info(f"Job {job_id}: Starting rule engine...")
            rule_redlines = self.rule_engine.apply_rules(working_text)
            logging.getLogger(__name__).info(f"Job {job_id}: Rule engine complete - found {len(rule_redlines)} redlines")
            print(f"Job {job_id}: Found {len(rule_redlines)} rule-based redlines")

            # Update status: analyzing with Claude
            await self._update_status(status_callback, JobStatus.APPLYING_RULES, 50)

            # Step 2: LLM analysis with Claude Opus + 100% Sonnet validation
            # The orchestrator will:
            #   - Use Claude Opus for comprehensive recall
            #   - Validate ALL suggestions with Claude Sonnet (100%)
            #   - Merge with rule_redlines automatically
            logging.getLogger(__name__).info(f"Job {job_id}: Starting All-Claude analysis (Opus + Sonnet 100% validation)...")
            all_redlines = await self.llm_orchestrator.analyze(working_text, rule_redlines)
            logging.getLogger(__name__).info(f"Job {job_id}: All-Claude analysis complete - {len(all_redlines)} total redlines")

            # Get LLM stats for reporting
            llm_stats = self.llm_orchestrator.get_stats()
            llm_redlines_count = llm_stats.get('validated_redlines', 0)

            print(f"Job {job_id}: All-Claude analysis complete:")
            print(f"  - Rule-based: {len(rule_redlines)}")
            print(f"  - Claude validated: {llm_redlines_count}")
            print(f"  - Total (merged): {len(all_redlines)}")
            print(f"  - Validation rate: {llm_stats.get('validation_rate', 1.0)*100:.0f}%")

            # Create comparison stats for backward compatibility
            comparison_stats = {
                'llm_only': llm_redlines_count,
                'rule_only': len(rule_redlines),
                'both_found': llm_stats.get('conflicts_resolved', 0),
                'total': len(all_redlines)
            }

            # Validate all redlines
            valid_redlines = RedlineValidator.validate_all(all_redlines, working_text)

            print(f"Job {job_id}: {len(valid_redlines)} valid redlines after validation")

            # Convert to RedlineModel objects
            redline_models = self._convert_to_models(valid_redlines)

            # Update status: generating
            await self._update_status(status_callback, JobStatus.GENERATING, 80)

            # 4. Generate redlined document
            output_path = await self._generate_redlined_doc(
                job_id,
                doc,
                indexer,
                valid_redlines
            )

            # Update status: complete
            await self._update_status(status_callback, JobStatus.COMPLETE, 100)

            # Return results with All-Claude statistics
            result = {
                'job_id': job_id,
                'status': JobStatus.COMPLETE,
                'total_redlines': len(valid_redlines),
                'rule_redlines': len(rule_redlines),
                'llm_redlines': llm_redlines_count,
                'redlines': redline_models,
                'output_path': str(output_path),
                'llm_stats': llm_stats,
                # All-Claude architecture statistics
                'comparison_stats': {
                    'llm_validated_count': comparison_stats['llm_only'],
                    'rule_count': comparison_stats['rule_only'],
                    'conflicts_resolved': comparison_stats['both_found'],
                    'agreement_rate': (
                        comparison_stats['both_found'] / comparison_stats['total'] * 100
                        if comparison_stats['total'] > 0 else 0
                    ),
                    'architecture': 'ALL_CLAUDE',
                    'validation_rate': '100%',  # 100% validation with Sonnet
                    'models': {
                        'recall': llm_stats.get('opus_model', 'claude-opus'),
                        'validation': llm_stats.get('sonnet_model', 'claude-sonnet-4')
                    }
                }
            }

            # Save result
            result_path = self.storage_path / "working" / f"{job_id}_result.json"
            result_path.write_text(json.dumps(result, default=str), encoding='utf-8')

            return result

        except Exception as e:
            logging.getLogger(__name__).error(
                f"Job {job_id}: Processing failed with {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            print(f"Error processing document {job_id}: {e}")
            import traceback
            traceback.print_exc()

            await self._update_status(
                status_callback,
                JobStatus.ERROR,
                0,
                error_message=str(e)
            )

            return {
                'job_id': job_id,
                'status': JobStatus.ERROR,
                'error': str(e)
            }

    async def _generate_redlined_doc(
        self,
        job_id: str,
        doc: Document,
        indexer: WorkingTextIndexer,
        redlines: List[Dict]
    ) -> Path:
        """Generate Word document with track changes"""
        # Create track changes engine
        engine = TrackChangesEngine(author="ndaOK")

        # Enable track changes in document
        engine.enable_track_changes(doc)

        # Apply all redlines
        applied_count = engine.apply_all_redlines(doc, indexer, redlines)

        print(f"Job {job_id}: Applied {applied_count} of {len(redlines)} redlines")

        # Save output
        output_path = self.storage_path / "exports" / f"{job_id}_redlined.docx"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc.save(str(output_path))

        return output_path

    def _compare_and_combine_redlines(
        self,
        llm_redlines: List[Dict],
        rule_redlines: List[Dict],
        working_text: str
    ) -> tuple[List[Dict], Dict]:
        """
        Compare and combine redlines from LLM and rule-based approaches.

        This method:
        1. Identifies redlines found by both approaches (high confidence)
        2. Identifies redlines found only by LLM (LLM-specific insights)
        3. Identifies redlines found only by rules (deterministic catches)
        4. Merges them intelligently, marking the source and agreement

        Returns:
            Tuple of (combined_redlines, comparison_stats)
        """
        combined = []
        comparison_stats = {
            'llm_only': 0,
            'rule_only': 0,
            'both_found': 0,
            'total': 0
        }

        # Create a map of rule redlines by position for quick lookup
        rule_map = {}
        for rule_redline in rule_redlines:
            key = (rule_redline['start'], rule_redline['end'])
            rule_map[key] = rule_redline

        # Process LLM redlines first
        llm_processed = set()
        for llm_redline in llm_redlines:
            key = (llm_redline['start'], llm_redline['end'])

            # Check if rule engine found the same position
            if key in rule_map:
                # Both found it - merge with highest confidence
                rule_redline = rule_map[key]
                merged = self._merge_redlines(llm_redline, rule_redline)
                merged['source'] = 'both'
                merged['agreement'] = True
                merged['llm_version'] = llm_redline.copy()
                merged['rule_version'] = rule_redline.copy()
                combined.append(merged)
                comparison_stats['both_found'] += 1
                llm_processed.add(key)
            else:
                # Only LLM found it
                llm_redline['source'] = 'llm'
                llm_redline['agreement'] = False
                combined.append(llm_redline)
                comparison_stats['llm_only'] += 1
                llm_processed.add(key)

        # Add rule redlines that weren't found by LLM
        for rule_redline in rule_redlines:
            key = (rule_redline['start'], rule_redline['end'])
            if key not in llm_processed:
                # Only rule engine found it
                rule_redline['source'] = 'rule'
                rule_redline['agreement'] = False
                combined.append(rule_redline)
                comparison_stats['rule_only'] += 1

        comparison_stats['total'] = len(combined)

        # Sort by position
        combined.sort(key=lambda r: r['start'])

        return combined, comparison_stats

    def _merge_redlines(self, llm_redline: Dict, rule_redline: Dict) -> Dict:
        """
        Merge redlines from LLM and rule engine when they overlap.

        Priority:
        - Use rule engine's revised_text (deterministic is more reliable)
        - Use rule engine's severity
        - Keep LLM's explanation but note agreement
        - Set confidence to 100 (both agreed)
        """
        merged = rule_redline.copy()

        # Enhance explanation to note both approaches found it
        llm_explanation = llm_redline.get('explanation', '')
        rule_explanation = rule_redline.get('explanation', '')

        if llm_explanation and rule_explanation:
            merged['explanation'] = (
                f"[VERIFIED BY BOTH LLM AND RULES] "
                f"Rule: {rule_explanation} | "
                f"LLM: {llm_explanation}"
            )
        elif rule_explanation:
            merged['explanation'] = f"[VERIFIED BY BOTH LLM AND RULES] {rule_explanation}"
        elif llm_explanation:
            merged['explanation'] = f"[VERIFIED BY BOTH LLM AND RULES] {llm_explanation}"

        # Set confidence to 100 since both approaches agree
        merged['confidence'] = 100

        # Preserve both versions for analysis
        merged['sources'] = ['llm', 'rule']

        return merged

    async def _update_status(
        self,
        callback,
        status: JobStatus,
        progress: float,
        error_message: str = None
    ):
        """Update job status via callback"""
        if callback:
            await callback({
                'status': status,
                'progress': progress,
                'error_message': error_message,
                'updated_at': datetime.now().isoformat()
            })

    def _convert_to_models(self, redlines: List[Dict]) -> List[Dict]:
        """Convert redline dicts to serializable format"""
        models = []

        for redline in redlines:
            clause_type = redline.get('clause_type', 'unknown')

            # Get full checklist rule explanation
            rule_info = get_rule_explanation(clause_type)

            model = {
                'id': str(uuid.uuid4()),
                'rule_id': redline.get('rule_id'),
                'clause_type': clause_type,
                'start': redline['start'],
                'end': redline['end'],
                'original_text': redline['original_text'],
                'revised_text': redline.get('revised_text', ''),
                'severity': redline.get('severity', 'moderate'),
                'confidence': redline.get('confidence', 100),
                'source': redline.get('source', 'rule'),
                'explanation': redline.get('explanation') or redline.get('reasoning'),
                'validated': redline.get('validated', False),
                'user_decision': None,
                # Add full checklist rule information for UI
                'checklist_rule': {
                    'title': rule_info.get('title'),
                    'requirement': rule_info.get('requirement'),
                    'description': rule_info.get('description'),
                    'why': rule_info.get('why'),
                    'standard_language': rule_info.get('standard_language')
                }
            }

            models.append(model)

        return models


class JobQueue:
    """Simple in-memory job queue with TTL-based cleanup"""

    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self.processor = DocumentProcessor()
        self.retention_days = int(os.getenv("RETENTION_DAYS", 7))
        self.cleanup_interval_hours = 1  # Run cleanup every hour
        self.logger = logging.getLogger(__name__)

        # Thread-safe lock for job operations
        self.jobs_lock = threading.RLock()  # Reentrant lock for thread safety

        # Flag to track if cleanup scheduler has been started
        self._cleanup_started = False

    async def _ensure_cleanup_started(self):
        """Ensure cleanup scheduler is running (called on first job submission)"""
        if not self._cleanup_started:
            self._cleanup_started = True
            asyncio.create_task(self._start_cleanup_scheduler())
            self.logger.info("Started job cleanup scheduler")

    async def submit_job(self, job_id: str, file_path: str, filename: str) -> Dict:
        """Submit a new job to the queue with thread safety"""
        # Ensure cleanup scheduler is running
        await self._ensure_cleanup_started()

        job_info = {
            'job_id': job_id,
            'filename': filename,
            'file_path': file_path,
            'status': JobStatus.QUEUED,
            'progress': 0,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'result': None
        }

        with self.jobs_lock:
            self.jobs[job_id] = job_info

        # Process in background with proper exception handling
        task = asyncio.create_task(self._process_job(job_id, file_path))

        # Add callback to handle task exceptions
        def handle_task_exception(task):
            try:
                # This will re-raise any exceptions from the task
                task.result()
            except asyncio.CancelledError:
                # Task was cancelled - this is normal during shutdown
                pass
            except Exception as e:
                self.logger.error(f"Background task for job {job_id} failed: {e}")

        task.add_done_callback(handle_task_exception)

        return job_info

    async def _process_job(self, job_id: str, file_path: str):
        """Process job and update status with proper exception handling and thread safety"""
        try:
            async def status_callback(update):
                with self.jobs_lock:
                    if job_id in self.jobs:
                        self.jobs[job_id].update(update)
                        self.jobs[job_id]['updated_at'] = datetime.now()

            result = await self.processor.process_document(
                job_id,
                file_path,
                status_callback
            )

            with self.jobs_lock:
                if job_id in self.jobs:
                    self.jobs[job_id]['result'] = result
                    self.jobs[job_id]['status'] = result.get('status', JobStatus.COMPLETE)
                    self.jobs[job_id]['updated_at'] = datetime.now()

        except Exception as e:
            # Ensure job error state is always set with thread safety
            with self.jobs_lock:
                if job_id in self.jobs:
                    self.jobs[job_id]['status'] = JobStatus.ERROR
                    self.jobs[job_id]['error_message'] = str(e)
                    self.jobs[job_id]['updated_at'] = datetime.now()
                    self.jobs[job_id]['result'] = {
                        'job_id': job_id,
                        'status': JobStatus.ERROR,
                        'error': str(e)
                    }
            self.logger.error(f"Job {job_id} failed: {e}", exc_info=True)

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current job status with thread safety"""
        with self.jobs_lock:
            # Return a copy to prevent external modifications
            job = self.jobs.get(job_id)
            if job:
                return dict(job)  # Return a shallow copy
            return None

    def update_redline_decision(self, job_id: str, redline_id: str, decision: str):
        """Update user decision on a redline with thread safety"""
        with self.jobs_lock:
            if job_id not in self.jobs:
                return False

            job = self.jobs[job_id]
            result = job.get('result')

            if not result:
                return False

            # Find and update the specific redline
            redlines = result.get('redlines', [])
            found = False

            for redline in redlines:
                if redline['id'] == redline_id:
                    redline['user_decision'] = decision
                    found = True
                    break

            if found:
                # Update timestamp to reflect modification
                job['updated_at'] = datetime.now()
                self.logger.debug(f"Updated redline {redline_id} decision to {decision} for job {job_id}")

            return found

    async def export_final_document(self, job_id: str) -> Optional[Path]:
        """Export final document with only accepted changes"""
        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]
        result = job.get('result')

        if not result:
            return None

        # Filter to accepted redlines
        all_redlines = result.get('redlines', [])
        accepted = [r for r in all_redlines if r.get('user_decision') == 'accept']

        # Re-generate with only accepted changes
        file_path = job['file_path']
        doc = Document(file_path)

        indexer = WorkingTextIndexer()
        indexer.build_index(doc)

        # Convert back to dict format
        accepted_dicts = [{
            'start': r['start'],
            'end': r['end'],
            'original_text': r['original_text'],
            'revised_text': r['revised_text']
        } for r in accepted]

        engine = TrackChangesEngine(author="ndaOK")
        engine.enable_track_changes(doc)
        engine.apply_all_redlines(doc, indexer, accepted_dicts)

        output_path = Path("./storage/exports") / f"{job_id}_final.docx"
        doc.save(str(output_path))

        return output_path

    async def _start_cleanup_scheduler(self):
        """Start periodic cleanup of old jobs"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_hours * 3600)  # Sleep for interval
                await self._cleanup_old_jobs()
            except Exception as e:
                self.logger.error(f"Error in cleanup scheduler: {e}", exc_info=True)
                # Continue running even if cleanup fails
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def _cleanup_old_jobs(self):
        """Remove jobs older than retention period"""
        try:
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            jobs_to_delete = []

            # Identify jobs to delete
            for job_id, job in self.jobs.items():
                created_at = job.get('created_at')
                if created_at and created_at < cutoff:
                    jobs_to_delete.append(job_id)

            # Delete old jobs
            for job_id in jobs_to_delete:
                await self._delete_job(job_id)

            if jobs_to_delete:
                self.logger.info(f"Cleaned up {len(jobs_to_delete)} old jobs (older than {self.retention_days} days)")

        except Exception as e:
            self.logger.error(f"Error cleaning up old jobs: {e}", exc_info=True)

    async def _delete_job(self, job_id: str):
        """Delete a job and its associated files"""
        try:
            if job_id not in self.jobs:
                return

            job = self.jobs[job_id]

            # Clean up associated files
            storage_path = Path("./storage")

            # Delete working files
            files_to_delete = [
                storage_path / "working" / f"{job_id}.txt",
                storage_path / "working" / f"{job_id}_result.json",
                storage_path / "exports" / f"{job_id}_redlined.docx",
                storage_path / "exports" / f"{job_id}_final.docx"
            ]

            # Also delete the original uploaded file if it exists
            if 'file_path' in job:
                files_to_delete.append(Path(job['file_path']))

            for file_path in files_to_delete:
                if file_path.exists():
                    file_path.unlink()
                    self.logger.debug(f"Deleted file: {file_path}")

            # Remove from memory
            del self.jobs[job_id]
            self.logger.debug(f"Deleted job {job_id} from memory")

        except Exception as e:
            self.logger.error(f"Error deleting job {job_id}: {e}", exc_info=True)

    def get_stats(self) -> Dict:
        """Get queue statistics"""
        total_jobs = len(self.jobs)
        status_counts = {}

        for job in self.jobs.values():
            status = job.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            'total_jobs': total_jobs,
            'status_breakdown': status_counts,
            'retention_days': self.retention_days,
            'oldest_job': min((j.get('created_at') for j in self.jobs.values() if j.get('created_at')), default=None)
        }


# Global queue instance
job_queue = JobQueue()
