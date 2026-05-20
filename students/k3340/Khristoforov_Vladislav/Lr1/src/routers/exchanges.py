from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List

from database import get_session
from models.exchanges import (
    ExchangeRequest, ExchangeRequestCreate, ExchangeRequestUpdate, ExchangeRequestPublic,
    Review, ReviewCreate, ReviewUpdate, ReviewPublic
)

exchanges_router = APIRouter(prefix="/exchanges", tags=["Exchanges"])
reviews_router = APIRouter(prefix="/reviews", tags=["Reviews"])

# ЭНДПОИНТЫ ДЛЯ ОБМЕНОВ

@exchanges_router.post("/", response_model=ExchangeRequestPublic)
def create_exchange(exchange: ExchangeRequestCreate, session: Session = Depends(get_session)):
    db_exchange = ExchangeRequest.model_validate(exchange)
    session.add(db_exchange)
    session.commit()
    session.refresh(db_exchange)
    return db_exchange

@exchanges_router.get("/", response_model=List[ExchangeRequestPublic])
def read_exchanges(offset: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)):
    return session.exec(select(ExchangeRequest).where(ExchangeRequest.is_deleted == False).offset(offset).limit(limit)).all()

@exchanges_router.get("/{exchange_id}", response_model=ExchangeRequestPublic)
def read_exchange(exchange_id: int, session: Session = Depends(get_session)):
    exchange = session.get(ExchangeRequest, exchange_id)
    if not exchange:
        raise HTTPException(status_code=404, detail="Exchange request not found")
    return exchange

@exchanges_router.patch("/{exchange_id}", response_model=ExchangeRequestPublic)
def update_exchange(exchange_id: int, exchange_data: ExchangeRequestUpdate, session: Session = Depends(get_session)):
    db_exchange = session.get(ExchangeRequest, exchange_id)
    if not db_exchange:
        raise HTTPException(status_code=404, detail="Exchange request not found")
        
    for key, value in exchange_data.model_dump(exclude_unset=True).items():
        setattr(db_exchange, key, value)
        
    session.add(db_exchange)
    session.commit()
    session.refresh(db_exchange)
    return db_exchange

@exchanges_router.delete("/{exchange_id}")
def delete_exchange(exchange_id: int, session: Session = Depends(get_session)):
    exchange = session.get(ExchangeRequest, exchange_id)
    if not exchange:
        raise HTTPException(status_code=404, detail="Exchange request not found")
        
    exchange.is_deleted = True
    session.add(exchange)
    session.commit()
    return {"ok": True, "message": "Exchange request soft deleted (archived)"}

# ЭНДПОИНТЫ ДЛЯ ОТЗЫВОВ

@reviews_router.post("/", response_model=ReviewPublic)
def create_review(review: ReviewCreate, session: Session = Depends(get_session)):
    db_review = Review.model_validate(review)
    session.add(db_review)
    session.commit()
    session.refresh(db_review)
    return db_review

@reviews_router.get("/", response_model=List[ReviewPublic])
def read_reviews(offset: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)):
    return session.exec(select(Review).where(Review.is_deleted == False).offset(offset).limit(limit)).all()

@reviews_router.get("/{review_id}", response_model=ReviewPublic)
def read_review(review_id: int, session: Session = Depends(get_session)):
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

@reviews_router.patch("/{review_id}", response_model=ReviewPublic)
def update_review(review_id: int, review_data: ReviewUpdate, session: Session = Depends(get_session)):
    db_review = session.get(Review, review_id)
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
        
    for key, value in review_data.model_dump(exclude_unset=True).items():
        setattr(db_review, key, value)
        
    session.add(db_review)
    session.commit()
    session.refresh(db_review)
    return db_review

@reviews_router.delete("/{review_id}")
def delete_review(review_id: int, session: Session = Depends(get_session)):
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.is_deleted = True
    session.add(review)
    session.commit()
    return {"ok": True, "message": "Review soft deleted"}