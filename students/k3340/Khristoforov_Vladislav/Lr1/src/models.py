from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

class Role(str, Enum):
    admin = "admin"
    user = "user"

class Location(BaseModel):
    id: int
    country: str
    city: str
    address: Optional[str] = None

class Genre(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

class Book(BaseModel):
    id: int
    bcid: str
    title: str
    author: str
    publication_year: int
    isbn: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    condition: str
    language: str
    is_available: bool = True
    owner_id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

class User(BaseModel):
    id: int
    username: str
    email: str
    hashed_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    
    role: Role = Role.user
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
    location: Optional[Location] = None
    
    genres: Optional[List[Genre]] = []
    books: Optional[List[Book]] = []