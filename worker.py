from arq import WorkerSettings
from arq.connections import RedisSettings
from config import settings


async def process_entry(ctx, entry_id: str):
    from core.db.session import AsyncSessionLocal
    from entries.model import Entry, Extractions
    from core.extraction.claude import ClaudeExtraction
    from sqlalchemy import select
    import json

    async with AsyncSessionLocal() as db:
        entry = (await db.execute(
            select(Entry).where(Entry.id == entry_id)
        )).scalar_one_or_none()
        
        if not entry:
            return {"status": "error", "message": "Entry not found"}
        
        extractor = ClaudeExtraction()
        extraction_result = extractor.extract(entry.raw_text)
        
        extraction = Extractions(
            entry_id=entry.id,
            **extraction_result
        )
        await extraction.create(db=db)
        
        entry.status = "processed"
        await entry.update(db=db)
        
        return {"status": "success", "extraction_id": str(extraction.id)}


async def generate_weekly_summary(ctx, user_id: str, week_start: str):
    from core.db.session import AsyncSessionLocal
    from users.model import WeeklySummary, User
    from entries.model import Entry, Extractions
    from sqlalchemy import select, and_
    from datetime import datetime, timedelta
    import json

    async with AsyncSessionLocal() as db:
        week_start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
        week_end_date = week_start_date + timedelta(days=6)
        
        entries = (await db.execute(
            select(Entry, Extractions).join(Extractions)
            .where(and_(
                Entry.user_id == user_id,
                Entry.entry_date >= week_start_date,
                Entry.entry_date <= week_end_date,
                Entry.is_deleted == False,
                Extractions.is_deleted == False
            ))
        )).all()
        
        if not entries:
            return {"status": "no_entries"}
        
        extractions_text = "\n\n".join([
            f"Date: {e.Entry.entry_date}\n"
            f"Mood: {e.Extractions.mood}\n"
            f"Topics: {e.Extractions.topics}\n"
            f"Wins: {e.Extractions.wins}\n"
            f"Missed: {e.Extractions.missed}\n"
            f"Intentions: {e.Extractions.intentions}"
            for e in entries
        ])
        
        from core.extraction.claude import EXTRACTION_SYSTEM_PROMPT
        from anthropic import Anthropic
        from config import settings
        
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system="You are a weekly journal summarizer. Create a concise summary of the week's entries, identify key themes, and describe the overall mood arc and energy arc.",
            temperature=0.3,
            messages=[
                {"role": "user", "content": f"Here are the weekly extractions:\n\n{extractions_text}\n\nCreate a weekly summary with:\n1. summary: 2-3 paragraph narrative summary\n2. themes: comma-separated key themes\n3. mood_arc: description of mood trajectory\n4. energy_arc: description of energy trajectory"}
            ],
        )
        
        block = response.content[0]
        if block.type != "text":
            return {"status": "error", "message": "Unexpected response format"}
        
        import json
        text = block.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        summary_data = json.loads(text)
        
        weekly_summary = WeeklySummary(
            user_id=user_id,
            week_start=week_start_date,
            week_end=week_end_date,
            summary=summary_data.get("summary"),
            themes=summary_data.get("themes"),
            mood_arch=summary_data.get("mood_arc"),
            energy_arch=summary_data.get("energy_arc"),
            generated_at=datetime.utcnow(),
        )
        await weekly_summary.create(db=db)
        
        return {"status": "success", "summary_id": str(weekly_summary.id)}


async def generate_monthly_summary(ctx, user_id: str, month_start: str):
    from core.db.session import AsyncSessionLocal
    from users.model import MonthlySummary
    from sqlalchemy import select, and_
    from datetime import datetime, timedelta
    import calendar

    async with AsyncSessionLocal() as db:
        month_start_date = datetime.strptime(month_start, "%Y-%m-%d").date()
        _, last_day = calendar.monthrange(month_start_date.year, month_start_date.month)
        month_end_date = month_start_date.replace(day=last_day)
        
        weekly_summaries = (await db.execute(
            select(WeeklySummary).where(and_(
                WeeklySummary.user_id == user_id,
                WeeklySummary.week_start >= month_start_date,
                WeeklySummary.week_end <= month_end_date,
                WeeklySummary.is_deleted == False
            ))
        )).scalars().all()
        
        if not weekly_summaries:
            return {"status": "no_weekly_summaries"}
        
        summaries_text = "\n\n".join([
            f"Week {ws.week_start} to {ws.week_end}:\n{ws.summary}\nThemes: {ws.themes}\nMood: {ws.mood_arch}\nEnergy: {ws.energy_arch}"
            for ws in weekly_summaries
        ])
        
        from anthropic import Anthropic
        from config import settings
        
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            system="You are a monthly journal summarizer. Create a comprehensive summary from weekly summaries, identify overarching themes, and describe the monthly mood and energy arcs.",
            temperature=0.3,
            messages=[
                {"role": "user", "content": f"Here are the weekly summaries:\n\n{summaries_text}\n\nCreate a monthly summary with:\n1. summary: 3-4 paragraph narrative\n2. themes: comma-separated key themes\n3. mood_arc: description of mood trajectory\n4. energy_arc: description of energy trajectory"}
            ],
        )
        
        block = response.content[0]
        if block.type != "text":
            return {"status": "error", "message": "Unexpected response format"}
        
        import json
        text = block.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        summary_data = json.loads(text)
        
        monthly_summary = MonthlySummary(
            user_id=user_id,
            month_start=month_start_date,
            month_end=month_end_date,
            summary=summary_data.get("summary"),
            themes=summary_data.get("themes"),
            mood_arch=summary_data.get("mood_arc"),
            energy_arch=summary_data.get("energy_arc"),
            generated_at=datetime.utcnow(),
        )
        await monthly_summary.create(db=db)
        
        return {"status": "success", "summary_id": str(monthly_summary.id)}


async def transcribe_audio(ctx, entry_id: str, audio_url: str):
    from core.db.session import AsyncSessionLocal
    from entries.model import Entry
    from sqlalchemy import select
    from core.minio import get_minio_object
    from faster_whisper import WhisperModel
    import io
    import os

    async with AsyncSessionLocal() as db:
        entry = (await db.execute(
            select(Entry).where(Entry.id == entry_id)
        )).scalar_one_or_none()
        
        if not entry:
            return {"status": "error", "message": "Entry not found"}
        
        minio_client = await get_minio_object(audio_url)
        audio_data = await minio_client.read()
        
        model_size = os.getenv("WHISPER_MODEL", "base")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        segments, info = model.transcribe(io.BytesIO(audio_data), beam_size=5)
        transcript = " ".join([segment.text for segment in segments])
        
        entry.raw_text = transcript
        entry.language_detected = info.language
        entry.status = "transcribed"
        await entry.update(db=db)
        
        return {"status": "success", "transcript": transcript, "language": info.language}


async def generate_follow_ups(ctx, entry_id: str):
    from core.db.session import AsyncSessionLocal
    from entries.model import Entry, Extractions, FollowUpQuestions
    from sqlalchemy import select
    from anthropic import Anthropic
    from config import settings
    import json

    async with AsyncSessionLocal() as db:
        entry = (await db.execute(
            select(Entry).where(Entry.id == entry_id)
        )).scalar_one_or_none()
        
        if not entry:
            return {"status": "error", "message": "Entry not found"}
        
        extraction = (await db.execute(
            select(Extractions).where(Extractions.entry_id == entry_id)
        )).scalar_one_or_none()
        
        if not extraction:
            return {"status": "error", "message": "Entry not yet processed"}
        
        context = f"""
Entry date: {entry.entry_date}
Raw text: {entry.raw_text}
Mood: {extraction.mood}
Energy: {extraction.energy_level}
Topics: {extraction.topics}
Wins: {extraction.wins}
Missed: {extraction.missed}
Intentions: {extraction.intentions}
Recurring themes: {extraction.recurring_themes}
"""
        
        system_prompt = """You are a thoughtful journaling companion. Based on the user's journal entry and its structured extraction, generate 2-3 targeted follow-up questions that:
1. Probe deeper into what they shared
2. Help them reflect on patterns or feelings
3. Are specific to their content, not generic
4. Match the language/register they used (English, Nepali, Romanized Nepali, or mixed)

Return ONLY valid JSON:
{
  "questions": ["question 1", "question 2", "question 3"]
}"""
        
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            system=system_prompt,
            temperature=0.7,
            messages=[
                {"role": "user", "content": f"Here is the entry and its extraction:\n{context}\n\nGenerate 2-3 follow-up questions."}
            ],
        )
        
        block = response.content[0]
        if block.type != "text":
            return {"status": "error", "message": "Unexpected response format"}
        
        text = block.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(text)
        
        questions = result.get("questions", [])
        for q in questions:
            fuq = FollowUpQuestions(
                entry_id=entry.id,
                question=q,
                asked_at=datetime.utcnow(),
            )
            await fuq.create(db=db)
        
        return {"status": "success", "questions_count": len(questions)}


from datetime import datetime


class WorkerSettings:
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )
    functions = [
        process_entry,
        generate_weekly_summary,
        generate_monthly_summary,
        transcribe_audio,
        generate_follow_ups,
    ]
    cron_jobs = [
        {
            "func": "generate_weekly_summary",
            "cron": "0 6 * * 0",  # Every Sunday at 6 AM
            "kwargs": {"user_id": None, "week_start": None},
        },
        {
            "func": "generate_monthly_summary",
            "cron": "0 6 1 * *",  # 1st of each month at 6 AM
            "kwargs": {"user_id": None, "month_start": None},
        },
    ]