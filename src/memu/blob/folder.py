"""Modality inference from file extensions."""

from __future__ import annotations

import pathlib

# Extension -> modality. Ambiguous extensions (.json, .webm) are mapped to a
# single sensible default and can be made configurable later if needed.
EXT_MODALITY: dict[str, str] = {
    ".json": "conversation",
    ".txt": "document",
    ".md": "document",
    ".text": "document",
    # Rich document formats converted to Markdown via MarkItDown on ingest.
    ".pdf": "document",
    ".docx": "document",
    ".doc": "document",
    ".pptx": "document",
    ".ppt": "document",
    ".xlsx": "document",
    ".xls": "document",
    ".html": "document",
    ".htm": "document",
    ".epub": "document",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
    ".mp4": "video",
    ".mov": "video",
    ".mkv": "video",
    ".avi": "video",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".mpeg": "audio",
    ".mpga": "audio",
}


def infer_modality(path: str | pathlib.Path) -> str | None:
    """Infer modality from a file extension, or None if unsupported."""
    return EXT_MODALITY.get(pathlib.Path(path).suffix.lower())
