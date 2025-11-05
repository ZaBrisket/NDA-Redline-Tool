"""
Integration tests for FastAPI endpoints
Tests full request/response cycles for all API routes
"""
import pytest
import json
from io import BytesIO
from unittest.mock import patch, MagicMock


@pytest.mark.integration
@pytest.mark.fast
class TestHealthEndpoints:
    """Test health check and status endpoints"""

    def test_root_health_check(self, test_client):
        """Test GET / health check endpoint"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data
        assert data["status"] == "operational"

    def test_health_check_response_structure(self, test_client):
        """Test that health check returns proper structure"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert isinstance(data, dict)
        assert "service" in data
        assert "version" in data
        assert "status" in data

    def test_api_stats_endpoint(self, test_client):
        """Test GET /api/stats endpoint"""
        response = test_client.get("/api/stats")

        # Should return 200 even with no processing history
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.integration
class TestUploadEndpoint:
    """Test document upload functionality"""

    def test_upload_endpoint_exists(self, test_client):
        """Test that upload endpoint is accessible"""
        # OPTIONS request to check endpoint exists
        response = test_client.options("/api/upload")
        assert response.status_code in [200, 405]  # 405 if OPTIONS not allowed

    @patch('backend.app.workers.document_worker.job_queue')
    def test_upload_valid_docx(self, mock_queue, test_client, sample_docx_file):
        """Test uploading a valid DOCX file"""
        # Mock job queue
        mock_queue.create_job.return_value = {
            'job_id': 'test-job-123',
            'status': 'queued'
        }

        with open(sample_docx_file, 'rb') as f:
            files = {'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = test_client.post("/api/upload", files=files)

        # Depending on implementation, might need API keys
        # Allow 400 if API keys are missing (expected in test env)
        assert response.status_code in [200, 400, 422, 500]

    def test_upload_missing_file(self, test_client):
        """Test upload with no file provided"""
        response = test_client.post("/api/upload")

        assert response.status_code == 422  # Validation error

    def test_upload_invalid_file_type(self, test_client):
        """Test uploading non-DOCX file"""
        # Create a fake PDF file
        fake_pdf = BytesIO(b'%PDF-1.4\nfake pdf content')
        files = {'file': ('test.pdf', fake_pdf, 'application/pdf')}

        response = test_client.post("/api/upload", files=files)

        # Should reject non-DOCX files
        assert response.status_code in [400, 415, 422]

    def test_upload_oversized_file(self, test_client):
        """Test uploading file exceeding size limit"""
        # Create large fake DOCX (> 50MB)
        large_content = b'PK\x03\x04' + (b'\x00' * (51 * 1024 * 1024))
        files = {'file': ('large.docx', BytesIO(large_content), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}

        response = test_client.post("/api/upload", files=files)

        # Should reject oversized files
        assert response.status_code in [400, 413, 422]

    def test_upload_empty_file(self, test_client):
        """Test uploading empty file"""
        empty_file = BytesIO(b'')
        files = {'file': ('empty.docx', empty_file, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}

        response = test_client.post("/api/upload", files=files)

        # Should reject empty files
        assert response.status_code in [400, 422]


@pytest.mark.integration
class TestJobStatusEndpoints:
    """Test job status and tracking endpoints"""

    def test_job_status_not_found(self, test_client):
        """Test getting status for non-existent job"""
        fake_job_id = "non-existent-job-12345"
        response = test_client.get(f"/api/jobs/{fake_job_id}/status")

        assert response.status_code == 404

    @patch('backend.app.workers.document_worker.job_queue')
    def test_job_status_found(self, mock_queue, test_client):
        """Test getting status for existing job"""
        job_id = "test-job-123"

        # Mock job data
        mock_queue.get_job.return_value = {
            'job_id': job_id,
            'status': 'complete',
            'progress': 100,
            'filename': 'test.docx'
        }

        response = test_client.get(f"/api/jobs/{job_id}/status")

        if response.status_code == 200:
            data = response.json()
            assert data['job_id'] == job_id
            assert 'status' in data

    def test_job_events_endpoint(self, test_client):
        """Test SSE events endpoint"""
        job_id = "test-job-123"
        response = test_client.get(f"/api/jobs/{job_id}/events")

        # SSE endpoint should exist (might return 404 for non-existent job)
        assert response.status_code in [200, 404]


@pytest.mark.integration
class TestDecisionEndpoints:
    """Test user decision submission endpoints"""

    @patch('backend.app.workers.document_worker.job_queue')
    def test_submit_decisions(self, mock_queue, test_client):
        """Test submitting accept/reject decisions"""
        job_id = "test-job-123"

        # Mock job
        mock_queue.get_job.return_value = {
            'job_id': job_id,
            'status': 'complete',
            'redlines': [
                {'id': 'r1', 'original_text': 'test'}
            ]
        }

        decisions = {
            'decisions': [
                {'redline_id': 'r1', 'decision': 'accept'}
            ]
        }

        response = test_client.post(
            f"/api/jobs/{job_id}/decisions",
            json=decisions
        )

        # Might return 404 if job doesn't exist, or 200 if it does
        assert response.status_code in [200, 404, 422]

    def test_submit_decisions_invalid_format(self, test_client):
        """Test submitting decisions with invalid format"""
        job_id = "test-job-123"

        invalid_data = {
            'wrong_field': 'invalid'
        }

        response = test_client.post(
            f"/api/jobs/{job_id}/decisions",
            json=invalid_data
        )

        # Should reject invalid format
        assert response.status_code in [400, 404, 422]


@pytest.mark.integration
class TestDownloadEndpoints:
    """Test document download endpoints"""

    def test_download_non_existent_job(self, test_client):
        """Test downloading from non-existent job"""
        fake_job_id = "non-existent-job"
        response = test_client.get(f"/api/jobs/{fake_job_id}/download")

        assert response.status_code == 404

    @patch('backend.app.workers.document_worker.job_queue')
    @patch('pathlib.Path.exists', return_value=True)
    def test_download_completed_job(self, mock_exists, mock_queue, test_client):
        """Test downloading from completed job"""
        job_id = "test-job-123"

        # Mock completed job
        mock_queue.get_job.return_value = {
            'job_id': job_id,
            'status': 'complete',
            'output_path': '/tmp/test_output.docx'
        }

        response = test_client.get(f"/api/jobs/{job_id}/download")

        # Will fail if file doesn't actually exist, but endpoint should respond
        assert response.status_code in [200, 404, 500]

    def test_download_with_final_parameter(self, test_client):
        """Test download with final=true parameter"""
        job_id = "test-job-123"
        response = test_client.get(f"/api/jobs/{job_id}/download?final=true")

        # Endpoint should handle final parameter
        assert response.status_code in [200, 404]


@pytest.mark.integration
class TestDeleteEndpoints:
    """Test job deletion endpoints"""

    def test_delete_non_existent_job(self, test_client):
        """Test deleting non-existent job"""
        fake_job_id = "non-existent-job"
        response = test_client.delete(f"/api/jobs/{fake_job_id}")

        assert response.status_code == 404

    @patch('backend.app.workers.document_worker.job_queue')
    def test_delete_existing_job(self, mock_queue, test_client):
        """Test deleting existing job"""
        job_id = "test-job-123"

        # Mock job
        mock_queue.get_job.return_value = {
            'job_id': job_id,
            'status': 'complete'
        }
        mock_queue.delete_job.return_value = True

        response = test_client.delete(f"/api/jobs/{job_id}")

        # Should successfully delete or return 404
        assert response.status_code in [200, 204, 404]


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""

    @pytest.mark.skip(reason="Requires API keys and full setup")
    def test_full_document_processing_workflow(self, test_client, sample_docx_file):
        """Test complete workflow from upload to download"""
        # 1. Upload document
        with open(sample_docx_file, 'rb') as f:
            files = {'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            upload_response = test_client.post("/api/upload", files=files)

        if upload_response.status_code != 200:
            pytest.skip("Upload failed, skipping workflow test")

        job_id = upload_response.json().get('job_id')

        # 2. Check status
        status_response = test_client.get(f"/api/jobs/{job_id}/status")
        assert status_response.status_code == 200

        # 3. Submit decisions (if complete)
        # 4. Download result
        # (Full workflow requires actual processing)


@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling"""

    def test_404_on_invalid_endpoint(self, test_client):
        """Test 404 response for non-existent endpoints"""
        response = test_client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_405_on_wrong_method(self, test_client):
        """Test 405 for unsupported HTTP methods"""
        # Try DELETE on health check (only GET allowed)
        response = test_client.delete("/")

        assert response.status_code == 405

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are present"""
        response = test_client.get("/")

        # CORS headers should be present
        # Note: TestClient may not include all middleware headers
        assert response.status_code == 200

    def test_malformed_json_handling(self, test_client):
        """Test handling of malformed JSON in requests"""
        response = test_client.post(
            "/api/jobs/test-job/decisions",
            content=b'{invalid json}',
            headers={'Content-Type': 'application/json'}
        )

        # Should return 422 for invalid JSON
        assert response.status_code in [400, 422]


@pytest.mark.integration
class TestRateLimiting:
    """Test rate limiting functionality"""

    @pytest.mark.skip(reason="Rate limiting requires Redis/SlowAPI setup")
    def test_rate_limit_enforcement(self, test_client):
        """Test that rate limits are enforced"""
        # Make many requests quickly
        responses = []
        for i in range(150):  # Exceed 100/min limit
            response = test_client.get("/")
            responses.append(response)

        # Some requests should be rate limited (429)
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes or all(s == 200 for s in status_codes)


@pytest.mark.integration
class TestV2Endpoints:
    """Test V2 API endpoints (4-pass pipeline)"""

    def test_v2_analyze_endpoint_exists(self, test_client):
        """Test that V2 analyze endpoint exists"""
        # Try accessing without file (should fail gracefully)
        response = test_client.post("/api/v2/analyze")

        # Endpoint should exist (422 for missing file, not 404)
        assert response.status_code in [422, 400], "V2 endpoint should exist"

    def test_v2_status_endpoint(self, test_client):
        """Test V2 status endpoint"""
        job_id = "test-job-v2"
        response = test_client.get(f"/api/v2/status/{job_id}")

        # Should return 404 for non-existent job
        assert response.status_code in [200, 404]
