"""Dify Adapter Module with FastAPI Router."""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from memu.app.service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dify/memory", tags=["dify"])


class MemoryRequest(BaseModel):
    """Request model for adding/searching memory."""

    query: str = Field(..., description="The content to memorize or search for.")
    user_id: str | None = Field(None, description="Optional user identifier.")


class DifyResponse(BaseModel):
    """Standard Dify tool response."""

    result: str = Field(..., description="The text result to display to the LLM.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context.")


def get_memu_service() -> MemoryService:
    """Dependency to get MemU service. Expected to be overridden in main app."""
    raise NotImplementedError("MemU Service dependency must be overridden.")


@router.post("/add", response_model=DifyResponse)
async def add_memory(
    request: MemoryRequest,
    service: MemoryService = Depends(get_memu_service),  # noqa: B008
) -> DifyResponse:
    """
    Add information to MemU memory.

    Args:
        request: The memory request containing query and user_id.
        service: The MemU service instance.

    Returns:
        DifyResponse with status message.
    """
    if not request.query:
        return DifyResponse(result="Error: Content cannot be empty.")

    # Create a temporary file to store the content
    temp_dir = Path(tempfile.gettempdir()) / "memu_dify_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"dify_{uuid.uuid4()}.txt"
    file_path = temp_dir / file_name

    try:
        file_path.write_text(request.query, encoding="utf-8")

        user_scope = {"user_id": request.user_id} if request.user_id else None

        # Call MemU service
        result = await service.memorize(resource_url=str(file_path.absolute()), modality="document", user=user_scope)

        items_count = len(result.get("items", []))
        return DifyResponse(
            result=f"Successfully memorized content. Created {items_count} memory items.",
            metadata={"resource_id": str(result.get("resource", {}).get("id")), "items_created": items_count},
        )

    except Exception as e:
        logger.exception("Failed to add memory from Dify")
        return DifyResponse(result=f"Error processing memory: {e!s}")

    finally:
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            logger.warning("Failed to cleanup temp file %s", file_path, exc_info=True)


@router.post("/search", response_model=DifyResponse)
async def search_memory(
    request: MemoryRequest,
    service: MemoryService = Depends(get_memu_service),  # noqa: B008
) -> DifyResponse:
    """
    Search MemU memory for relevant context.

    Args:
        request: The search request containing query and user_id.
        service: The MemU service instance.

    Returns:
        DifyResponse with formatted retrieved context.
    """
    if not request.query:
        return DifyResponse(result="Please provide a query.")

    try:
        user_scope = {"user_id": request.user_id} if request.user_id else None

        # Construct MemU query format
        memu_queries = [{"role": "user", "content": {"text": request.query}}]

        result = await service.retrieve(queries=memu_queries, where=user_scope)

        return _format_search_response(result)

    except Exception as e:
        logger.exception("Failed to search memory from Dify")
        return DifyResponse(result=f"Error searching memory: {e!s}")


def _format_search_response(result: dict[str, Any]) -> DifyResponse:
    """Format MemU retrieve response for Dify."""
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

    return DifyResponse(result=final_text, metadata={"item_count": len(items), "category_count": len(categories)})


# Standalone app for direct execution (e.g., uvicorn memu.integrations.dify_adapter:app)
def create_app():
    """Create a standalone FastAPI app with the Dify adapter router."""
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from memu.app.service import MemoryService

    memu_service: MemoryService | None = None

    @asynccontextmanager
    async def lifespan(fastapi_app: FastAPI):  # noqa: ARG001
        nonlocal memu_service
        memu_service = MemoryService()
        yield

    def get_service_override() -> MemoryService:
        if memu_service is None:
            raise RuntimeError("MemU service not initialized")
        return memu_service

    fastapi_app = FastAPI(
        title="MemU Dify Adapter",
        description="API server for integrating MemU with Dify",
        lifespan=lifespan,
    )
    fastapi_app.include_router(router)
    fastapi_app.dependency_overrides[get_memu_service] = get_service_override

    return fastapi_app


app = create_app()
