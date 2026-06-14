import os
import sys
import time
import random
import asyncio
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]
LR1_SRC_DIR = BASE_DIR / "Lr1" / "src"

if str(LR1_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(LR1_SRC_DIR))

ENV_PATH = BASE_DIR / "Lr1" / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "bookcrossing_db")

SYNC_DB_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
ASYNC_DB_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

from sqlalchemy import create_engine, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import Session, select
from sqlmodel.ext.asyncio.session import AsyncSession

import models.users
import models.links
import models.exchanges
from models.books import Book, Genre, BookCondition
from models.links import BookGenreLink

sync_engine = create_engine(SYNC_DB_URL)
async_engine = create_async_engine(ASYNC_DB_URL)
async_session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

def save_to_db_sync(book_data: dict, retries: int = 3):
    """
    Сохраняет данные книги в базу данных с помощью SQLModel и синхронного движка.
    """
    for attempt in range(retries):
        try:
            with Session(sync_engine) as session:
                existing_book = session.exec(
                    select(Book).where(func.lower(Book.title) == book_data["title"].lower())
                ).first()
                if existing_book:
                    return

                db_genres = []
                for genre_name in book_data["genres"]:
                    genre = session.exec(select(Genre).where(func.lower(Genre.name) == genre_name.lower())).first()
                    if not genre:
                        genre = Genre(name=genre_name)
                        session.add(genre)
                        session.flush()
                    db_genres.append(genre)

                book = Book(
                    bcid=book_data["bcid"],
                    title=book_data["title"],
                    author=book_data["author"],
                    publication_year=book_data["publication_year"],
                    isbn=book_data["isbn"],
                    description=book_data["description"],
                    condition=BookCondition.GOOD,
                    language=book_data["language"],
                    owner_id=None
                )

                book.genres = db_genres
                session.add(book)
                session.commit()
                return
        except IntegrityError:
            if attempt < retries - 1:
                time.sleep(random.uniform(0.1, 0.4))
                continue
            else:
                raise
        except Exception as e:
            raise e 

async def save_to_db_async(book_data: dict, retries: int = 3):
    """
    Сохраняет данные книги в базу данных с помощью SQLModel и асинхронного движка.
    """
    for attempt in range(retries):
        try:
            async with async_session_factory() as session:
                result = await session.exec(select(Book).where(func.lower(Book.title) == book_data["title"].lower()))
                if result.first():
                    return
                    
                db_genres = []
                for genre_name in book_data["genres"]:
                    genre_result = await session.exec(select(Genre).where(func.lower(Genre.name) == genre_name.lower()))
                    genre = genre_result.first()
                    if not genre:
                        genre = Genre(name=genre_name)
                        session.add(genre)
                        await session.flush()
                    db_genres.append(genre)
                    
                book = Book(
                    bcid=book_data["bcid"],
                    title=book_data["title"],
                    author=book_data["author"],
                    publication_year=book_data["publication_year"],
                    isbn=book_data["isbn"],
                    description=book_data["description"],
                    condition=BookCondition.GOOD,
                    language=book_data["language"],
                    owner_id=None
                )
                
                book.genres = db_genres
                session.add(book)
                await session.commit()
                return
        except IntegrityError:
            if attempt < retries - 1:
                await asyncio.sleep(random.uniform(0.1, 0.4))
                continue
            else:
                raise
        except Exception as e:
            raise e
    
def clean_db_sync():
    """
    Полностью очищает базу данных от всех книг и жанров.
    """
    try:
        with Session(sync_engine) as session:
            session.exec(delete(BookGenreLink))
            session.exec(delete(Book))
            session.exec(delete(Genre))
            session.commit()
            print("[Очистка] База данных полностью очищена.")
    except Exception as e:
        print(f"[БД Ошибка] Не удалось очистить базу: {e}")
        raise e