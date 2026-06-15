from fastapi import FastAPI
from routers import users, books, exchanges, parser
from routers.auth import auth_router

app = FastAPI(title="BookCrossing API")

app.include_router(auth_router)
app.include_router(users.users_router)
app.include_router(users.locations_router)
app.include_router(books.books_router)
app.include_router(books.genres_router)
app.include_router(exchanges.exchanges_router)
app.include_router(exchanges.reviews_router)
app.include_router(parser.router)

@app.get("/")
def root():
    return {"message": "Welcome to BookCrossing API. Go to /docs for Swagger UI."}