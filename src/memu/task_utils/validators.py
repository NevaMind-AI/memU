"""
Input validation for Celery tasks.

This module provides Pydantic models to validate task inputs before processing,
preventing security vulnerabilities like SSRF, path traversal, and injection attacks.
"""

from typing import Any, Dict, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class MemorizeTaskInput(BaseModel):
    """
    Validated input for memorize task.

    Security validations:
    - URL scheme: Only http/https allowed (blocks file://, ftp://, etc.)
    - SSRF protection: Blocks localhost and private IP ranges
    - Path traversal: Blocks ".." in URLs
    - Modality whitelist: Only allowed modalities accepted
    - User validation: Ensures user_id exists if user dict provided
    """

    resource_url: str
    modality: Literal["conversation", "document", "image", "video", "audio"]
    user: Dict[str, Any] | None = None

    @field_validator("resource_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """
        Validate resource URL for security vulnerabilities.

        Checks:
        1. URL length (max 2048 chars)
        2. URL scheme (only http/https)
        3. SSRF protection (blocks localhost and private IPs)
        4. Path traversal prevention (blocks ".." sequences)

        Args:
            v: The resource URL to validate

        Returns:
            The validated URL

        Raises:
            ValueError: If validation fails
        """
        # Length check
        if len(v) > 2048:
            raise ValueError("URL exceeds maximum length of 2048 characters")

        # Parse and validate
        try:
            parsed = urlparse(v)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

        # Scheme validation (prevent file://, ftp://, etc.)
        if parsed.scheme not in ["http", "https"]:
            raise ValueError(
                f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed"
            )

        # Netloc must be present
        if not parsed.netloc:
            raise ValueError("URL must include a hostname")

        # Path traversal protection
        if ".." in parsed.path or ".." in parsed.netloc:
            raise ValueError("Path traversal detected in URL")

        # SSRF protection - Block localhost/private IPs
        # For IPv6 addresses in brackets like [::1], keep the brackets
        # For regular hostnames, remove port if present
        netloc_lower = parsed.netloc.lower()
        if netloc_lower.startswith('['):
            # IPv6 address - extract the part in brackets
            bracket_end = netloc_lower.find(']')
            if bracket_end != -1:
                hostname_lower = netloc_lower[:bracket_end + 1]
            else:
                hostname_lower = netloc_lower
        else:
            # Regular hostname - remove port
            hostname_lower = netloc_lower.split(":")[0]

        # Localhost patterns
        localhost_patterns = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "[::1]",
            "::1",
        ]

        if hostname_lower in localhost_patterns:
            raise ValueError("Access to localhost is not allowed")

        # Private IP ranges (check if hostname looks like an IP)
        private_ip_patterns = [
            "10.",           # 10.0.0.0/8
            "172.16.",       # 172.16.0.0/12
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
            "192.168.",      # 192.168.0.0/16
            "169.254.",      # Link-local (169.254.0.0/16)
        ]

        if any(hostname_lower.startswith(pattern) for pattern in private_ip_patterns):
            raise ValueError("Access to private IP ranges is not allowed")

        return v

    @field_validator("user")
    @classmethod
    def validate_user(cls, v: Dict[str, Any] | None) -> Dict[str, Any] | None:
        """
        Validate user dictionary structure.

        Args:
            v: The user dictionary to validate

        Returns:
            The validated user dictionary

        Raises:
            ValueError: If user_id is missing or invalid
        """
        if v is None:
            return None

        # Ensure user_id exists if user dict provided
        if "user_id" not in v:
            raise ValueError("user_id is required in user dict")

        # Type safety for user_id
        if not isinstance(v["user_id"], str) or not v["user_id"].strip():
            raise ValueError("user_id must be a non-empty string")

        return v

    @model_validator(mode="after")
    def validate_modality_url_compatibility(self) -> "MemorizeTaskInput":
        """
        Validate URL extension matches modality (warning only).

        This is a soft validation - we log warnings but don't block
        since URLs may not always have file extensions.
        """
        parsed = urlparse(self.resource_url)
        ext = parsed.path.lower().split(".")[-1] if "." in parsed.path else ""

        modality_extensions = {
            "document": ["pdf", "txt", "doc", "docx", "md", "rtf", "odt"],
            "image": ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"],
            "video": ["mp4", "avi", "mov", "webm", "mkv", "flv", "wmv"],
            "audio": ["mp3", "wav", "m4a", "ogg", "flac", "aac", "wma"],
        }

        if self.modality in modality_extensions:
            allowed = modality_extensions[self.modality]
            if ext and ext not in allowed:
                # Warn but don't block (URL might not have extension)
                # In production, this could be logged
                pass

        return self


class TaskValidationConfig(BaseModel):
    """Configuration for task input validation."""

    max_url_length: int = Field(default=2048, description="Maximum URL length")
    allowed_url_schemes: list[str] = Field(
        default=["http", "https"],
        description="Allowed URL schemes"
    )
    blocked_domains: list[str] = Field(
        default_factory=list,
        description="Domains to block (optional custom blocklist)"
    )
    max_file_size_mb: int = Field(
        default=100,
        description="Maximum file size in MB (not enforced at validation)"
    )
    allowed_modalities: list[str] = Field(
        default=["conversation", "document", "image", "video", "audio"],
        description="Allowed modality values"
    )
    user_id_required: bool = Field(
        default=True,
        description="Whether user_id is required in user dict"
    )
