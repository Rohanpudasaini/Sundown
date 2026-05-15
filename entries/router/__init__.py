from fastapi import APIRouter
from entries.model import Entry, Extractions, FollowUpQuestions
from fastapi import Depends
from core.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession


app = APIRouter(prefix="/entries", tags=["entries"])


@app.get("/")
async def read_entries(
    db: AsyncSession = Depends(get_db),
):
    return Entry.get(db)


@app.get("/{id}")
async def read_entry(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    return Entry.get(db, id=id)


@app.get("/extractions")
async def read_extractions(
    db: AsyncSession = Depends(get_db),
):
    return Extractions.get(db)


@app.get("/extractions/{id}")
async def read_extraction(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    return Extractions.get(db, id=id)


@app.get("/follow_up_questions")
async def read_follow_up_questions(
    db: AsyncSession = Depends(get_db),
):
    return FollowUpQuestions.get(db)


@app.get("/follow_up_questions/{id}")
async def read_follow_up_question(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    return FollowUpQuestions.get(db, id=id)


@app.post("/create_entry")
async def create_entry(
    data,  # TODO: Add proper schema with field validation
    db: AsyncSession = Depends(get_db),
):
    return await Entry(**data.model_dump()).create(db=db)
