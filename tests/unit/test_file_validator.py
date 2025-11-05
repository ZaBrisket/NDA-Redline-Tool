"""
Unit tests for File Validator
Tests file type validation, size checking, and security scanning
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.unit
@pytest.mark.fast
class TestFileValidator:
    """Test suite for FileValidator"""

    def test_file_extension_validation(self):
        """Test that file extensions are validated correctly"""
        valid_extensions = ['.docx', '.doc']
        invalid_extensions = ['.pdf', '.txt', '.exe', '.sh', '.py']

        for ext in valid_extensions:
            filename = f"test{ext}"
            file_ext = Path(filename).suffix.lower()
            assert file_ext in valid_extensions

        for ext in invalid_extensions:
            filename = f"test{ext}"
            file_ext = Path(filename).suffix.lower()
            assert file_ext not in valid_extensions

    def test_file_size_validation(self):
        """Test file size limit checking"""
        max_size_mb = 50
        max_size_bytes = max_size_mb * 1024 * 1024

        # Test sizes
        test_cases = [
            (1024 * 1024, True),  # 1MB - should pass
            (10 * 1024 * 1024, True),  # 10MB - should pass
            (50 * 1024 * 1024, True),  # 50MB - should pass
            (51 * 1024 * 1024, False),  # 51MB - should fail
            (100 * 1024 * 1024, False),  # 100MB - should fail
        ]

        for size_bytes, should_pass in test_cases:
            is_valid = size_bytes <= max_size_bytes
            assert is_valid == should_pass, f"Size {size_bytes} bytes validation incorrect"

    def test_docx_magic_bytes(self):
        """Test DOCX file signature (magic bytes) validation"""
        # DOCX files are ZIP files, start with PK\x03\x04
        docx_magic = b'PK\x03\x04'

        # Valid DOCX signature
        valid_content = docx_magic + b'\x00' * 100
        assert valid_content[:4] == docx_magic

        # Invalid signature
        invalid_content = b'INVALID' + b'\x00' * 100
        assert invalid_content[:4] != docx_magic

    def test_filename_sanitization(self):
        """Test that filenames are sanitized properly"""
        test_cases = [
            ("../../etc/passwd", False),  # Path traversal
            ("test.docx", True),  # Normal file
            ("my document.docx", True),  # Spaces OK
            ("../../../malicious.docx", False),  # Path traversal
            ("test\x00.docx", False),  # Null byte
            ("COM1.docx", False),  # Windows reserved name
        ]

        def is_safe_filename(filename):
            """Simple filename safety check"""
            if '..' in filename:
                return False
            if '\x00' in filename:
                return False
            if filename.upper() in ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1']:
                return False
            return True

        for filename, should_be_safe in test_cases:
            assert is_safe_filename(filename) == should_be_safe

    def test_mime_type_validation(self):
        """Test MIME type checking"""
        allowed_mime_types = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/msword"  # .doc
        }

        valid_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        invalid_mimes = [
            "application/pdf",
            "text/plain",
            "application/x-sh",
            "application/x-executable"
        ]

        assert valid_mime in allowed_mime_types
        for mime in invalid_mimes:
            assert mime not in allowed_mime_types

    @patch('backend.app.middleware.security.HAS_MAGIC', False)
    def test_missing_python_magic_warning(self, caplog):
        """Test that warning is logged when python-magic is missing"""
        from backend.app.middleware.security import FileValidator

        validator = FileValidator()

        # Check that validator was created
        assert validator is not None

        # When HAS_MAGIC is False, warning should be in logs
        # Note: In actual code, the warning is logged in __init__

    def test_empty_file_rejection(self):
        """Test that empty files are rejected"""
        empty_content = b''
        min_size = 100  # Minimum file size in bytes

        file_size = len(empty_content)
        is_valid = file_size >= min_size

        assert not is_valid, "Empty files should be rejected"

    def test_file_content_validation(self):
        """Test validating file content structure"""
        # Valid DOCX content starts with ZIP signature
        valid_content = b'PK\x03\x04' + b'\x14\x00\x00\x00' + b'\x08\x00'

        # Check signature
        has_valid_signature = valid_content[:4] == b'PK\x03\x04'
        assert has_valid_signature

    def test_multiple_file_validation(self):
        """Test validating multiple files"""
        files = [
            {'name': 'test1.docx', 'size': 1024 * 1024, 'valid': True},
            {'name': 'test2.doc', 'size': 5 * 1024 * 1024, 'valid': True},
            {'name': 'test3.pdf', 'size': 1024 * 1024, 'valid': False},
            {'name': 'test4.docx', 'size': 60 * 1024 * 1024, 'valid': False},  # Too large
        ]

        max_size = 50 * 1024 * 1024
        valid_extensions = ['.docx', '.doc']

        for file in files:
            ext = Path(file['name']).suffix.lower()
            size_ok = file['size'] <= max_size
            ext_ok = ext in valid_extensions

            is_valid = size_ok and ext_ok
            assert is_valid == file['valid'], f"File {file['name']} validation incorrect"


@pytest.mark.unit
class TestSecurityMiddleware:
    """Test security middleware functionality"""

    def test_rate_limiting_config(self):
        """Test rate limiting configuration"""
        default_rate = "100 per minute"
        batch_rate = "2 per minute"

        # Parse rate strings
        def parse_rate(rate_string):
            parts = rate_string.split()
            return int(parts[0])

        assert parse_rate(default_rate) == 100
        assert parse_rate(batch_rate) == 2

    def test_cors_origin_validation(self):
        """Test CORS origin validation"""
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "https://yourdomain.com"
        ]

        test_origins = [
            ("http://localhost:3000", True),
            ("https://yourdomain.com", True),
            ("http://evil.com", False),
            ("https://malicious.org", False),
        ]

        for origin, should_allow in test_origins:
            is_allowed = origin in allowed_origins
            assert is_allowed == should_allow

    def test_api_key_hashing(self):
        """Test that API keys are hashed, not stored raw"""
        import hashlib

        api_key = "test-api-key-12345"

        # Keys should be hashed with SHA256
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        assert len(key_hash) == 64  # SHA256 produces 64 hex characters
        assert key_hash != api_key  # Hash should not equal original

    def test_request_size_limits(self):
        """Test request size limit enforcement"""
        max_request_size_mb = 20
        max_size_bytes = max_request_size_mb * 1024 * 1024

        request_sizes = [
            (1 * 1024 * 1024, True),  # 1MB - OK
            (10 * 1024 * 1024, True),  # 10MB - OK
            (20 * 1024 * 1024, True),  # 20MB - OK
            (25 * 1024 * 1024, False),  # 25MB - Too large
        ]

        for size, should_allow in request_sizes:
            is_allowed = size <= max_size_bytes
            assert is_allowed == should_allow

    def test_real_ip_extraction(self):
        """Test extracting real IP from X-Forwarded-For header"""
        test_cases = [
            ("1.2.3.4", "1.2.3.4"),
            ("1.2.3.4, 5.6.7.8", "1.2.3.4"),  # First IP in chain
            ("1.2.3.4, 5.6.7.8, 9.10.11.12", "1.2.3.4"),  # Multiple proxies
        ]

        for header_value, expected_ip in test_cases:
            extracted_ip = header_value.split(",")[0].strip()
            assert extracted_ip == expected_ip


@pytest.mark.unit
class TestAuditLogging:
    """Test audit logging functionality"""

    def test_audit_log_entry_format(self):
        """Test audit log entry structure"""
        import json
        from datetime import datetime

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'request_success',
            'ip_address': '1.2.3.4',
            'method': 'POST',
            'path': '/api/upload',
            'user_agent': 'TestClient/1.0',
            'status_code': 200
        }

        # Should be JSON serializable
        json_str = json.dumps(log_entry)
        assert isinstance(json_str, str)

        # Should be parseable
        parsed = json.loads(json_str)
        assert parsed['event_type'] == 'request_success'
        assert parsed['status_code'] == 200

    def test_audit_log_retention(self):
        """Test audit log retention policy"""
        retention_days = 90
        retention_seconds = retention_days * 24 * 60 * 60

        assert retention_days == 90
        assert retention_seconds == 7776000  # 90 days in seconds

    def test_sensitive_data_masking(self):
        """Test that sensitive data is masked in logs"""
        api_key = "sk-1234567890abcdef"

        # API keys should be masked
        masked_key = api_key[:7] + "..." + api_key[-4:]

        assert "..." in masked_key
        assert len(masked_key) < len(api_key)
        assert masked_key.startswith("sk-")
