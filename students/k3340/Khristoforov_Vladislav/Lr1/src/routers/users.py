from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import or_, select
from sqlalchemy.orm import selectinload
from typing import List

from database import get_session
from models.books import Book, BookPublic, Genre, GenrePublic
from models.exchanges import ExchangeRequest, ExchangeRequestPublic, Review, ReviewPublic
from models.users import (
    Role, User, UserChangePassword, UserPublic, UserUpdate, UserPublicWithLocation,
    Location, LocationCreate, LocationUpdate, LocationPublic
)

from routers.auth import get_current_admin, get_current_user

users_router = APIRouter(prefix="/users", tags=["Users"])
locations_router = APIRouter(prefix="/locations", tags=["Locations"])

# --- ЛОКАЦИИ ---

@locations_router.post("/", response_model=LocationPublic, dependencies=[Depends(get_current_admin)])
async def create_location(location: LocationCreate, session: AsyncSession = Depends(get_session)):
    db_location = Location.model_validate(location)
    session.add(db_location)
    await session.commit()
    await session.refresh(db_location)
    return db_location

@locations_router.get("/", response_model=List[LocationPublic])
async def read_locations(offset: int = 0, limit: int = Query(default=100, le=100), session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(Location).offset(offset).limit(limit))
    return result.all()

@locations_router.get("/{location_id}", response_model=LocationPublic)
async def read_location(location_id: int, session: AsyncSession = Depends(get_session)):
    location = await session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

@locations_router.patch("/{location_id}", response_model=LocationPublic, dependencies=[Depends(get_current_admin)])
async def update_location(location_id: int, loc_data: LocationUpdate, session: AsyncSession = Depends(get_session)):
    db_location = await session.get(Location, location_id)
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")
        
    loc_data_dict = loc_data.model_dump(exclude_unset=True)
    for key, value in loc_data_dict.items():
        setattr(db_location, key, value)
        
    session.add(db_location)
    await session.commit()
    await session.refresh(db_location)
    return db_location

@locations_router.delete("/{location_id}", dependencies=[Depends(get_current_admin)])
async def delete_location(location_id: int, session: AsyncSession = Depends(get_session)):
    location = await session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    await session.delete(location)
    await session.commit()
    return {"ok": True, "message": "Location deleted"}

# --- ПОЛЬЗОВАТЕЛИ ---

@users_router.get("/", response_model=List[UserPublic])
async def read_users(offset: int = 0, limit: int = Query(default=100, le=100), session: AsyncSession = Depends(get_session)):
    # Выводим только активных юзеров (исключая забаненных/удаленных)
    result = await session.exec(select(User).where(User.is_active == True).offset(offset).limit(limit))
    return result.all()

@users_router.get("/me", response_model=UserPublicWithLocation)
async def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user

@users_router.get("/{user_id}", response_model=UserPublicWithLocation)
async def read_user(user_id: int, session: AsyncSession = Depends(get_session)):
    # Упреждающая загрузка (selectinload) для получения данных о локации вместе с пользователем
    statement = select(User).where(User.id == user_id).options(selectinload(User.location))
    result = await session.exec(statement)
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@users_router.patch("/{user_id}", response_model=UserPublic)
async def update_user(user_id: int, user_data: UserUpdate, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    # Проверка прав: редактировать профиль может только владелец или администратор
    if current_user.id != user_id and current_user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions to edit this profile")

    db_user = await session.get(User, user_id)
    if not db_user or not db_user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
        
    for key, value in user_data.model_dump(exclude_unset=True).items():
        setattr(db_user, key, value)
        
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

@users_router.post("/{user_id}/password")
async def change_password(
    user_id: int,
    password_data: UserChangePassword,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
        
    from security import verify_password, get_password_hash
    
    if not verify_password(password_data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
        
    user.hashed_password = get_password_hash(password_data.new_password)
    session.add(user)
    await session.commit()
    return {"ok": True, "message": "Password changed successfully"}

@users_router.delete("/{user_id}")
async def delete_user(
    user_id: int, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions to delete this profile")

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Мягкое удаление: вместо `session.delete(user)` скрываем флажком,
    # чтобы не сломать историю обменов в базе данных
    user.is_active = False 
    session.add(user)
    await session.commit()
    return {"ok": True, "message": "User soft deleted"}

# --- ВИШЛИСТЫ ---

@users_router.get("/{user_id}/wishlist", response_model=List[BookPublic])
async def get_wishlist(user_id: int, session: AsyncSession = Depends(get_session)):
    # Подгружаем M:M связь (wishlisted_books) с помощью асинхронного selectinload
    statement = select(User).where(User.id == user_id, User.is_active == True).options(selectinload(User.wishlisted_books))
    result = await session.exec(statement)
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user.wishlisted_books

@users_router.post("/{user_id}/wishlist/{book_id}")
async def add_to_wishlist(user_id: int, book_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    statement = select(User).where(User.id == user_id, User.is_active == True).options(selectinload(User.wishlisted_books))
    result = await session.exec(statement)
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    book = await session.get(Book, book_id)
    if not book or book.is_deleted:
        raise HTTPException(status_code=404, detail="Book not found")
        
    if book in user.wishlisted_books:
         raise HTTPException(status_code=400, detail="Book already in wishlist")

    user.wishlisted_books.append(book)
    session.add(user)
    await session.commit()
    return {"ok": True, "message": "Book added to wishlist"}

@users_router.delete("/{user_id}/wishlist/{book_id}")
async def remove_from_wishlist(user_id: int, book_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    statement = select(User).where(User.id == user_id, User.is_active == True).options(selectinload(User.wishlisted_books))
    result = await session.exec(statement)
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    if book not in user.wishlisted_books:
         raise HTTPException(status_code=400, detail="Book not in wishlist")

    user.wishlisted_books.remove(book)
    session.add(user)
    await session.commit()
    return {"ok": True, "message": "Book removed from wishlist"}

# --- ИНТЕРЕСЫ ПОЛЬЗОВАТЕЛЯ ---

@users_router.get("/{user_id}/genres", response_model=List[GenrePublic])
async def get_user_genres(user_id: int, session: AsyncSession = Depends(get_session)):
    statement = select(User).where(User.id == user_id, User.is_active == True).options(selectinload(User.genres))
    result = await session.exec(statement)
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.genres

@users_router.post("/{user_id}/genres/{genre_id}")
async def add_user_genre(user_id: int, genre_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    statement = select(User).where(User.id == user_id, User.is_active == True).options(selectinload(User.genres))
    result = await session.exec(statement)
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    genre = await session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
        
    if genre in user.genres:
         raise HTTPException(status_code=400, detail="Genre already in user interests")

    user.genres.append(genre)
    session.add(user)
    await session.commit()
    return {"ok": True, "message": "Genre added to user interests"}

@users_router.delete("/{user_id}/genres/{genre_id}")
async def remove_user_genre(user_id: int, genre_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    statement = select(User).where(User.id == user_id, User.is_active == True).options(selectinload(User.genres))
    result = await session.exec(statement)
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    genre = await session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
        
    if genre not in user.genres:
         raise HTTPException(status_code=400, detail="Genre not in user interests")

    user.genres.remove(genre)
    session.add(user)
    await session.commit()
    return {"ok": True, "message": "Genre removed from user interests"}

# --- КНИГИ ПОЛЬЗОВАТЕЛЯ ---

@users_router.get("/{user_id}/books", response_model=List[BookPublic])
async def get_user_books(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await session.exec(select(Book).where(Book.owner_id == user_id, Book.is_deleted == False))
    return result.all()


# --- ИСТОРИЯ ОБМЕНОВ И ОТЗЫВЫ ---

@users_router.get("/{user_id}/exchanges", response_model=List[ExchangeRequestPublic])
async def get_user_exchanges(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    statement = select(ExchangeRequest).join(Book, ExchangeRequest.requested_book_id == Book.id).where(
        or_(
            ExchangeRequest.requester_id == user_id,
            Book.owner_id == user_id
        ),
        ExchangeRequest.is_deleted == False
    )
    result = await session.exec(statement)
    return result.all()

@users_router.get("/{user_id}/reviews", response_model=List[ReviewPublic])
async def get_user_reviews(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    statement = select(Review).where(Review.target_user_id == user_id, Review.is_deleted == False)
    result = await session.exec(statement)
    return result.all()