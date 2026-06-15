"""
Контроллер (Router) интеграции со службой парсинга.

Предоставляет HTTP-эндпоинты для синхронного и асинхронного извлечения данных.
Делегирует бизнес-логику модулю parser_service и брокеру сообщений Celery.
"""

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
from celery.result import AsyncResult

from database import get_session
from models.books import BookPublicWithGenres
from models.users import User
from routers.auth import get_current_user

from services.parser_service import fetch_data_from_microservice, save_parsed_book
from worker import celery_app
from tasks import parse_and_save_task

router = APIRouter(prefix="/parser", tags=["Parser Integration"])

class ParseRequestURL(BaseModel):
    """
    DSO-схема (Data Specification Object) запроса на парсинг.

    Attributes:
        url (str): Целевой URL-адрес.
    """
    url: str

class TaskResponse(BaseModel):
    """
    DSO-схема ответа диспетчера фоновых задач.

    Attributes:
        task_id (str): Уникальный идентификатор задачи в очереди.
        status (str): Текущее состояние исполнения.
    """
    task_id: str
    status: str


@router.post("/sync", response_model=BookPublicWithGenres)
async def parse_and_save_sync(
    request: ParseRequestURL, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Инициирует синхронный процесс извлечения и сохранения данных.
    Блокирует контекст запроса до полного завершения транзакции.
    """
    parser_data = await fetch_data_from_microservice(request.url)
    new_book = await save_parsed_book(session, parser_data, current_user.id)
    return new_book


@router.post("/async", response_model=TaskResponse)
async def parse_and_save_async(
    request: ParseRequestURL, 
    current_user: User = Depends(get_current_user)
):
    """
    Инициирует асинхронный пайплайн посредством передачи задачи брокеру сообщений.
    Возвращает управление клиенту до завершения фактического исполнения задачи.
    """
    task = parse_and_save_task.delay(request.url, current_user.id)
    return {"task_id": task.id, "status": "Task added to queue"}


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Опрашивает хранилище результатов брокера (Result Backend) 
    для получения текущего статуса фоновой задачи.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    if task_result.ready():
        response["result"] = task_result.result
    return response