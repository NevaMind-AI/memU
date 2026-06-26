from __future__ import annotations

import asyncio
import pathlib
import shutil
from urllib.parse import parse_qs, urlparse

import httpx

from memu.blob.document_text import extract_document_text

# Modalities whose ingested text is read straight from the file as UTF-8.
_PLAIN_TEXT_MODALITIES = frozenset({"conversation", "text"})


class LocalFS:
    def __init__(self, base_dir: str):
        self.base = pathlib.Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _get_filename_from_url(self, url: str, modality: str) -> str:
        """
        Extract a clean filename from URL, handling query parameters.

        Args:
            url: The URL to parse
            modality: The resource modality (for extension inference)

        Returns:
            A clean filename without query parameters
        """
        parsed = urlparse(url)
        path = parsed.path

        # Get base filename from path
        filename = pathlib.Path(path).name

        # If filename has no extension or is just a script name (like grab.php),
        # try to get the real extension from query parameters or use modality
        if not filename or "." not in filename or filename.endswith(".php"):
            # Check for 'type' parameter in query string (e.g., ?type=mp3)
            query_params = parse_qs(parsed.query)
            if "type" in query_params:
                ext = query_params["type"][0]
                # Generate a filename based on the ID if available
                filename = f"audio_{query_params['id'][0]}.{ext}" if "id" in query_params else f"resource.{ext}"
            else:
                # Use modality to infer extension
                ext_map = {
                    "audio": "mp3",
                    "video": "mp4",
                    "image": "jpg",
                    "document": "txt",
                }
                ext = ext_map.get(modality, "bin")
                filename = f"resource.{ext}"

        # Remove any remaining query parameters from filename
        filename = filename.split("?")[0]

        return filename

    async def fetch(self, url: str, modality: str) -> tuple[str, str | None]:
        # Local path
        p = pathlib.Path(url)
        if p.exists():
            dst = self.base / p.name
            if str(p.resolve()) != str(dst.resolve()):
                shutil.copyfile(p, dst)
            text = await self._read_text(dst, modality)
            return str(dst), text

        # HTTP - get clean filename
        filename = self._get_filename_from_url(url, modality)
        dst = self.base / filename

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url)
            r.raise_for_status()
            dst.write_bytes(r.content)
        text = await self._read_text(dst, modality)
        return str(dst), text

    @staticmethod
    async def _read_text(path: pathlib.Path, modality: str) -> str | None:
        """Resolve the ingested text for a fetched file based on its modality.

        - ``document``: extract via MarkItDown for rich formats (PDF/Office/...),
          or read plain text directly; runs off-loop since extraction is blocking.
        - ``conversation``/``text``: read the file as UTF-8.
        - everything else (image/audio/video): no inline text.
        """
        if modality == "document":
            return await asyncio.to_thread(extract_document_text, path)
        if modality in _PLAIN_TEXT_MODALITIES:
            return path.read_text(encoding="utf-8")
        return None
