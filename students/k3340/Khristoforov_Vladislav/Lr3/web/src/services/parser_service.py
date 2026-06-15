"""
Модуль сервисного слоя для обработки операций извлечения данных.

Изолирует бизнес-логику межсервисного взаимодействия и сохранения 
сущностей в базу данных от транспортного слоя (роутеров) и брокера задач.
"""

import httpx
from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from typing import List, Dict, Any

from models.books import Book, BookCondition, Genre

async def fetch_data_from_microservice(url: str) -> Dict[str, Any]:
    """
    Осуществляет межсервисный HTTP-запрос к службе парсинга.

    Args:
        url (str): Целевой URL-адрес для извлечения метаданных.

    Returns:
        Dict[str, Any]: Десериализованный ответ от микросервиса.

    Raises:
        HTTPException: В случае недоступности сервиса или внутренней ошибки.
    """
    parser_service_url = "http://parser:8000/parse"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                parser_service_url, 
                json={"url": url},
                timeout=15.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json().get("detail", "Internal Parser Error")
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Parser service unavailable: {str(e)}")

async def resolve_genres(session: AsyncSession, genre_names: List[str]) -> List[Genre]:
    """
    Разрешает зависимости отношений 'Многие-ко-многим' для сущности жанров.
    Ищет существующие записи в БД или инициирует создание новых.

    Args:
        session (AsyncSession): Объект сессии базы данных.
        genre_names (List[str]): Список наименований жанров.

    Returns:
        List[Genre]: Список ORM-экземпляров жанров.
    """
    db_genres = []
    for genre_name in genre_names:
        stmt_genre = select(Genre).where(func.lower(Genre.name) == genre_name.lower())
        genre = (await session.exec(stmt_genre)).first()
        
        if not genre:
            genre = Genre(name=genre_name)
            session.add(genre)
            await session.flush()
            
        db_genres.append(genre)
    return db_genres

async def save_parsed_book(session: AsyncSession, parser_data: Dict[str, Any], user_id: int) -> Book:
    """
    Транслирует десериализованные данные в ORM-модель и сохраняет в БД.

    Args:
        session (AsyncSession): Объект сессии базы данных.
        parser_data (Dict[str, Any]): Метаданные книги из микросервиса.
        user_id (int): Идентификатор пользователя-инициатора запроса.

    Returns:
        Book: Экземпляр сохраненной сущности книги.

    Raises:
        HTTPException (400): В случае выявления дубликата в БД.
    """
    stmt_book = select(Book).where(
        (func.lower(Book.title) == parser_data.get("title", "").lower()) |
        (Book.bcid == parser_data.get("bcid"))
    )
    if (await session.exec(stmt_book)).first():
        raise HTTPException(status_code=400, detail="Book already exists in the database")

    db_genres = await resolve_genres(session, parser_data.get("genres", []))
    
    new_book = Book(
        bcid=parser_data.get("bcid"),
        title=parser_data.get("title"),
        author=parser_data.get("author"),
        publication_year=parser_data.get("publication_year"),
        isbn="Unknown",
        description=parser_data.get("description"),
        language=parser_data.get("language"),
        condition=BookCondition.GOOD,
        owner_id=user_id
    )
    new_book.genres = db_genres
    
    session.add(new_book)
    await session.commit()
    await session.refresh(new_book)
    
    return new_book