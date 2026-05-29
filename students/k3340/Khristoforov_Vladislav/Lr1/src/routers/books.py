from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from database import get_session
from models.books import (
    Book, BookCreate, BookUpdate, BookPublic, BookPublicWithGenres,
    Genre, GenreCreate, GenreUpdate, GenrePublic
)
from models.links import BookGenreLink
from models.users import Location, Role, User
from routers.auth import get_current_admin, get_current_user

books_router = APIRouter(prefix="/books", tags=["Books"])
genres_router = APIRouter(prefix="/genres", tags=["Genres"])

# --- ЭНДПОИНТЫ ДЛЯ ЖАНРОВ (Модификация только для Администраторов) ---

@genres_router.post("/", response_model=GenrePublic, dependencies=[Depends(get_current_admin)])
async def create_genre(genre: GenreCreate, session: AsyncSession = Depends(get_session)):
    db_genre = Genre.model_validate(genre)
    session.add(db_genre)
    await session.commit()
    await session.refresh(db_genre)
    return db_genre

@genres_router.get("/", response_model=List[GenrePublic])
async def read_genres(session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(Genre))
    return result.all()

@genres_router.get("/{genre_id}", response_model=GenrePublic)
async def read_genre(genre_id: int, session: AsyncSession = Depends(get_session)):
    genre = await session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre

@genres_router.patch("/{genre_id}", response_model=GenrePublic, dependencies=[Depends(get_current_admin)])
async def update_genre(genre_id: int, genre_data: GenreUpdate, session: AsyncSession = Depends(get_session)):
    db_genre = await session.get(Genre, genre_id)
    if not db_genre:
        raise HTTPException(status_code=404, detail="Genre not found")
        
    for key, value in genre_data.model_dump(exclude_unset=True).items():
        setattr(db_genre, key, value)
        
    session.add(db_genre)
    await session.commit()
    await session.refresh(db_genre)
    return db_genre

@genres_router.delete("/{genre_id}", dependencies=[Depends(get_current_admin)])
async def delete_genre(genre_id: int, session: AsyncSession = Depends(get_session)):
    genre = await session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    await session.delete(genre)
    await session.commit()
    return {"ok": True, "message": "Genre deleted"}

# --- ЭНДПОИНТЫ ДЛЯ КНИГ ---

@books_router.post("/", response_model=BookPublic)
async def create_book(book: BookCreate, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    db_book = Book.model_validate(book)
    # Автоматически привязываем создателя книги как владельца
    db_book.owner_id = current_user.id
    session.add(db_book)
    await session.commit()
    await session.refresh(db_book)
    return db_book

@books_router.get("/bcid/{bcid}", response_model=BookPublicWithGenres)
async def read_book_by_bcid(bcid: str, session: AsyncSession = Depends(get_session)):
    # Изолированный поиск по уникальному коду буккроссинга
    statement = select(Book).where(Book.bcid == bcid, Book.is_deleted == False).options(selectinload(Book.genres))
    result = await session.exec(statement)
    book = result.first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found or deleted")
    return book

@books_router.get("/{book_id}", response_model=BookPublicWithGenres)
async def read_book(book_id: int, session: AsyncSession = Depends(get_session)):
    statement = select(Book).where(Book.id == book_id).options(selectinload(Book.genres))
    result = await session.exec(statement)
    book = result.first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@books_router.get("/", response_model=List[BookPublic])
async def read_books(
    offset: int = 0, 
    limit: int = Query(default=100, le=100), 
    is_available: Optional[bool] = Query(default=None, description="Фильтр по доступности"),
    search: Optional[str] = Query(default=None, description="Поиск по названию или автору"),
    genre_id: Optional[int] = Query(default=None, description="Фильтр по ID жанра"),
    city: Optional[str] = Query(default=None, description="Фильтр по городу"),
    session: AsyncSession = Depends(get_session)
):
    # Динамическая сборка запроса для фильтрации каталога
    statement = select(Book).where(Book.is_deleted == False)
    
    if is_available is not None:
        statement = statement.where(Book.is_available == is_available)
        
    if search:
        statement = statement.where(
            Book.title.contains(search) | Book.author.contains(search)
        )
        
    if genre_id:
        statement = statement.join(BookGenreLink).where(BookGenreLink.genre_id == genre_id)
        
    if city:
        statement = statement.join(User, Book.owner_id == User.id).join(Location, User.location_id == Location.id).where(Location.city == city)
        
    result = await session.exec(statement.offset(offset).limit(limit))
    return result.all()

@books_router.patch("/{book_id}", response_model=BookPublic)
async def update_book(book_id: int, book_data: BookUpdate, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    db_book = await session.get(Book, book_id)
    if not db_book or db_book.is_deleted:
        raise HTTPException(status_code=404, detail="Book not found")
        
    if db_book.owner_id != current_user.id and current_user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    for key, value in book_data.model_dump(exclude_unset=True).items():
        setattr(db_book, key, value)
        
    session.add(db_book)
    await session.commit()
    await session.refresh(db_book)
    return db_book

@books_router.delete("/{book_id}")
async def delete_book(book_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.owner_id != current_user.id and current_user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Мягкое удаление: скрываем книгу, но сохраняем для истории сделок
    book.is_deleted = True
    session.add(book)
    await session.commit()
    return {"ok": True, "message": "Book soft deleted"}

@books_router.post("/{book_id}/genres/{genre_id}", response_model=BookPublicWithGenres)
async def add_genre_to_book(book_id: int, genre_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    statement = select(Book).where(Book.id == book_id).options(selectinload(Book.genres))
    result = await session.exec(statement)
    book = result.first()
    
    if not book or book.is_deleted:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    genre = await session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    if genre not in book.genres:
        book.genres.append(genre)
        session.add(book)
        await session.commit()
        await session.refresh(book)
    return book