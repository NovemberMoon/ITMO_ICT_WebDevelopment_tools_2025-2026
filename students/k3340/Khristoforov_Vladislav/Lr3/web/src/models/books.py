from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

from .links import BookGenreLink, UserGenreLink, WishlistLink

if TYPE_CHECKING:
    from .users import User

class BookCondition(str, Enum):
    NEW = "new"
    GOOD = "good"
    WORN = "worn"
    POOR = "poor"

# МОДЕЛИ ЖАНРА

class GenreBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

class Genre(GenreBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    books: List["Book"] = Relationship(link_model=BookGenreLink, back_populates="genres")
    users: List["User"] = Relationship(link_model=UserGenreLink, back_populates="genres")

class GenreCreate(GenreBase):
    pass

class GenreUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None

class GenrePublic(GenreBase):
    id: int

# МОДЕЛИ КНИГИ

class BookBase(SQLModel):
    bcid: str = Field(unique=True, index=True)
    title: str
    author: str
    publication_year: int
    isbn: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    condition: BookCondition
    language: str
    is_available: bool = Field(default=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")

class Book(BookBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    owner: Optional["User"] = Relationship(back_populates="books")
    genres: List[Genre] = Relationship(link_model=BookGenreLink, back_populates="books")
    wishlisted_by: List["User"] = Relationship(link_model=WishlistLink, back_populates="wishlisted_books")

class BookCreate(BookBase):
    pass

class BookUpdate(SQLModel):
    title: Optional[str] = None
    author: Optional[str] = None
    publication_year: Optional[int] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    condition: Optional[BookCondition] = None
    is_available: Optional[bool] = None

class BookPublic(BookBase):
    id: int
    is_deleted: bool
    created_at: datetime

class BookPublicWithGenres(BookPublic):
    genres: List[GenrePublic] = []