"""
Модуль интеграции с микросервисом парсинга.

Предоставляет HTTP-эндпоинты для синхронного взаимодействия с сервисом извлечения
данных и последующего сохранения объектов в локальную базу данных приложения.
"""

import httpx
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from pydantic import BaseModel
from typing import List, Dict, Any

from database import get_session
from models.books import Book, BookPublicWithGenres, BookCondition, Genre
from models.users import User
from routers.auth import get_current_user

router = APIRouter(prefix="/parser", tags=["Parser Integration"])

class ParseRequestURL(BaseModel):
    """
    Схема входящего запроса на парсинг.

    Attributes:
        url (str): Исходный URL-адрес для извлечения данных.
    """
    url: str


async def _fetch_data_from_microservice(url: str) -> Dict[str, Any]:
    """
    Вспомогательная функция: Осуществляет межсервисный HTTP-запрос.

    Args:
        url (str): Целевой URL для парсинга.

    Returns:
        Dict[str, Any]: Ответ от микросервиса парсера.

    Raises:
        HTTPException: Если сервис недоступен или вернул ошибку.
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


async def _resolve_genres(session: AsyncSession, genre_names: List[str]) -> List[Genre]:
    """
    Вспомогательная функция: Разрешение зависимостей для M:M связей.
    Ищет жанры в БД, если их нет — создает новые.

    Args:
        session (AsyncSession): Сессия БД.
        genre_names (List[str]): Список названий жанров из парсера.

    Returns:
        List[Genre]: Список ORM-объектов жанров.
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


async def _save_parsed_book(session: AsyncSession, parser_data: Dict[str, Any], user_id: int) -> Book:
    """
    Вспомогательная функция: Сохраняет валидированные данные в БД.

    Args:
        session (AsyncSession): Сессия БД.
        parser_data (Dict[str, Any]): Данные, полученные от микросервиса.
        user_id (int): ID владельца книги.

    Returns:
        Book: Сохраненный ORM-объект книги.

    Raises:
        HTTPException (400): Если книга уже существует.
    """
    stmt_book = select(Book).where(
        (func.lower(Book.title) == parser_data.get("title", "").lower()) |
        (Book.bcid == parser_data.get("bcid"))
    )
    if (await session.exec(stmt_book)).first():
        raise HTTPException(status_code=400, detail="Book already exists in the database")

    db_genres = await _resolve_genres(session, parser_data.get("genres", []))
    
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


@router.post("/sync", response_model=BookPublicWithGenres)
async def parse_and_save_sync(
    request: ParseRequestURL, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Синхронно обрабатывает запрос на парсинг и сохраняет результат в БД.

    Делегирует задачи извлечения данных, обработки жанров и сохранения
    соответствующим сервисным функциям.

    Args:
        request (ParseRequestURL): Объект с URL для парсинга.
        session (AsyncSession): Сессия базы данных.
        current_user (User): Текущий авторизованный пользователь (владелец книги).

    Returns:
        Book: Сохраненный объект книги с подгруженными жанрами.
    """
    parser_data = await _fetch_data_from_microservice(request.url)
    
    new_book = await _save_parsed_book(session, parser_data, current_user.id)
    
    return new_book