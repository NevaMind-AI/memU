"""Dify Integration Module."""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from memu.app.service import MemoryService

if TYPE_CHECKING:
    from memu.app.service import MemoryService

logger = logging.getLogger(__name__)


class DifyToolProvider:
    """
    Adapter to expose MemU functionality as Dify Tools.
    """

    def __init__(self, service: MemoryService, api_key: str | None = None) -> None:
        """
        Initialize the Dify Tool Provider.

        Args:
            service: An initialized MemU MemoryService instance.
            api_key: Optional API key for authentication check (if manually enforcing).
        """
        self.service = service
        self.api_key = api_key

    async def add_memory(self, query: str, user_id: str | None = None) -> dict[str, Any]:
        """
        Add information to MemU memory.

        Args:
            query: The content to be memorized (Dify sends 'query' for text input).
            user_id: The ID of the user this memory belongs to.

        Returns:
            Dictionary with status and stored resource details.
        """
        if not query:
            return {"status": "error", "message": "Content cannot be empty"}

        # Create a temporary file to store the content, as MemU expects a resource URL/path
        # We use a unique name to avoid collisions
        temp_dir = Path(tempfile.gettempdir()) / "memu_dify_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"dify_{uuid.uuid4()}.txt"
        file_path = temp_dir / file_name

        try:
            file_path.write_text(query, encoding="utf-8")

            user_scope = {"user_id": user_id} if user_id else None

            # Call MemU service
            result = await self.service.memorize(
                resource_url=str(file_path.absolute()), modality="document", user=user_scope
            )

            return {
                "status": "success",
                "message": "Memory added successfully",
                "resource_id": str(result.get("resource", {}).get("id")),
                "items_created": len(result.get("items", [])),
            }

        except Exception as e:
            logger.exception("Failed to add memory from Dify")
            return {"status": "error", "message": str(e)}
        finally:
            # Cleanup temp file
            # In a real async production env, we might want to delay this or rely on OS temp cleaning,
            # but for now synchronous cleanup after processing is fine as memorize() is awaited.
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                logger.warning("Failed to cleanup temp file %s", file_path, exc_info=True)

    async def search_memory(self, query: str, user_id: str | None = None) -> dict[str, Any]:
        """
        Search MemU memory for relevant information.

        Args:
            query: The search query.
            user_id: The ID of the user scope to search within.

        Returns:
            Dictionary with retrieved context and relevant items.
        """
        if not query:
            return {"result": "Please provide a query."}

        try:
            user_scope = {"user_id": user_id} if user_id else None

            # Construct MemU query format
            memu_queries = [{"role": "user", "content": {"text": query}}]

            result = await self.service.retrieve(queries=memu_queries, where=user_scope)

            return self._format_response(result)

        except Exception as e:
            logger.exception("Failed to search memory from Dify")
            return {"status": "error", "message": str(e)}

    def _format_response(self, result: dict[str, Any]) -> dict[str, Any]:
        """Format MemU retrieve response for Dify consumption."""

        # Extract response construction logic similar to MemU's internal formatters
        # but simplified for Dify's text-based tool expectation.

        if result.get("response", {}).get("answer"):
            # If MemU returns a generated answer (future feature), use it
            pass

        # Helper to format items
        items = result.get("items", [])
        categories = result.get("categories", [])

        context_parts = []

        if items:
            context_parts.append("### Relevant Memories")
            for item in items:
                summary = item.get("summary", "")
                if summary:
                    context_parts.append(f"- {summary}")

        if categories:
            context_parts.append("\n### Category Context")
            for cat in categories:
                summary = cat.get("summary", "")
                if summary:
                    context_parts.append(f"**{cat.get('name', 'Category')}**: {summary}")

        final_text = "\n".join(context_parts) if context_parts else "No relevant memories found."

        return {"result": final_text, "metadata": {"item_count": len(items), "category_count": len(categories)}}
