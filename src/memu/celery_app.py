import os

from celery import Celery
from celery.signals import setup_logging

# Redis configuration with optional authentication
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

celery_app = Celery("memu_worker", broker=REDIS_URL, backend=REDIS_URL, include=["memu.tasks"])


# Configure Celery logging
@setup_logging.connect
def setup_celery_logging_config(**kwargs):
    """Override Celery's default logging with structured JSON logging."""
    from memu.task_utils.logging_config import configure_celery_logging

    log_level = os.getenv("CELERY_LOG_LEVEL", "INFO")
    use_json = os.getenv("CELERY_LOG_JSON", "true").lower() == "true"
    log_file = os.getenv("CELERY_LOG_FILE", None)

    configure_celery_logging(log_level, use_json, log_file)


celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task acknowledgment
    task_acks_late=True,
    task_acks_on_failure_or_timeout=True,
    task_reject_on_worker_lost=True,
    # Timeouts (can be overridden per-task)
    task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "300")),  # 5 minutes
    task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "360")),  # 6 minutes
    # Result backend settings
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "86400")),  # 24 hours
    result_compression="gzip",
    result_extended=True,  # Store task args in result
    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,
    task_store_eager_result=True,  # For testing
    # Worker settings
    worker_prefetch_multiplier=int(os.getenv("CELERY_WORKER_PREFETCH", "1")),
    worker_max_tasks_per_child=int(os.getenv("CELERY_WORKER_MAX_TASKS", "100")),
    worker_max_memory_per_child=int(os.getenv("CELERY_WORKER_MAX_MEMORY", "500000")),  # 500MB
    # Connection settings
    broker_connection_retry_on_startup=True,
    broker_pool_limit=int(os.getenv("CELERY_BROKER_POOL_LIMIT", "10")),
    # Global rate limiting
    task_default_rate_limit=os.getenv("CELERY_TASK_RATE_LIMIT", "100/h"),
)
