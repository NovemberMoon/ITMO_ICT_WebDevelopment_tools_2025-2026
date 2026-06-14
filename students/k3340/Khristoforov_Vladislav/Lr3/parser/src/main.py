"""
Основной модуль микросервиса парсинга книг.

Предоставляет REST API для асинхронного извлечения метаданных
из удаленных HTML-ресурсов (Project Gutenberg, Standard Ebooks).
Функционирует как чистый сервис обработки данных (Stateless) без подключения к БД.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import aiohttp

from scraper import extract_book_info

app = FastAPI(
    title="Parser Microservice API",
    description="REST API для извлечения метаданных о книгах по URL",
    version="1.0.0"
)

class ParseRequest(BaseModel):
    """
    Схема входящего запроса.

    Attributes:
        url (str): Целевой URL-адрес для парсинга.
    """
    url: str

class ParseResponse(BaseModel):
    """
    Схема исходящего ответа (Поле ISBN удалено за ненадобностью).

    Attributes:
        bcid (str): Уникальный сгенерированный идентификатор книги.
        title (str): Название книги.
        author (str): Автор книги (или 'Unknown').
        publication_year (int): Год публикации (или 0, если неизвестен).
        description (Optional[str]): Аннотация или описание.
        language (str): Нормализованный язык книги.
        genres (List[str]): Список жанров.
        source_url (str): Исходный URL-адрес парсинга.
    """
    bcid: str
    title: str
    author: str
    publication_year: int
    description: Optional[str] = None
    language: str
    genres: List[str] = []
    source_url: str


@app.post("/parse", response_model=ParseResponse)
async def parse_url(request: ParseRequest):
    """
    Обрабатывает запрос на извлечение данных о книге по указанному URL.

    Загружает HTML-код страницы по сети и передает его в ядро парсинга.

    Args:
        request (ParseRequest): Объект запроса, содержащий целевой URL.

    Returns:
        ParseResponse: Нормализованные данные о книге, соответствующие схеме ответа.

    Raises:
        HTTPException (400): Сетевая ошибка при попытке скачивания страницы.
        HTTPException (422): Если целевая страница не поддерживается или не содержит заголовка.
        HTTPException (500): Непредвиденная ошибка на этапе парсинга.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(request.url, headers=headers, timeout=10) as response:
                response.raise_for_status()
                html = await response.text()
                
                book_data = extract_book_info(html, request.url)
                
                if not book_data.get("title"):
                    raise HTTPException(
                        status_code=422, 
                        detail="Unprocessable Entity: Failed to extract book title. The source might be unsupported."
                    )
                    
                return book_data
                
        except aiohttp.ClientError as e:
            raise HTTPException(status_code=400, detail=f"Network error occurred: {str(e)}")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Internal parsing error: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Проверяет состояние работоспособности микросервиса.

    Используется системами оркестрации (Docker Compose) для определения 
    готовности сервиса принимать HTTP-запросы.

    Returns:
        dict: Словарь со статусом работы сервиса.
    """
    return {"status": "ok"}