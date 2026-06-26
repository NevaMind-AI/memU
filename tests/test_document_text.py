"""Tests for rich-document text extraction via MarkItDown."""

from __future__ import annotations

import pathlib
import sys

import pytest

from memu.blob.document_text import extract_document_text, is_rich_document
from memu.blob.folder import infer_modality
from memu.blob.local_fs import LocalFS

HTML_SAMPLE = "<html><body><h1>Title</h1><p>Hello <b>world</b></p><ul><li>a</li><li>b</li></ul></body></html>"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a.pdf", True),
        ("a.PDF", True),
        ("a.docx", True),
        ("a.pptx", True),
        ("a.xlsx", True),
        ("a.html", True),
        ("a.epub", True),
        ("a.txt", False),
        ("a.md", False),
        ("a.json", False),
    ],
)
def test_is_rich_document(name: str, expected: bool) -> None:
    assert is_rich_document(name) is expected


def test_infer_modality_includes_rich_documents() -> None:
    assert infer_modality("report.pdf") == "document"
    assert infer_modality("notes.docx") == "document"
    assert infer_modality("deck.pptx") == "document"
    assert infer_modality("sheet.xlsx") == "document"
    assert infer_modality("page.HTML") == "document"


def test_plain_text_is_read_directly(tmp_path: pathlib.Path) -> None:
    txt = tmp_path / "note.txt"
    txt.write_text("plain text content", encoding="utf-8")
    assert extract_document_text(txt) == "plain text content"


def test_html_is_converted_to_markdown(tmp_path: pathlib.Path) -> None:
    html = tmp_path / "sample.html"
    html.write_text(HTML_SAMPLE, encoding="utf-8")
    text = extract_document_text(html)
    assert "# Title" in text
    assert "**world**" in text
    assert "* a" in text


def test_docx_is_converted_to_markdown(tmp_path: pathlib.Path) -> None:
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_heading("Quarterly Report", level=1)
    document.add_paragraph("Revenue grew by 20 percent.")
    path = tmp_path / "report.docx"
    document.save(path)

    text = extract_document_text(path)
    assert "Quarterly Report" in text
    assert "Revenue grew by 20 percent." in text


def test_missing_markitdown_raises_actionable_error(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    # Force the lazy ``import markitdown`` inside the helper to fail.
    monkeypatch.setitem(sys.modules, "markitdown", None)

    with pytest.raises(RuntimeError, match="memu-py\\[document\\]"):
        extract_document_text(pdf)


async def test_local_fs_fetch_converts_document(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "sample.html"
    src.write_text(HTML_SAMPLE, encoding="utf-8")
    fs = LocalFS(str(tmp_path / "store"))

    local_path, text = await fs.fetch(str(src), "document")

    assert pathlib.Path(local_path).exists()
    assert text is not None
    assert "# Title" in text


async def test_local_fs_fetch_plain_text_document(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "note.md"
    src.write_text("# Heading\n\nbody", encoding="utf-8")
    fs = LocalFS(str(tmp_path / "store"))

    _, text = await fs.fetch(str(src), "document")

    assert text == "# Heading\n\nbody"
