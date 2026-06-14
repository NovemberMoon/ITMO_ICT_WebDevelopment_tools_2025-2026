from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class UserGenreLink(SQLModel, table=True):
    __tablename__ = "user_genre"
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    genre_id: Optional[int] = Field(default=None, foreign_key="genre.id", primary_key=True)
    
    preference_level: int = Field(default=5, description="Уровень интереса от 1 до 5")


class BookGenreLink(SQLModel, table=True):
    __tablename__ = "book_genre"
    
    book_id: Optional[int] = Field(default=None, foreign_key="book.id", primary_key=True)
    genre_id: Optional[int] = Field(default=None, foreign_key="genre.id", primary_key=True)
    
    is_primary: bool = Field(default=False, description="Основной жанр книги")


class WishlistLink(SQLModel, table=True):
    __tablename__ = "wishlist"
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    book_id: Optional[int] = Field(default=None, foreign_key="book.id", primary_key=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)