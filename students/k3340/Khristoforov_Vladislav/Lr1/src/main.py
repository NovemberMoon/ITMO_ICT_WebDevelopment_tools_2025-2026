from fastapi import FastAPI
from routers import users, books, exchanges

app = FastAPI(title="BookCrossing API (Practice 1.3)")

app.include_router(users.users_router)
app.include_router(users.locations_router)
app.include_router(books.books_router)
app.include_router(books.genres_router)
app.include_router(exchanges.exchanges_router)
app.include_router(exchanges.reviews_router)

@app.get("/")
def root():
    return {"message": "Welcome to BookCrossing API. Go to /docs for Swagger UI."}