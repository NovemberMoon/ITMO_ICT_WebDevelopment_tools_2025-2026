import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

load_dotenv()

DB_URL=os.getenv("DB_URL")
if not DB_URL:
    raise ValueError("Не найдена переменная DB_URL в файле .env")

engine = create_engine(DB_URL, echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session