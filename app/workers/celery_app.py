from celery import Celery

from app.core.settings import get_settings


settings = get_settings()

celery_app = Celery(
    'simulacao_worker',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=settings.simulation_timeout_seconds,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(['app.workers'])
