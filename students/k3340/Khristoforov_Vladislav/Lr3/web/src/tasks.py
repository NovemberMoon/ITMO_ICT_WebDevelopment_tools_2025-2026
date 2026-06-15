"""
Модуль исполнения фоновых и периодических задач.

Инкапсулирует вызовы к сервисному слою и управляет изолированными 
циклами событий для корректной работы асинхронных драйверов СУБД.
"""

import asyncio
from celery import shared_task
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

import models.links
import models.users
import models.books
import models.exchanges

from config import settings

@shared_task(name="tasks.parse_and_save_task")
def parse_and_save_task(url: str, user_id: int) -> dict:
    """
    Изолированная задача для консьюмера очередей.
    
    Инициализирует локальный пул соединений во избежание конфликтов 
    дескрипторов контекста (Event Loop attachment errors) драйвера asyncpg.
    """
    from services.parser_service import fetch_data_from_microservice, save_parsed_book
    
    async def run_async_pipeline() -> dict:
        engine = create_async_engine(settings.DATABASE_URL)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with session_factory() as session:
                data = await fetch_data_from_microservice(url)
                book = await save_parsed_book(session, data, user_id)
                return {"status": "Success", "title": book.title, "bcid": book.bcid}
        except HTTPException as e:
            return {"status": "Failed", "error": str(e.detail)}
        except Exception as e:
            return {"status": "Error", "error": str(e)}
        finally:
            await engine.dispose()

    return asyncio.run(run_async_pipeline())


@shared_task(name="tasks.log_database_statistics")
def log_database_statistics():
    """
    Периодическая (Cron) задача для агрегации статистических метрик.
    Выполняется планировщиком Celery Beat в соответствии с регламентом.
    """
    async def run_stats_check():
        engine = create_async_engine(settings.DATABASE_URL)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with session_factory() as session:
                from sqlmodel import select, func
                from models.books import Book
                
                result = await session.exec(select(func.count(Book.id)))
                total_books = result.one()
                print(f"[CELERY BEAT] Системная аналитика: Зарегистрировано {total_books} сущностей 'Книга'.")
        finally:
            await engine.dispose()

    asyncio.run(run_stats_check())