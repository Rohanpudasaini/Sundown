from typing import Annotated
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from entries.model import Entry, Extractions, FollowUpQuestions
from core.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from entries.schema import (
    EntryBaseSchema,
    ExtractionsBaseSchema,
    FollowUpQuestionsBaseSchema,
)
from users.router import get_current_user
from arq import create_pool
from arq.connections import RedisSettings
from config import settings
from anthropic import Anthropic
import json
from core.minio import put_minio_object
import io
import uuid as uuid_lib

app = APIRouter(prefix="/entries", tags=["entries"])


async def get_redis_pool():
    return await create_pool(RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT))


@app.get(
    "/",
)
async def read_entries(
    db: AsyncSession = Depends(get_db),
):
    return await Entry.get(db)


@app.get("/{id}", response_model=EntryBaseSchema)
async def read_entry(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    return await Entry.get(db, id=id)


@app.get(
    "/extractions"
)
async def read_extractions(
    db: AsyncSession = Depends(get_db),
):
    return await Extractions.get(db)


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
    user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    entry = await Entry(**data.model_dump(exclude={"user_id"}), user_id=user_id).create(db=db)
    
    # Enqueue background job for processing
    redis = await get_redis_pool()
    await redis.enqueue_job("process_entry", str(entry.id))
    
    return {"message": "Entry received and is being processed.", "entry_id": str(entry.id)}


@app.post("/upload_audio")
async def upload_audio(
    file: UploadFile = File(...),
    user_id: Annotated[UUID, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """Upload audio file and create an entry with it."""
    # Read file content
    content = await file.read()
    
    # Generate unique object name
    object_name = f"audio/{user_id}/{uuid_lib.uuid7()}.webm"
    
    # Upload to MinIO
    bucket_name = "sundown-audio"
    audio_data = io.BytesIO(content)
    await put_minio_object(bucket_name, object_name, audio_data)
    
    # Create entry with audio URL
    today = datetime.utcnow().date().isoformat()
    audio_url = f"s3://{bucket_name}/{object_name}"
    
    entry = await Entry(
        entry_date=today,
        input_type="voice",
        status="transcribing",
        audio_url=audio_url,
        user_id=user_id
    ).create(db=db)
    
    # Enqueue transcription job
    redis = await get_redis_pool()
    await redis.enqueue_job("transcribe_audio", str(entry.id), audio_url)
    
    return {"message": "Audio uploaded, transcription started", "entry_id": str(entry.id)}


@app.post("/{entry_id}/follow_up")
async def create_follow_up(
    entry_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Generate follow-up questions for an entry using background job."""
    entry = await Entry.get_one(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    if entry.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get the extraction if available
    extraction_result = await db.execute(
        select(Extractions).where(Extractions.entry_id == entry_id)
    )
    extraction = extraction_result.scalar_one_or_none()
    
    if not extraction:
        raise HTTPException(status_code=400, detail="Entry not yet processed")
    
    # Enqueue job for generating follow-up questions
    redis = await get_redis_pool()
    await redis.enqueue_job("generate_follow_ups", str(entry_id))
    
    return {"message": "Follow-up questions generation started", "entry_id": str(entry_id)}


@app.get("/{entry_id}/follow_up/questions")
async def get_follow_up_questions(
    entry_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    entry = await Entry.get_one(db, entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    questions = await FollowUpQuestions.get(db, entry_id=str(entry_id))
    return questions


@app.patch("/follow_up_questions/{question_id}")
async def update_follow_up_answer(
    question_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    answer: str = None,
):
    """Update answer to a follow-up question."""
    question = await FollowUpQuestions.get_one(db, str(question_id))
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Verify ownership via entry
    entry = await Entry.get_one(db, question.entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    question.answer = answer
    question.answered_at = datetime.utcnow()
    await question.update(db=db)
    
    return {"message": "Answer saved", "question_id": str(question.id)}


@app.post("/{entry_id}/follow_up/stream")
async def stream_follow_up_questions(
    entry_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Stream follow-up questions from Claude Haiku for low-latency UX."""
    entry = await Entry.get_one(db, entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    extraction_result = await db.execute(
        select(Extractions).where(Extractions.entry_id == entry_id)
    )
    extraction = extraction_result.scalar_one_or_none()
    
    if not extraction:
        raise HTTPException(status_code=400, detail="Entry not yet processed")
    
    # Build context for follow-up questions
    context = f"""
    Entry: {entry.raw_text}
    Mood: {extraction.mood}
    Energy: {extraction.energy_level}
    Topics: {extraction.topics}
    Wins: {extraction.wins}
    Missed: {extraction.missed}
    Intentions: {extraction.intentions}
    Recurring themes: {extraction.recurring_themes}
    """
    
    async def generate():
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        system_prompt = """You are a thoughtful journaling companion. Based on the user's journal entry and its extracted insights, generate 3-5 follow-up questions that would help them reflect deeper. 

        Rules:
        - Questions should be open-ended and specific to their entry
        - Match the user's language/register (English, Nepali, Romanized Nepali, or mixed)
        - Avoid generic prompts like "How was your day?"
        - Return ONE question at a time as JSON: {"question": "...", "question_number": 1, "total": 3}
        - Stream each question separately with a small delay"""
        
        with client.messages.stream(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": context}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {text}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/search")
async def search_entries(
    query: str,
    user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    source: str = "entries",  # entries, extractions, weekly, monthly
):
    """Semantic search across journal entries using pgvector."""
    from pgvector.sqlalchemy import Vector
    from sqlalchemy import select, and_
    
    # TODO: Generate embedding for query using an embedding model
    # For now, we'll use a placeholder - in production, call an embedding model
    # e.g., using sentence-transformers or OpenAI embeddings
    query_embedding = [0.0] * 1536  # Placeholder
    
    if source == "entries":
        results = await db.execute(
            select(Entry)
            .where(and_(
                Entry.user_id == user_id,
                Entry.is_deleted == False,
                Entry.embedding.is_not(None)
            ))
            .order_by(Entry.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        entries = results.scalars().all()
        return [{"id": str(e.id), "date": e.entry_date, "text": e.raw_text, "score": 0.0} for e in entries]
    
    elif source == "extractions":
        results = await db.execute(
            select(Extractions)
            .join(Entry)
            .where(and_(
                Entry.user_id == user_id,
                Entry.is_deleted == False,
                Extractions.is_deleted == False,
                Extractions.embedding.is_not(None)
            ))
            .order_by(Extractions.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        extractions = results.scalars().all()
        return [{"id": str(e.id), "entry_id": str(e.entry_id), "mood": e.mood, "topics": e.topics, "score": 0.0} for e in extractions]
    
    elif source == "weekly":
        from users.model import WeeklySummary
        results = await db.execute(
            select(WeeklySummary)
            .where(and_(
                WeeklySummary.user_id == user_id,
                WeeklySummary.is_deleted == False,
                WeeklySummary.embedding.is_not(None)
            ))
            .order_by(WeeklySummary.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        summaries = results.scalars().all()
        return [{"id": str(s.id), "week": f"{s.week_start} to {s.week_end}", "summary": s.summary, "score": 0.0} for s in summaries]
    
    elif source == "monthly":
        from users.model import MonthlySummary
        results = await db.execute(
            select(MonthlySummary)
            .where(and_(
                MonthlySummary.user_id == user_id,
                MonthlySummary.is_deleted == False,
                MonthlySummary.embedding.is_not(None)
            ))
            .order_by(MonthlySummary.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        summaries = results.scalars().all()
        return [{"id": str(s.id), "month": f"{s.month_start} to {s.month_end}", "summary": s.summary, "score": 0.0} for s in summaries]
    
    else:
        raise HTTPException(status_code=400, detail="Invalid source. Use: entries, extractions, weekly, monthly")


### TODO - Consult whether we need endpoint for this or not
# The extractions and followup should be handled by the backend itself and not exposed as an endpoint.
@app.post("/create_extractions")
async def create_extractions(
    data: ExtractionsBaseSchema,  # TODO: Add proper schema with field validation
    db: AsyncSession = Depends(get_db),
):
    return await Extractions(**data.model_dump()).create(db=db)


@app.post("/create_follow_up_question")
async def create_follow_up_question(
    data: FollowUpQuestionsBaseSchema,  # TODO: Add proper schema with field validation
    db: AsyncSession = Depends(get_db),
):
    return await FollowUpQuestions(**data.model_dump()).create(db=db)
