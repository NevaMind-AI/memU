"""Document text extraction for the ``document`` modality.

Plain-text documents (``.txt``/``.md``/``.json``/...) are read directly as
UTF-8. Rich office/binary formats (PDF, Word, PowerPoint, Excel, HTML, EPub,
...) are converted to Markdown via Microsoft's `MarkItDown
<https://github.com/microsoft/markitdown>`_ so downstream memory extraction
receives clean, structure-preserving text instead of raw bytes.

MarkItDown is an optional dependency (``pip install 'memu-py[document]'``); it is
imported lazily so installations that never ingest rich documents stay slim.
"""

from __future__ import annotations

import logging
import pathlib

logger = logging.getLogger(__name__)

# Rich formats that MarkItDown converts to Markdown. Anything not listed here is
# read directly as UTF-8 text.
MARKITDOWN_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".epub",
})


def is_rich_document(path: str | pathlib.Path) -> bool:
    """Whether ``path`` is a rich format that requires MarkItDown conversion."""
    return pathlib.Path(path).suffix.lower() in MARKITDOWN_EXTENSIONS


def extract_document_text(path: str | pathlib.Path) -> str:
    """Extract document text, converting rich formats to Markdown via MarkItDown.

    Plain-text files are read directly as UTF-8. PDF/Office/HTML/EPub files are
    routed through MarkItDown's local-file converter (the narrowest API, per its
    security guidance). Raises ``RuntimeError`` with an actionable message when a
    rich format is encountered but MarkItDown is not installed.
    """
    p = pathlib.Path(path)
    if is_rich_document(p):
        return _convert_with_markitdown(p)
    return p.read_text(encoding="utf-8")


def _convert_with_markitdown(path: pathlib.Path) -> str:
    try:
        from markitdown import MarkItDown
    except ImportError as exc:  # pragma: no cover - exercised via tests with monkeypatch
        msg = f"Converting '{path.name}' requires MarkItDown. Install it with: pip install 'memu-py[document]'"
        raise RuntimeError(msg) from exc

    # ``convert_local`` is the narrowest converter for trusted local files.
    converter = MarkItDown(enable_plugins=False)
    result = converter.convert_local(str(path))
    return result.text_content or ""
