from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator


class EntryBaseSchema(BaseModel):
    id: UUID
    user_id: UUID
    entry_date: datetime
    input_type: str
    status: str
    audio_url: str | None = None
    raw_text: str | None = None
    language_detected: str | None = None

    @model_validator(mode="before")
    def validate_entry_date(cls, values):
        audio = values.get("audio_url")
        raw_text = values.get("raw_text")
        if not audio and not raw_text:
            raise ValueError("Either audio_url or raw_text must be provided.")
        return values


class ExtractionsBaseSchema(BaseModel):
    id: UUID
    entry_id: UUID
    mood: str | None = None
    energy_level: str | None = None
    topics: str | None = None
    wins: str | None = None
    missed: str | None = None
    intentions: str | None = None
    recurring_themes: str | None = None
    model_version: str | None = None
    extracted_at: datetime


class FollowUpQuestionsBaseSchema(BaseModel):
    id: UUID
    entry_id: UUID
    question: str
    answer: str | None = None
    asked_at: datetime
    answered_at: datetime | None = None
