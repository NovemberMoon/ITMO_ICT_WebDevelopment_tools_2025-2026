"""
Модуль конфигурации брокера задач Celery и планировщика (Beat).

Определяет параметры подключения к Redis и регламент периодических операций.
"""

from celery import Celery
from celery.schedules import crontab

from config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "log-db-stats-every-minute": {
        "task": "tasks.log_database_statistics",
        "schedule": crontab(minute="*"), 
    }
}