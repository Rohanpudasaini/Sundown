from fastapi import FastAPI
from users.router import app as user_router
from entries.router import app as entry_router

app = FastAPI(title="Sundown", version="0.0.1")

app.include_router(user_router)
app.include_router(entry_router)


@app.get("/")
async def root():
    return {"message": "Sundown is running!"}
