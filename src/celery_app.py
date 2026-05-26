"""Celery configuration for distributed task queue."""

import os
from celery import Celery

# Default to memory queue if Redis not configured
broker_url = os.getenv("CELERY_BROKER_URL", "memory://")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "rpc://")

celery = Celery("nfcc", broker=broker_url, backend=result_backend)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=30,
    task_soft_time_limit=25,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Optional: Configure Redis if available
if broker_url.startswith("redis://"):
    celery.conf.update(
        broker_transport_options={
            "visibility_timeout": 3600,
            "fanout_patterns": True,
        }
    )
    print("✅ Celery configured with Redis broker")
else:
    print("⚠️  Celery using memory broker (not for production)")

# Auto-discover tasks
celery.autodiscover_tasks(["src.tasks"], force=True)
