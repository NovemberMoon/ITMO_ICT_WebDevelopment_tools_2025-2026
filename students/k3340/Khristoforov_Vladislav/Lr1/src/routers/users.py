from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List

from database import get_session
from models.users import (
    User, UserCreate, UserPublic, UserUpdate, UserPublicWithLocation,
    Location, LocationCreate, LocationUpdate, LocationPublic
)

users_router = APIRouter(prefix="/users", tags=["Users"])
locations_router = APIRouter(prefix="/locations", tags=["Locations"])

# ЭНДПОИНТЫ ДЛЯ ЛОКАЦИЙ

@locations_router.post("/", response_model=LocationPublic)
def create_location(location: LocationCreate, session: Session = Depends(get_session)):
    db_location = Location.model_validate(location)
    session.add(db_location)
    session.commit()
    session.refresh(db_location)
    return db_location

@locations_router.get("/", response_model=List[LocationPublic])
def read_locations(offset: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)):
    return session.exec(select(Location).offset(offset).limit(limit)).all()

@locations_router.get("/{location_id}", response_model=LocationPublic)
def read_location(location_id: int, session: Session = Depends(get_session)):
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

@locations_router.patch("/{location_id}", response_model=LocationPublic)
def update_location(location_id: int, loc_data: LocationUpdate, session: Session = Depends(get_session)):
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
def delete_location(location_id: int, session: Session = Depends(get_session)):
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    session.delete(location)
    session.commit()
    return {"ok": True, "message": "Location deleted"}

# ЭНДПОИНТЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ

@users_router.post("/", response_model=UserPublic)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    db_user = User.model_validate(user, update={"hashed_password": user.password})
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@users_router.get("/", response_model=List[UserPublic])
def read_users(offset: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)):
    return session.exec(select(User).where(User.is_active == True).offset(offset).limit(limit)).all()

@users_router.get("/{user_id}", response_model=UserPublicWithLocation)
def read_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@users_router.patch("/{user_id}", response_model=UserPublic)
def update_user(user_id: int, user_data: UserUpdate, session: Session = Depends(get_session)):
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
def delete_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    session.add(user)
    session.commit()
    return {"ok": True, "message": "User deactivated"}