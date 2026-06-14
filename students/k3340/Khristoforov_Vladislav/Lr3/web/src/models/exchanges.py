from typing import Optional
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field

class ExchangeStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"

# ЗАПРОСЫ НА ОБМЕН

class ExchangeRequestBase(SQLModel):
    requester_id: int = Field(foreign_key="user.id")
    requested_book_id: int = Field(foreign_key="book.id")
    offered_book_id: Optional[int] = Field(default=None, foreign_key="book.id")
    comment: Optional[str] = None
    tracking_info: Optional[str] = None

class ExchangeRequest(ExchangeRequestBase, table=True):
    __tablename__ = "exchange_request"
    id: Optional[int] = Field(default=None, primary_key=True)
    
    status: ExchangeStatus = Field(default=ExchangeStatus.PENDING)
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class ExchangeRequestCreate(ExchangeRequestBase):
    pass

class ExchangeRequestUpdate(SQLModel):
    status: Optional[ExchangeStatus] = None
    comment: Optional[str] = None
    tracking_info: Optional[str] = None
    completed_at: Optional[datetime] = None

class ExchangeRequestPublic(ExchangeRequestBase):
    id: int
    status: ExchangeStatus
    created_at: datetime
    completed_at: Optional[datetime]

# ОТЗЫВЫ

class ReviewBase(SQLModel):
    author_id: int = Field(foreign_key="user.id")
    target_user_id: int = Field(foreign_key="user.id")
    exchange_id: int = Field(foreign_key="exchange_request.id")
    rating: int = Field(ge=1, le=5)
    text: Optional[str] = None

class Review(ReviewBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ReviewCreate(ReviewBase):
    pass

class ReviewUpdate(SQLModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    text: Optional[str] = None

class ReviewPublic(ReviewBase):
    id: int
    created_at: datetime