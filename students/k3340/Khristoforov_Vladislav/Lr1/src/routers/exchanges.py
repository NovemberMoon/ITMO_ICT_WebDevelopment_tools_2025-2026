from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List

from database import get_session
from models.books import Book
from models.exchanges import (
    ExchangeRequest, ExchangeRequestCreate, ExchangeRequestUpdate, ExchangeRequestPublic, ExchangeStatus,
    Review, ReviewCreate, ReviewUpdate, ReviewPublic
)
from models.users import Role, User
from routers.auth import get_current_user

exchanges_router = APIRouter(prefix="/exchanges", tags=["Exchanges"])
reviews_router = APIRouter(prefix="/reviews", tags=["Reviews"])

# ЭНДПОИНТЫ ДЛЯ ОБМЕНОВ

@exchanges_router.post("/", response_model=ExchangeRequestPublic)
def create_exchange(exchange: ExchangeRequestCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> ExchangeRequestPublic:
    exchange.requester_id = current_user.id

    # ЗАЩИТА: Нельзя запросить книгу, которая недоступна
    requested_book = session.get(Book, exchange.requested_book_id)
    if not requested_book or not requested_book.is_available or requested_book.is_deleted:
        raise HTTPException(status_code=400, detail="Requested book is not available")
        
    # ЗАЩИТА: Нельзя запросить свою же собственную книгу
    if requested_book.owner_id == exchange.requester_id:
        raise HTTPException(status_code=400, detail="You cannot request your own book")

    # ЗАЩИТА: Предложенная взамен книга должна принадлежать инициатору обмена
    if exchange.offered_book_id:
        offered_book = session.get(Book, exchange.offered_book_id)
        if not offered_book or not offered_book.is_available or offered_book.is_deleted:
            raise HTTPException(status_code=400, detail="Offered book is not available")
        if offered_book.owner_id != exchange.requester_id:
            raise HTTPException(status_code=403, detail="You can only offer your own books for exchange")

    db_exchange = ExchangeRequest.model_validate(exchange)
    session.add(db_exchange)
    session.commit()
    session.refresh(db_exchange)
    return db_exchange

@exchanges_router.get("/", response_model=List[ExchangeRequestPublic])
def read_exchanges(offset: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)) -> List[ExchangeRequestPublic]:
    return session.exec(select(ExchangeRequest).where(ExchangeRequest.is_deleted == False).offset(offset).limit(limit)).all()

@exchanges_router.get("/{exchange_id}", response_model=ExchangeRequestPublic)
def read_exchange(exchange_id: int, session: Session = Depends(get_session)) -> ExchangeRequestPublic:
    exchange = session.get(ExchangeRequest, exchange_id)
    if not exchange:
        raise HTTPException(status_code=404, detail="Exchange request not found")
    return exchange

@exchanges_router.patch("/{exchange_id}", response_model=ExchangeRequestPublic)
def update_exchange(
    exchange_id: int, 
    exchange_data: ExchangeRequestUpdate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> ExchangeRequestPublic:
    db_exchange = session.get(ExchangeRequest, exchange_id)
    if not db_exchange or db_exchange.is_deleted:
        raise HTTPException(status_code=404, detail="Exchange request not found")
        
    requested_book = session.get(Book, db_exchange.requested_book_id)
    
    # Изменять сделку (менять статус, вносить трек-номера и т.д.) может:
    # 1. Администратор (без ограничений)
    # 2. Владелец запрошенной книги
    # 3. Инициатор обмена (но исключительно для перевода сделки в статус REJECTED — отмена)
    if current_user.role != Role.admin and current_user.id != requested_book.owner_id:
        if not (current_user.id == db_exchange.requester_id and exchange_data.status == ExchangeStatus.REJECTED):
            raise HTTPException(status_code=403, detail="Not enough permissions to update this exchange")

    old_status = db_exchange.status

    # ЗАЩИТА: Заморозка завершенных/отмененных сделок для обычных пользователей.
    # Администратор может обходить эту блокировку для ручной корректировки в случае форс-мажора.
    if current_user.role != Role.admin:
        if old_status in [ExchangeStatus.COMPLETED, ExchangeStatus.REJECTED] and exchange_data.status and exchange_data.status != old_status:
             raise HTTPException(status_code=400, detail="Cannot change the status of a finalized exchange")

    for key, value in exchange_data.model_dump(exclude_unset=True).items():
        setattr(db_exchange, key, value)
        
    new_status = db_exchange.status

    requested_book = session.get(Book, db_exchange.requested_book_id)
    offered_book = session.get(Book, db_exchange.offered_book_id) if db_exchange.offered_book_id else None

    # ЛОГИКА 1: Бронь при принятии заявки (ACCEPTED)
    if old_status != ExchangeStatus.ACCEPTED and new_status == ExchangeStatus.ACCEPTED:
        # ЗАЩИТА ОТ ДВОЙНОГО БРОНИРОВАНИЯ
        if requested_book and not requested_book.is_available:
            raise HTTPException(status_code=400, detail="Requested book is already reserved by another exchange")
        if offered_book and not offered_book.is_available:
            raise HTTPException(status_code=400, detail="Offered book is already reserved by another exchange")

        if requested_book: requested_book.is_available = False
        if offered_book: offered_book.is_available = False
        session.add(requested_book)
        if offered_book: session.add(offered_book)

    # ЛОГИКА 2: Снятие брони, если заявка отменена/отклонена (REJECTED)
    elif old_status == ExchangeStatus.ACCEPTED and new_status == ExchangeStatus.REJECTED:
        if requested_book: requested_book.is_available = True
        if offered_book: offered_book.is_available = True
        session.add(requested_book)
        if offered_book: session.add(offered_book)

    # ЛОГИКА 3: Смена владельца при завершении (COMPLETED)
    elif old_status != ExchangeStatus.COMPLETED and new_status == ExchangeStatus.COMPLETED:
        if requested_book:
            old_owner_id = requested_book.owner_id
            requested_book.owner_id = db_exchange.requester_id
            requested_book.is_available = False # Новый хозяин начинает читать
            session.add(requested_book)

            if offered_book:
                offered_book.owner_id = old_owner_id
                offered_book.is_available = False
                session.add(offered_book)
                
        db_exchange.completed_at = datetime.now(timezone.utc)

    session.add(db_exchange)
    session.commit()
    session.refresh(db_exchange)
    return db_exchange

@exchanges_router.delete("/{exchange_id}")
def delete_exchange(
    exchange_id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    exchange = session.get(ExchangeRequest, exchange_id)
    if not exchange:
        raise HTTPException(status_code=404, detail="Exchange request not found")
        
    # Удалить (архивировать) заявку может её инициатор ИЛИ АДМИН
    if exchange.requester_id != current_user.id and current_user.role != Role.admin:
        raise HTTPException(status_code=403, detail="You can only delete your own exchanges")
        
    # ЗАЩИТА: Снятие брони при удалении активной заявки
    if exchange.status == ExchangeStatus.ACCEPTED:
        requested_book = session.get(Book, exchange.requested_book_id)
        offered_book = session.get(Book, exchange.offered_book_id) if exchange.offered_book_id else None
        if requested_book: requested_book.is_available = True
        if offered_book: offered_book.is_available = True
        session.add(requested_book)
        if offered_book: session.add(offered_book)
        exchange.status = ExchangeStatus.REJECTED # Безопасный перевод статуса

    exchange.is_deleted = True # Архивация (мягкое удаление)
    session.add(exchange)
    session.commit()
    return {"ok": True, "message": "Exchange request archived and reservations released"}

# ЭНДПОИНТЫ ДЛЯ ОТЗЫВОВ

@reviews_router.post("/", response_model=ReviewPublic)
def create_review(review: ReviewCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> ReviewPublic:
    review.author_id = current_user.id

    # ЗАЩИТА БИЗНЕС-ЛОГИКИ: Валидация отзыва
    exchange = session.get(ExchangeRequest, review.exchange_id)
    if not exchange or exchange.is_deleted:
        raise HTTPException(status_code=404, detail="Exchange not found")
        
    if exchange.status != ExchangeStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only review completed exchanges")
        
    if review.author_id == review.target_user_id:
        raise HTTPException(status_code=400, detail="You cannot review yourself")
        
    # Проверка, что оба юзера реально участвовали в сделке
    requested_book = session.get(Book, exchange.requested_book_id)
    if not requested_book:
        raise HTTPException(status_code=400, detail="Original book not found")
        
    participants = {exchange.requester_id, requested_book.owner_id}
    if review.author_id not in participants or review.target_user_id not in participants:
        raise HTTPException(status_code=400, detail="Users did not participate in this exchange")

    # ЗАЩИТА: Защита от спама (один отзыв от одного автора на одну сделку)
    existing_review = session.exec(
        select(Review).where(
            Review.exchange_id == review.exchange_id,
            Review.author_id == review.author_id
        )
    ).first()
    if existing_review:
         raise HTTPException(status_code=400, detail="You have already reviewed this exchange")

    db_review = Review.model_validate(review)
    session.add(db_review)
    session.commit()
    session.refresh(db_review)
    return db_review

@reviews_router.get("/", response_model=List[ReviewPublic])
def read_reviews(offset: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)) -> List[ReviewPublic]:
    return session.exec(select(Review).where(Review.is_deleted == False).offset(offset).limit(limit)).all()

@reviews_router.get("/{review_id}", response_model=ReviewPublic)
def read_review(review_id: int, session: Session = Depends(get_session)) -> ReviewPublic:
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

@reviews_router.patch("/{review_id}", response_model=ReviewPublic)
def update_review(review_id: int, review_data: ReviewUpdate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> ReviewPublic:
    db_review = session.get(Review, review_id)
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")

    if db_review.author_id != current_user.id and current_user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions to update this review")

    for key, value in review_data.model_dump(exclude_unset=True).items():
        setattr(db_review, key, value)
        
    session.add(db_review)
    session.commit()
    session.refresh(db_review)
    return db_review

@reviews_router.delete("/{review_id}")
def delete_review(review_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> dict:
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.author_id != current_user.id and current_user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions to delete this review")

    # МЯГКОЕ УДАЛЕНИЕ - помечаем запись как удаленную, но не удаляем из базы данных
    review.is_deleted = True
    session.add(review)
    session.commit()
    return {"ok": True, "message": "Review soft deleted"}