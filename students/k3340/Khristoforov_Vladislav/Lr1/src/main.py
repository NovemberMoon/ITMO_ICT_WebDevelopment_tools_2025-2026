from fastapi import FastAPI
from contextlib import asynccontextmanager

from database import init_db
from routers import users, books, exchanges

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="BookCrossing API (Practice 1.2)", 
    lifespan=lifespan
)

app.include_router(users.users_router)
app.include_router(users.locations_router)
app.include_router(books.books_router)
app.include_router(books.genres_router)
app.include_router(exchanges.exchanges_router)
app.include_router(exchanges.reviews_router)

@app.get("/")
def root():
    return {"message": "Welcome to BookCrossing API. Go to /docs for Swagger UI."}