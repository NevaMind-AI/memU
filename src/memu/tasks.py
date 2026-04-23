import asyncio
import logging
from typing import Any

from pydantic import ValidationError

from memu.app.service import MemoryService

from .celery_app import celery_app
from .task_utils.validators import MemorizeTaskInput

logger = logging.getLogger(__name__)

# modality-specific timeout configurations (soft_limit, hard_limit) in seconds
MODALITY_TIMEOUTS = {
    "conversation": (180, 210),  # 3 min soft, 3.5 min hard
    "document": (300, 360),  # 5 min soft, 6 min hard
    "image": (120, 150),  # 2 min soft, 2.5 min hard
    "video": (600, 660),  # 10 min soft, 11 min hard (video processing intensive)
    "audio": (300, 360),  # 5 min soft, 6 min hard (transcription)
}


def run_async(coro):
    """
    Helper to run async code in a sync Celery worker.

    Args:
        coro: An async coroutine to execute

    Returns:
        The result of the coroutine
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No event loop in thread, create new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


def calculate_retry_countdown(retry_count: int, base: int = 60, max_delay: int = 3600) -> int:
    """
    Calculate exponential backoff with jitter for task retries.

    Formula: min(base * 2^retry_count + random_jitter, max_delay)

    Args:
        retry_count: Current retry attempt number (0-indexed)
        base: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Calculated countdown in seconds

    Examples:
        Retry 0: ~60s
        Retry 1: ~120s
        Retry 2: ~240s
        Retry 3: ~480s (capped at max_delay)
    """
    import random

    delay = base * (2**retry_count)
    jitter = random.uniform(0, delay * 0.1)  # noqa: S311  # 10% jitter to prevent thundering herd
    return min(int(delay + jitter), max_delay)


@celery_app.task(
    bind=True,
    name="memu.tasks.process_memory",
    autoretry_for=(Exception,),  # Auto-retry on exceptions
    retry_backoff=True,  # Enable exponential backoff
    retry_backoff_max=3600,  # Max 1 hour between retries
    retry_jitter=True,  # Add jitter
    max_retries=5,  # Max total retries
)
def process_memory_task(self, resource_url: str, modality: str, user: dict[str, Any] | None = None):
    """
    Background task that initializes MemU and runs the memorization logic.

    This task includes:
    - Input validation (SSRF protection, path traversal, etc.)
    - Modality-specific timeouts
    - Exponential backoff retry logic
    - Structured logging with context

    Args:
        resource_url: URL of the resource to memorize
        modality: Type of content (conversation, document, image, video, audio)
        user: Optional user context dictionary

    Returns:
        Result dictionary from MemoryService.memorize()

    Raises:
        ValueError: If validation fails (not retried)
        Exception: Other errors trigger retry with exponential backoff
    """
    task_id = self.request.id

    # Step 0: Apply modality-specific timeouts
    if modality in MODALITY_TIMEOUTS:
        soft_limit, hard_limit = MODALITY_TIMEOUTS[modality]
        self.soft_time_limit = soft_limit
        self.time_limit = hard_limit

        logger.debug(
            f"Task {task_id}: Applied modality-specific timeout",
            extra={
                "task_id": task_id,
                "modality": modality,
                "soft_time_limit": soft_limit,
                "hard_time_limit": hard_limit,
            },
        )

    # Step 1: Input validation
    try:
        validated_input = MemorizeTaskInput(resource_url=resource_url, modality=modality, user=user)
        logger.debug(
            f"Task {task_id}: Input validation passed",
            extra={
                "task_id": task_id,
                "resource_url": resource_url,
                "modality": modality,
            },
        )
    except ValidationError as e:
        logger.error(
            f"Task {task_id}: Input validation failed",
            exc_info=True,
            extra={
                "task_id": task_id,
                "validation_errors": str(e),
                "resource_url": resource_url,
                "modality": modality,
            },
        )
        # Don't retry validation errors - they will always fail
        raise ValueError(f"Invalid input: {e}") from e  # noqa: TRY003

    # Step 2: Log task start
    logger.info(
        "Starting memory processing",
        extra={
            "task_id": task_id,
            "resource_url": validated_input.resource_url,
            "modality": validated_input.modality,
            "user_id": validated_input.user.get("user_id") if validated_input.user else None,
            "retry_count": self.request.retries,
        },
    )

    # Step 3: Initialize service and execute
    service = MemoryService()

    try:
        result = run_async(
            service.memorize(
                resource_url=validated_input.resource_url,
                modality=validated_input.modality,
                user=validated_input.user,
            )
        )

        logger.info(
            "Memory processing completed successfully",
            extra={
                "task_id": task_id,
                "resource_url": validated_input.resource_url,
                "modality": validated_input.modality,
                "result_items": len(result.get("items", [])) if isinstance(result, dict) else 0,
            },
        )

    except Exception as e:
        error_type = type(e).__name__

        logger.error(
            "Memory processing failed",
            exc_info=True,
            extra={
                "task_id": task_id,
                "error_type": error_type,
                "resource_url": validated_input.resource_url,
                "modality": validated_input.modality,
                "retry_count": self.request.retries,
                "max_retries": self.max_retries,
            },
        )

        # Check if we should retry
        if self.request.retries >= self.max_retries:
            logger.critical(
                f"Task {task_id}: Max retries exceeded, task permanently failed",
                extra={
                    "task_id": task_id,
                    "final_error": str(e),
                    "retry_count": self.request.retries,
                },
            )
            raise  # Don't retry, task goes to failed state

        # Calculate exponential backoff countdown
        countdown = calculate_retry_countdown(self.request.retries)

        logger.warning(
            f"Task {task_id}: Retry scheduled",
            extra={
                "task_id": task_id,
                "retry_count": self.request.retries + 1,
                "countdown": countdown,
                "error_type": error_type,
            },
        )

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=countdown, max_retries=self.max_retries) from e
    else:
        return result
