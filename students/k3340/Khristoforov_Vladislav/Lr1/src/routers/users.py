from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, or_, select
from typing import List

from database import get_session
from models.books import Book, BookPublic, Genre, GenrePublic
from models.exchanges import ExchangeRequest, ExchangeRequestPublic, Review, ReviewPublic
from models.users import (
    User, UserCreate, UserPublic, UserUpdate, UserPublicWithLocation,
    Location, LocationCreate, LocationUpdate, LocationPublic
)

users_router = APIRouter(prefix="/users", tags=["Users"])
locations_router = APIRouter(prefix="/locations", tags=["Locations"])

# ЭНДПОИНТЫ ДЛЯ ЛОКАЦИЙ

@locations_router.post("/", response_model=LocationPublic)
def create_location(location: LocationCreate, session: Session = Depends(get_session)) -> LocationPublic:
    db_location = Location.model_validate(location)
    session.add(db_location)
    session.commit()
    session.refresh(db_location)
    return db_location

@locations_router.get("/", response_model=List[LocationPublic])
def read_locations(offset: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)) -> List[LocationPublic]:
    return session.exec(select(Location).offset(offset).limit(limit)).all()

@locations_router.get("/{location_id}", response_model=LocationPublic)
def read_location(location_id: int, session: Session = Depends(get_session)) -> LocationPublic:
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

@locations_router.patch("/{location_id}", response_model=LocationPublic)
def update_location(location_id: int, loc_data: LocationUpdate, session: Session = Depends(get_session)) -> LocationPublic:
    db_location = session.get(Location, location_id)
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")
        
    for key, value in loc_data.model_dump(exclude_unset=True).items():
        setattr(db_location, key, value)
        
    session.add(db_location)
    session.commit()
    session.refresh(db_location)
    return db_location

@locations_router.delete("/{location_id}")
def delete_location(location_id: int, session: Session = Depends(get_session)) -> dict:
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    session.delete(location)
    session.commit()
    return {"ok": True, "message": "Location deleted"}

# ЭНДПОИНТЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ

@users_router.post("/", response_model=UserPublic)
def create_user(user: UserCreate, session: Session = Depends(get_session)) -> UserPublic:
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    db_user = User.model_validate(user, update={"hashed_password": user.password})
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@users_router.get("/", response_model=List[UserPublic])
def read_users(offset: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)) -> List[UserPublic]:
    return session.exec(select(User).where(User.is_active == True).offset(offset).limit(limit)).all()

@users_router.get("/{user_id}", response_model=UserPublicWithLocation)
def read_user(user_id: int, session: Session = Depends(get_session)) -> UserPublicWithLocation:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@users_router.patch("/{user_id}", response_model=UserPublic)
def update_user(user_id: int, user_data: UserUpdate, session: Session = Depends(get_session)) -> UserPublic:
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    for key, value in user_data.model_dump(exclude_unset=True).items():
        if key == "password":
            setattr(db_user, "hashed_password", value)
        else:
            setattr(db_user, key, value)
            
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@users_router.delete("/{user_id}")
def delete_user(user_id: int, session: Session = Depends(get_session)) -> dict:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # МЯГКОЕ УДАЛЕНИЕ - помечаем пользователя как неактивного, но не удаляем из базы данных
    user.is_active = False
    session.add(user)
    session.commit()
    return {"ok": True, "message": "User deactivated"}

# ВИШЛИСТ ПОЛЬЗОВАТЕЛЯ

@users_router.get("/{user_id}/wishlist", response_model=List[BookPublic])
def get_wishlist(user_id: int, session: Session = Depends(get_session)) -> List[BookPublic]:
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user.wishlisted_books

@users_router.post("/{user_id}/wishlist/{book_id}")
def add_to_wishlist(user_id: int, book_id: int, session: Session = Depends(get_session)) -> dict:
    # ДОБАВЛЕНИЕ СВЯЗИ MANY-TO-MANY:
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
        
    book = session.get(Book, book_id)
    if not book or book.is_deleted:
        raise HTTPException(status_code=404, detail="Book not found")
        
    if book in user.wishlisted_books:
         raise HTTPException(status_code=400, detail="Book already in wishlist")

    user.wishlisted_books.append(book)
    session.add(user)
    session.commit()
    return {"ok": True, "message": "Book added to wishlist"}

@users_router.delete("/{user_id}/wishlist/{book_id}")
def remove_from_wishlist(user_id: int, book_id: int, session: Session = Depends(get_session)) -> dict:
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
        
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    if book not in user.wishlisted_books:
         raise HTTPException(status_code=400, detail="Book not in wishlist")

    user.wishlisted_books.remove(book)
    session.add(user)
    session.commit()
    return {"ok": True, "message": "Book removed from wishlist"}

# ИНТЕРЕСЫ ПОЛЬЗОВАТЕЛЯ

@users_router.get("/{user_id}/genres", response_model=List[GenrePublic])
def get_user_genres(user_id: int, session: Session = Depends(get_session)) -> List[GenrePublic]:
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return user.genres

@users_router.post("/{user_id}/genres/{genre_id}")
def add_user_genre(user_id: int, genre_id: int, session: Session = Depends(get_session)) -> dict:
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
        
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
        
    if genre in user.genres:
         raise HTTPException(status_code=400, detail="Genre already in user interests")

    user.genres.append(genre)
    session.add(user)
    session.commit()
    return {"ok": True, "message": "Genre added to user interests"}

@users_router.delete("/{user_id}/genres/{genre_id}")
def remove_user_genre(user_id: int, genre_id: int, session: Session = Depends(get_session)) -> dict:
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
        
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
        
    if genre not in user.genres:
         raise HTTPException(status_code=400, detail="Genre not in user interests")

    user.genres.remove(genre)
    session.add(user)
    session.commit()
    return {"ok": True, "message": "Genre removed from user interests"}

# КНИГИ ПОЛЬЗОВАТЕЛЯ

@users_router.get("/{user_id}/books", response_model=List[BookPublic])
def get_user_books(user_id: int, session: Session = Depends(get_session)) -> List[BookPublic]:
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Возвращаем только не удаленные книги, владельцем которых является пользователь
    books = session.exec(select(Book).where(Book.owner_id == user_id, Book.is_deleted == False)).all()
    return books


# ИСТОРИЯ ОБМЕНОВ ПОЛЬЗОВАТЕЛЯ

@users_router.get("/{user_id}/exchanges", response_model=List[ExchangeRequestPublic])
def get_user_exchanges(user_id: int, session: Session = Depends(get_session)) -> List[ExchangeRequestPublic]:
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    # Сложный запрос: ищем обмены, где пользователь либо просил книгу, либо просили ЕГО книгу.
    statement = select(ExchangeRequest).join(Book, ExchangeRequest.requested_book_id == Book.id).where(
        or_(
            ExchangeRequest.requester_id == user_id,
            Book.owner_id == user_id
        ),
        ExchangeRequest.is_deleted == False
    )
    return session.exec(statement).all()

# ОТЗЫВЫ О ПОЛЬЗОВАТЕЛЕ

@users_router.get("/{user_id}/reviews", response_model=List[ReviewPublic])
def get_user_reviews(user_id: int, session: Session = Depends(get_session)) -> List[ReviewPublic]:
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    # Ищем отзывы, написанные НА этого пользователя (рейтинг юзера)
    statement = select(Review).where(Review.target_user_id == user_id, Review.is_deleted == False)
    return session.exec(statement).all()