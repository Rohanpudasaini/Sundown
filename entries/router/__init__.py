from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks
from entries.model import Entry, Extractions, FollowUpQuestions
from fastapi import Depends
from core.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from entries.schema import (
    EntryBaseSchema,
    ExtractionPaginatedSchema,
    ExtractionsBaseSchema,
    FollowUpQuestionsBaseSchema,
)
from users.router import get_current_user

app = APIRouter(prefix="/entries", tags=["entries"])


@app.get("/", response_model=list[EntryBaseSchema])
async def read_entries(
    db: AsyncSession = Depends(get_db),
):
    return await Entry.get(db)


@app.get(
    "/extractions",
    response_model=ExtractionPaginatedSchema,
)
async def read_extractions(
    user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    offset: int = 20,
):
    return await Extractions.get(db, page=page, offset=offset, user_id=user_id)


@app.get("/{id}", response_model=EntryBaseSchema)
async def read_entry(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    return await Entry.get_one(db, id=id)


@app.get("/extractions/{id}", response_model=ExtractionsBaseSchema)
async def read_extraction(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    return await Extractions.get_one(db, id=id)


@app.get("/follow_up_questions", response_model=list[FollowUpQuestionsBaseSchema])
async def read_follow_up_questions(
    db: AsyncSession = Depends(get_db),
):
    return await FollowUpQuestions.get(db)


@app.get("/follow_up_questions/{id}", response_model=FollowUpQuestionsBaseSchema)
async def read_follow_up_question(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    return await FollowUpQuestions.get_one(db, id=id)


@app.post(
    "/create_entry",
)
async def create_entry(
    data: EntryBaseSchema,
    bg_tasks: BackgroundTasks,
    user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    entry = await Entry(
        **data.model_dump(exclude_none=True, exclude_unset=True), user_id=user_id
    ).create(db=db)
    data.user_id = user_id
    bg_tasks.add_task(entry.process_entry, data.model_dump(), db)
    return {"message": "Entry received and is being processed."}


@app.post("/create_follow_up_question")
async def create_follow_up_question(
    data: FollowUpQuestionsBaseSchema,
    db: AsyncSession = Depends(get_db),
):
    return await FollowUpQuestions(**data.model_dump()).create(db=db)
