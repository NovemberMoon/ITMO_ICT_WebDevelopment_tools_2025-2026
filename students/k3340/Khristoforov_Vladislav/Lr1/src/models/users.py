from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from .links import UserGenreLink, WishlistLink

if TYPE_CHECKING:
    from .books import Book, Genre

class Role(str, Enum):
    admin = "admin"
    user = "user"

# МОДЕЛИ ЛОКАЦИИ

class LocationBase(SQLModel):
    country: str
    city: str
    address: Optional[str] = None

class Location(LocationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    users: List["User"] = Relationship(back_populates="location")

class LocationCreate(LocationBase):
    pass

class LocationUpdate(SQLModel):
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None

class LocationPublic(LocationBase):
    id: int


# МОДЕЛИ ПОЛЬЗОВАТЕЛЯ

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location_id: Optional[int] = Field(default=None, foreign_key="location.id")

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    
    role: Role = Field(default=Role.user)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    location: Optional[Location] = Relationship(back_populates="users")
    genres: List["Genre"] = Relationship(link_model=UserGenreLink, back_populates="users")
    books: List["Book"] = Relationship(back_populates="owner")
    wishlisted_books: List["Book"] = Relationship(link_model=WishlistLink, back_populates="wishlisted_by")

class UserCreate(UserBase):
    password: str

class UserUpdate(SQLModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location_id: Optional[int] = None
    password: Optional[str] = None

class UserPublic(UserBase):
    id: int
    role: Role
    is_active: bool
    created_at: datetime

class UserPublicWithLocation(UserPublic):
    location: Optional[LocationPublic] = None