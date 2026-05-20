from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional

from database import get_session
from models.books import (
    Book, BookCreate, BookUpdate, BookPublic, BookPublicWithGenres,
    Genre, GenreCreate, GenreUpdate, GenrePublic
)
from models.links import BookGenreLink
from models.users import Location, User

books_router = APIRouter(prefix="/books", tags=["Books"])
genres_router = APIRouter(prefix="/genres", tags=["Genres"])

# ЭНДПОИНТЫ ДЛЯ ЖАНРОВ

@genres_router.post("/", response_model=GenrePublic)
def create_genre(genre: GenreCreate, session: Session = Depends(get_session)) -> GenrePublic:
    db_genre = Genre.model_validate(genre)
    session.add(db_genre)
    session.commit()
    session.refresh(db_genre)
    return db_genre

@genres_router.get("/", response_model=List[GenrePublic])
def read_genres(session: Session = Depends(get_session)) -> List[GenrePublic]:
    return session.exec(select(Genre)).all()

@genres_router.get("/{genre_id}", response_model=GenrePublic)
def read_genre(genre_id: int, session: Session = Depends(get_session)) -> GenrePublic:
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre

@genres_router.patch("/{genre_id}", response_model=GenrePublic)
def update_genre(genre_id: int, genre_data: GenreUpdate, session: Session = Depends(get_session)) -> GenrePublic:
    db_genre = session.get(Genre, genre_id)
    if not db_genre:
        raise HTTPException(status_code=404, detail="Genre not found")
        
    for key, value in genre_data.model_dump(exclude_unset=True).items():
        setattr(db_genre, key, value)
        
    session.add(db_genre)
    session.commit()
    session.refresh(db_genre)
    return db_genre

@genres_router.delete("/{genre_id}")
def delete_genre(genre_id: int, session: Session = Depends(get_session)) -> dict:
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    session.delete(genre)
    session.commit()
    return {"ok": True, "message": "Genre deleted"}

# ЭНДПОИНТЫ ДЛЯ КНИГ

@books_router.post("/", response_model=BookPublic)
def create_book(book: BookCreate, session: Session = Depends(get_session)) -> BookPublic:
    db_book = Book.model_validate(book)
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book

# ЛОГИКА БУККРОССИНГА: Поиск книги по уникальному физическому номеру (BCID)
@books_router.get("/bcid/{bcid}", response_model=BookPublicWithGenres)
def read_book_by_bcid(bcid: str, session: Session = Depends(get_session)) -> BookPublicWithGenres:
    book = session.exec(select(Book).where(Book.bcid == bcid, Book.is_deleted == False)).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found or deleted")
    return book

@books_router.get("/{book_id}", response_model=BookPublicWithGenres)
def read_book(book_id: int, session: Session = Depends(get_session)) -> BookPublicWithGenres:
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@books_router.get("/", response_model=List[BookPublic])
def read_books(
    offset: int = 0, 
    limit: int = Query(default=100, le=100), 
    is_available: Optional[bool] = Query(default=None, description="Фильтр по доступности"),
    search: Optional[str] = Query(default=None, description="Поиск по названию или автору"),
    genre_id: Optional[int] = Query(default=None, description="Фильтр по ID жанра"),
    city: Optional[str] = Query(default=None, description="Фильтр по городу"),
    session: Session = Depends(get_session)
) -> List[BookPublic]:
    
    statement = select(Book).where(Book.is_deleted == False)
    
    if is_available is not None:
        statement = statement.where(Book.is_available == is_available)
        
    if search:
        # Ищем совпадения в названии или авторе
        statement = statement.where(
            Book.title.contains(search) | Book.author.contains(search)
        )
        
    if genre_id:
        # Фильтрация Many-to-Many: джойним промежуточную таблицу
        statement = statement.join(BookGenreLink).where(BookGenreLink.genre_id == genre_id)
        
    if city:
        # Сложный JOIN: Книга -> Пользователь (владелец) -> Локация (город)
        statement = statement.join(User, Book.owner_id == User.id).join(Location, User.location_id == Location.id).where(Location.city == city)
        
    return session.exec(statement.offset(offset).limit(limit)).all()


@books_router.patch("/{book_id}", response_model=BookPublic)
def update_book(book_id: int, book_data: BookUpdate, session: Session = Depends(get_session)) -> BookPublic:
    db_book = session.get(Book, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    for key, value in book_data.model_dump(exclude_unset=True).items():
        setattr(db_book, key, value)
        
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book

@books_router.delete("/{book_id}")
def delete_book(book_id: int, session: Session = Depends(get_session)) -> dict:
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # МЯГКОЕ УДАЛЕНИЕ - помечаем запись как удаленную, но не удаляем из базы данных
    book.is_deleted = True
    session.add(book)
    session.commit()
    return {"ok": True, "message": "Book soft deleted"}

@books_router.post("/{book_id}/genres/{genre_id}", response_model=BookPublicWithGenres)
def add_genre_to_book(book_id: int, genre_id: int, session: Session = Depends(get_session)) -> BookPublicWithGenres:
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    # ДОБАВЛЕНИЕ СВЯЗИ MANY-TO-MANY МЕЖДУ КНИГОЙ И ЖАНРОМ - добавляем жанр в список жанров книги, SQLModel автоматически создаст запись в связующей таблице
    book.genres.append(genre)
    session.add(book)
    session.commit()
    session.refresh(book)
    return book