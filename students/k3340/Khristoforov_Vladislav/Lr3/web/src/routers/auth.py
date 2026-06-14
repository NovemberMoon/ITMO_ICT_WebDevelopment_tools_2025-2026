from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import jwt

from database import get_session
from models.users import Role, User, UserCreate, UserPublic
from security import verify_password, get_password_hash, create_access_token
from config import settings

auth_router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@auth_router.post("/register", response_model=UserPublic)
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)) -> UserPublic:
    # Асинхронно проверяем, не занят ли логин
    existing_user = (await session.exec(select(User).where(User.username == user.username))).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    existing_email = (await session.exec(select(User).where(User.email == user.email))).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Хешируем пароль перед сохранением в БД
    hashed_pwd = get_password_hash(user.password)
    db_user = User.model_validate(user, update={"hashed_password": hashed_pwd})
    
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

@auth_router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)) -> dict:
    user = (await session.exec(select(User).where(User.username == form_data.username))).first()
    
    # Сверяем введенный пароль с захешированным из базы
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Формируем Payload (полезную нагрузку) JWT и шифруем его
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

# --- МЕХАНИЗМЫ ЗАЩИТЫ РОУТЕРОВ ---

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)) -> User:
    """
    Зависимость (Dependency). Извлекает токен из заголовка запроса,
    расшифровывает его и находит пользователя. Используется для закрытых эндпоинтов.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
        
    user = await session.get(User, int(user_id))
    # Проверка на мягкое удаление / бан
    if user is None or not user.is_active:
        raise credentials_exception
        
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Замок ролевого доступа. Пропускает только администраторов."""
    if current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges. Admin only."
        )
    return current_user