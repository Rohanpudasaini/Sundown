from sqlalchemy import Date
from datetime import date
from sqlalchemy import DateTime
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from core.auth.pw_lib import hash_password
from core.db import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_extension import uuid7
from uuid import UUID
from sqlalchemy import Column, ForeignKey, String, Table, select


class Entry(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    input_type: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    audio_url: Mapped[str] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(String(255), nullable=True)
    language_detected: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


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
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class FollowUpQuestions(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    entry_id: Mapped[UUID] = mapped_column(ForeignKey("entry.id"), nullable=False)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    answer: Mapped[str] = mapped_column(String(255), nullable=True)
    asked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
