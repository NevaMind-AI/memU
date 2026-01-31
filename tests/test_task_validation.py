"""
Tests for Celery task input validation.

This test suite verifies that the input validation properly prevents:
- SSRF attacks (Server-Side Request Forgery)
- Path traversal attacks
- Invalid modalities
- Malformed user data
"""

import os
import sys

# ensure Python finds the src folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from pydantic import ValidationError

from memu.task_utils.validators import MemorizeTaskInput


class TestURLValidation:
    """Test URL validation for security vulnerabilities."""

    def test_valid_https_url(self):
        """Valid HTTPS URL should pass validation."""
        task_input = MemorizeTaskInput(
            resource_url="https://example.com/test.pdf", modality="document", user={"user_id": "test_user"}
        )
        assert task_input.resource_url == "https://example.com/test.pdf"

    def test_valid_http_url(self):
        """Valid HTTP URL should pass validation."""
        task_input = MemorizeTaskInput(
            resource_url="http://example.com/test.pdf", modality="document", user={"user_id": "test_user"}
        )
        assert task_input.resource_url == "http://example.com/test.pdf"

    def test_reject_file_scheme(self):
        """File:// URLs should be rejected (prevents local file access)."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="file:///etc/passwd", modality="document")
        assert "Invalid URL scheme" in str(exc_info.value)

    def test_reject_ftp_scheme(self):
        """FTP URLs should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="ftp://example.com/test.pdf", modality="document")
        assert "Invalid URL scheme" in str(exc_info.value)

    def test_reject_localhost(self):
        """Localhost URLs should be rejected (SSRF protection)."""
        localhost_urls = [
            "http://localhost:6379/",
            "http://127.0.0.1:6379/",
            "http://0.0.0.0/admin",
            "http://[::1]/test",
        ]

        for url in localhost_urls:
            with pytest.raises(ValidationError) as exc_info:
                MemorizeTaskInput(resource_url=url, modality="document")
            assert "localhost" in str(exc_info.value).lower()

    def test_reject_private_ip_10_x(self):
        """Private IP 10.x.x.x should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="http://10.0.0.1/admin", modality="document")
        assert "private" in str(exc_info.value).lower()

    def test_reject_private_ip_192_168(self):
        """Private IP 192.168.x.x should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="http://192.168.1.1/router", modality="document")
        assert "private" in str(exc_info.value).lower()

    def test_reject_private_ip_172_16(self):
        """Private IP 172.16-31.x.x should be rejected."""
        private_ips = [
            "http://172.16.0.1/",
            "http://172.20.0.1/",
            "http://172.31.255.255/",
        ]

        for url in private_ips:
            with pytest.raises(ValidationError) as exc_info:
                MemorizeTaskInput(resource_url=url, modality="document")
            assert "private" in str(exc_info.value).lower()

    def test_reject_link_local_169_254(self):
        """Link-local IP 169.254.x.x should be rejected (AWS metadata, etc.)."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="http://169.254.169.254/latest/meta-data/", modality="document")
        assert "private" in str(exc_info.value).lower()

    def test_reject_path_traversal_in_path(self):
        """URLs with .. in path should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="http://example.com/../../../etc/passwd", modality="document")
        assert "Path traversal" in str(exc_info.value)

    def test_reject_path_traversal_in_netloc(self):
        """URLs with .. in netloc should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="http://example.com..evil.com/test", modality="document")
        assert "Path traversal" in str(exc_info.value)

    def test_reject_url_too_long(self):
        """URLs exceeding 2048 characters should be rejected."""
        long_url = "http://example.com/" + "a" * 2100
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url=long_url, modality="document")
        assert "exceeds maximum length" in str(exc_info.value)

    def test_reject_url_without_netloc(self):
        """URLs without hostname should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="http:///test", modality="document")
        assert "hostname" in str(exc_info.value).lower()


class TestModalityValidation:
    """Test modality validation."""

    def test_valid_modalities(self):
        """All valid modalities should pass validation."""
        valid_modalities = ["conversation", "document", "image", "video", "audio"]

        for modality in valid_modalities:
            task_input = MemorizeTaskInput(
                resource_url="https://example.com/test.pdf", modality=modality, user={"user_id": "test_user"}
            )
            assert task_input.modality == modality

    def test_reject_invalid_modality(self):
        """Invalid modalities should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="https://example.com/test.pdf", modality="invalid_modality")
        # Pydantic will include "Input should be" in error
        assert "Input should be" in str(exc_info.value)

    def test_reject_sql_injection_modality(self):
        """SQL injection attempts in modality should be rejected."""
        with pytest.raises(ValidationError):
            MemorizeTaskInput(resource_url="https://example.com/test.pdf", modality="'; DROP TABLE memories; --")


class TestUserValidation:
    """Test user dictionary validation."""

    def test_valid_user_dict(self):
        """Valid user dict with user_id should pass."""
        task_input = MemorizeTaskInput(
            resource_url="https://example.com/test.pdf", modality="document", user={"user_id": "test_user_123"}
        )
        assert task_input.user["user_id"] == "test_user_123"

    def test_user_none_allowed(self):
        """User can be None."""
        task_input = MemorizeTaskInput(resource_url="https://example.com/test.pdf", modality="document", user=None)
        assert task_input.user is None

    def test_reject_user_without_user_id(self):
        """User dict without user_id should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(
                resource_url="https://example.com/test.pdf",
                modality="document",
                user={"name": "John Doe"},  # Missing user_id
            )
        assert "user_id" in str(exc_info.value)

    def test_reject_empty_user_id(self):
        """User dict with empty user_id should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="https://example.com/test.pdf", modality="document", user={"user_id": ""})
        assert "user_id" in str(exc_info.value)

    def test_reject_whitespace_only_user_id(self):
        """User dict with whitespace-only user_id should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(resource_url="https://example.com/test.pdf", modality="document", user={"user_id": "   "})
        assert "user_id" in str(exc_info.value)

    def test_reject_non_string_user_id(self):
        """User dict with non-string user_id should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemorizeTaskInput(
                resource_url="https://example.com/test.pdf",
                modality="document",
                user={"user_id": 123},  # Integer instead of string
            )
        assert "user_id" in str(exc_info.value)


class TestCompleteValidation:
    """Integration tests for complete validation."""

    def test_complete_valid_input(self):
        """Complete valid input should pass all validations."""
        task_input = MemorizeTaskInput(
            resource_url="https://api.example.com/documents/12345.pdf",
            modality="document",
            user={"user_id": "user_123", "name": "John Doe"},
        )

        assert task_input.resource_url == "https://api.example.com/documents/12345.pdf"
        assert task_input.modality == "document"
        assert task_input.user["user_id"] == "user_123"

    def test_url_with_port(self):
        """URLs with ports should work (as long as not localhost)."""
        task_input = MemorizeTaskInput(resource_url="https://example.com:8080/test.pdf", modality="document")
        assert task_input.resource_url == "https://example.com:8080/test.pdf"

    def test_url_with_query_params(self):
        """URLs with query parameters should work."""
        task_input = MemorizeTaskInput(resource_url="https://example.com/file?id=123&token=abc", modality="document")
        assert task_input.resource_url == "https://example.com/file?id=123&token=abc"

    def test_url_with_fragment(self):
        """URLs with fragments should work."""
        task_input = MemorizeTaskInput(resource_url="https://example.com/page.html#section1", modality="document")
        assert task_input.resource_url == "https://example.com/page.html#section1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
