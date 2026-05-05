from fastapi import FastAPI
from typing import List
from typing_extensions import TypedDict
from models import User, Location

app = FastAPI(title="BookCrossing API (Practice 1.1)")

temp_db = [
    {
        "id": 1,
        "username": "user1",
        "email": "user1@example.com",
        "hashed_password": "hashed1",
        "first_name": "Dim",
        "last_name": "Dimych",
        "bio": "A reader",
        "avatar_url": None,
        "role": "user",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "is_active": True,
        "location": {
            "id": 1,
            "country": "Russia",
            "city": "Moscow",
            "address": "Red Square"
        },
        "genres": [
            {
                "id": 1,
                "name": "Fiction",
                "description": "Fictional stories"
            },
            {
                "id": 2,
                "name": "Science",
                "description": "Scientific books"
            }
        ],
        "books": [
            {
                "id": 1,
                "bcid": "RU-12345",
                "title": "1984",
                "author": "George Orwell",
                "publication_year": 1949,
                "isbn": "978-0451524935",
                "condition": "Good",
                "language": "English",
                "is_available": True,
                "owner_id": 1,
                "created_at": "2026-01-05T00:00:00",
                "updated_at": "2026-01-05T00:00:00",
                "is_deleted": False
            }
        ]
    },
    {
        "id": 2,
        "username": "user2",
        "email": "user2@example.com",
        "hashed_password": "hashed2",
        "first_name": "Maya",
        "last_name": "Mayaeva",
        "bio": "Book lover",
        "avatar_url": None,
        "role": "user",
        "created_at": "2026-01-02T00:00:00",
        "updated_at": "2026-01-02T00:00:00",
        "is_active": True,
        "location": {
            "id": 1,
            "country": "Russia",
            "city": "Moscow",
            "address": "Red Square"
        },
        "genres": [
            {
                "id": 1,
                "name": "Fiction",
                "description": "Fictional stories"
            },
            {
                "id": 3,
                "name": "History",
                "description": "Historical books"
            }
        ],
        "books": []
    }
]

temp_locations = [
    {
        "id": 1,
        "country": "Russia",
        "city": "Moscow",
        "address": "Red Square"
    }
]

# --- CRUD Эндпоинты для User ---

@app.get("/users")
def users_list() -> List[User]:
    return temp_db

@app.get("/user/{user_id}")
def user_get(user_id: int) -> List[User]:
    return [u for u in temp_db if u.get("id") == user_id]

@app.post("/user")
def user_create(user: User) -> TypedDict('Response', {"status": int, "data": User}):
    temp_db.append(user.model_dump())
    return {"status": 200, "data": user}

@app.delete("/user/delete/{user_id}")
def user_delete(user_id: int) -> TypedDict('Response', {"status": int, "message": str}):
    for i, u in enumerate(temp_db):
        if u.get("id") == user_id:
            temp_db.pop(i)
            break
    return {"status": 201, "message": "deleted"}

@app.put("/user/{user_id}")
def user_update(user_id: int, user: User) -> List[User]:
    for i, u in enumerate(temp_db):
        if u.get("id") == user_id:
            temp_db[i] = user.model_dump()
    return temp_db

# --- CRUD Эндпоинты для Location ---

@app.get("/locations")
def locations_list() -> List[Location]:
    return temp_locations

@app.get("/location/{loc_id}")
def location_get(loc_id: int) -> List[Location]:
    return [l for l in temp_locations if l.get("id") == loc_id]

@app.post("/location")
def location_create(location: Location) -> TypedDict('Response', {"status": int, "data": Location}):
    temp_locations.append(location.model_dump())
    return {"status": 200, "data": location}

@app.delete("/location/delete/{loc_id}")
def location_delete(loc_id: int) -> TypedDict('Response', {"status": int, "message": str}):
    for i, l in enumerate(temp_locations):
        if l.get("id") == loc_id:
            temp_locations.pop(i)
            break
    return {"status": 201, "message": "deleted"}

@app.put("/location/{loc_id}")
def location_update(loc_id: int, location: Location) -> List[Location]:
    for i, l in enumerate(temp_locations):
        if l.get("id") == loc_id:
            temp_locations[i] = location.model_dump()
    return temp_locations