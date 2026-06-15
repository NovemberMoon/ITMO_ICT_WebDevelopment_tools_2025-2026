"""
Модуль фонового исполнителя задач (Celery Worker).

Обеспечивает асинхронную обработку длительных I/O операций вне 
основного цикла событий FastAPI. Интегрирован с брокером сообщений Redis.
"""

import asyncio
from celery import Celery
from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import settings

# Инициализация приложения Celery с динамическими настройками брокера
celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

@celery_app.task(name="parse_and_save_task")
def parse_and_save_task(url: str, user_id: int) -> dict:
    """
    Фоновая задача извлечения данных о книге и сохранения их в БД.

    Запускает изолированный цикл событий. Для предотвращения конфликтов контекста
    асинхронного драйвера (asyncpg), инициализирует локальный движок базы данных,
    строго привязанный к текущему циклу.

    Args:
        url (str): Исходный URL-адрес для парсинга.
        user_id (int): Идентификатор пользователя, запросившего операцию.

    Returns:
        dict: Результат выполнения задачи со статусом и метаданными книги
              или детальным описанием возникшей ошибки.
    """
    from routers.parser import _fetch_data_from_microservice, _save_parsed_book
    
    async def run_async_pipeline() -> dict:
        """
        Внутренняя корутина, определяющая жизненный цикл подключения к БД 
        и бизнес-логику задачи.
        """
        # Инициализация изолированного пула подключений
        engine = create_async_engine(settings.DATABASE_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            async with session_factory() as session:
                data = await _fetch_data_from_microservice(url)
                book = await _save_parsed_book(session, data, user_id)
                return {
                    "status": "Success", 
                    "title": book.title, 
                    "bcid": book.bcid
                }
        except HTTPException as e:
            return {"status": "Failed", "error": str(e.detail)}
        except Exception as e:
            return {"status": "Error", "error": str(e)}
        finally:
            # Корректное уничтожение пула и закрытие сокетов
            await engine.dispose()

    # Запуск нового цикла событий для текущей задачи
    return asyncio.run(run_async_pipeline())