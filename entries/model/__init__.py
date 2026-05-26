from sqlalchemy import Date
from sqlalchemy import DateTime
from datetime import date, datetime, timezone

# from sqlalchemy.ext.asyncio import AsyncSession
from core.db import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from uuid_extension import uuid7
from uuid import UUID
from sqlalchemy import ForeignKey, String


from core.extraction.claude import ClaudeExtraction


class Entry(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    input_type: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    audio_url: Mapped[str] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(String(255), nullable=True)
    language_detected: Mapped[str] = mapped_column(String(255), nullable=True)

    async def process_entry(self, entry_data: dict, db: AsyncSession):
        # Placeholder for the actual processing logic, e.g., calling the extraction system
        extractor = ClaudeExtraction()
        print(f"Processing entry: {entry_data}")
        extraction_result = extractor.extract(entry_data["raw_text"])
        print(f"Extraction result: {extraction_result}")
        # response = {
        #     "mood": "content",
        #     "energy_level": "medium",
        #     "topics": "work, social media usage, exercise, side project, coding streak",
        #     "wins": "completed work tasks, did some exercise, made GitHub commit, maintained 155-day streak",
        #     "missed": "scrolled too many reels",
        #     "intentions": None,
        #     "recurring_themes": None,
        # }
        await Extractions(entry_id=self.id, **extraction_result).create(db=db)


class Extractions(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    entry_id: Mapped[UUID] = mapped_column(ForeignKey("entry.id"), nullable=False)
    mood: Mapped[str] = mapped_column(String(255), nullable=True)
    energy_level: Mapped[str] = mapped_column(String(255), nullable=True)
    topics: Mapped[str] = mapped_column(String(255), nullable=True)
    wins: Mapped[str] = mapped_column(String(255), nullable=True)
    missed: Mapped[str] = mapped_column(String(255), nullable=True)
    intentions: Mapped[str] = mapped_column(String(255), nullable=True)
    recurring_themes: Mapped[str] = mapped_column(String(255), nullable=True)
    model_version: Mapped[str] = mapped_column(String(255), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(timezone.utc)
    )


class FollowUpQuestions(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    entry_id: Mapped[UUID] = mapped_column(ForeignKey("entry.id"), nullable=False)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    answer: Mapped[str] = mapped_column(String(255), nullable=True)
    asked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
