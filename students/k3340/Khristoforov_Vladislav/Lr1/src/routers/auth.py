from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
import jwt

from database import get_session
from models.users import Role, User, UserCreate, UserPublic
from security import verify_password, get_password_hash, create_access_token
from config import settings

auth_router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@auth_router.post("/register", response_model=UserPublic)
def register(user: UserCreate, session: Session = Depends(get_session)) -> UserPublic:
    # Проверяем, существует ли пользователь с таким логином
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    existing_email = session.exec(select(User).where(User.email == user.email)).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Хешируем пароль и создаем пользователя
    hashed_pwd = get_password_hash(user.password)
    db_user = User.model_validate(user, update={"hashed_password": hashed_pwd})
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@auth_router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)) -> dict:
    # 1. Ищем пользователя по username
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    
    # 2. Проверяем, есть ли пользователь и совпадает ли пароль
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Генерируем токен
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # 4. Возвращаем ответ в стандарте OAuth2
    return {"access_token": access_token, "token_type": "bearer"}

# ЗАВИСИМОСТЬ ДЛЯ ИДЕНТИФИКАЦИИ

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    """
    Эта функция будет "вешаться" на защищенные эндпоинты.
    Она берет токен из заголовка запроса, расшифровывает его и находит юзера в БД.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Расшифровываем токен с помощью нашего секретного ключа
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.InvalidTokenError: # Ловит просроченные и поддельные токены
        raise credentials_exception
        
    # Находим пользователя в базе
    user = session.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
        
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Замок только для администраторов"""
    if current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges. Admin only."
        )
    return current_user