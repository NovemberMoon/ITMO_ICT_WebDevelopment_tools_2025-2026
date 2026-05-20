from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List

from database import get_session
from models.books import (
    Book, BookCreate, BookUpdate, BookPublic, BookPublicWithGenres,
    Genre, GenreCreate, GenreUpdate, GenrePublic
)

books_router = APIRouter(prefix="/books", tags=["Books"])
genres_router = APIRouter(prefix="/genres", tags=["Genres"])

# ЭНДПОИНТЫ ДЛЯ ЖАНРОВ

@genres_router.post("/", response_model=GenrePublic)
def create_genre(genre: GenreCreate, session: Session = Depends(get_session)):
    db_genre = Genre.model_validate(genre)
    session.add(db_genre)
    session.commit()
    session.refresh(db_genre)
    return db_genre

@genres_router.get("/", response_model=List[GenrePublic])
def read_genres(session: Session = Depends(get_session)):
    return session.exec(select(Genre)).all()

@genres_router.get("/{genre_id}", response_model=GenrePublic)
def read_genre(genre_id: int, session: Session = Depends(get_session)):
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre

@genres_router.patch("/{genre_id}", response_model=GenrePublic)
def update_genre(genre_id: int, genre_data: GenreUpdate, session: Session = Depends(get_session)):
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
def delete_genre(genre_id: int, session: Session = Depends(get_session)):
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    session.delete(genre)
    session.commit()
    return {"ok": True, "message": "Genre deleted"}

# ЭНДПОИНТЫ ДЛЯ КНИГ

@books_router.post("/", response_model=BookPublic)
def create_book(book: BookCreate, session: Session = Depends(get_session)):
    db_book = Book.model_validate(book)
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book

@books_router.get("/{book_id}", response_model=BookPublicWithGenres)
def read_book(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@books_router.get("/", response_model=List[BookPublic])
def read_books(offset: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)):
    return session.exec(select(Book).where(Book.is_deleted == False).offset(offset).limit(limit)).all()

@books_router.patch("/{book_id}", response_model=BookPublic)
def update_book(book_id: int, book_data: BookUpdate, session: Session = Depends(get_session)):
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
def delete_book(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    book.is_deleted = True
    session.add(book)
    session.commit()
    return {"ok": True, "message": "Book soft deleted"}

@books_router.post("/{book_id}/genres/{genre_id}", response_model=BookPublicWithGenres)
def add_genre_to_book(book_id: int, genre_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
        
    book.genres.append(genre)
    session.add(book)
    session.commit()
    session.refresh(book)
    return book