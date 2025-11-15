from __future__ import annotations

import pathlib
import shutil

import httpx


class LocalFS:
    def __init__(self, base_dir: str):
        self.base = pathlib.Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    async def fetch(self, url: str, modality: str) -> tuple[str, str | None]:
        # Local path
        p = pathlib.Path(url)
        dst = self.base / p.name
        if p.exists():
            if str(p.resolve()) != str(dst.resolve()):
                shutil.copyfile(p, dst)
            text = None
            if modality in ("conversation", "text"):
                text = dst.read_text(encoding="utf-8")
            return str(dst), text

        # HTTP
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url)
            r.raise_for_status()
            dst.write_bytes(r.content)
        text = None
        if modality in ("conversation", "text"):
            text = r.text
        return str(dst), text
