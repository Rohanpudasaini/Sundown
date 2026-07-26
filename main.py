from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from users.router import app as user_router
from entries.router import app as entry_router

app = FastAPI(title="Sundown", version="0.0.1")

app.include_router(user_router)
app.include_router(entry_router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("templates/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
