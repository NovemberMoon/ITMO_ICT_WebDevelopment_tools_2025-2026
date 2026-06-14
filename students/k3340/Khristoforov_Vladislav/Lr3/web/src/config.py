import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # База данных
    DATABASE_URL: str = os.getenv("DB_URL", "sqlite:///./bookcrossing.db")
    
    # Безопасность и JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-bookcrossing-lab1")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Создаем глобальный объект настроек
settings = Settings()