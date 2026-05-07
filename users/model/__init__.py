from sqlalchemy import DateTime
from datetime import datetime
from sqlalchemy import Date
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from core.auth.pw_lib import hash_password
from core.db import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_extension import uuid7
from uuid import UUID
from sqlalchemy import Column, ForeignKey, String, Table, select


class User(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)
    role: Mapped["Role"] = relationship("Role", lazy="joined")
    role_id: Mapped[UUID] = mapped_column(ForeignKey("role.id"), nullable=True)

    async def create(self, db: AsyncSession):
        self.hashed_password = hash_password(self.hashed_password)
        self.role_id = await Role.get_default_role(db)
        return await super().create(db)


class WeeklySummary(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=True)
    themes: Mapped[str] = mapped_column(String, nullable=True)
    mood_arch: Mapped[str] = mapped_column(String, nullable=True)
    energy_arch: Mapped[str] = mapped_column(String, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class MonthlySummary(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    month_start: Mapped[date] = mapped_column(Date, nullable=False)
    month_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=True)
    themes: Mapped[str] = mapped_column(String, nullable=True)
    mood_arch: Mapped[str] = mapped_column(String, nullable=True)
    energy_arch: Mapped[str] = mapped_column(String, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", ForeignKey("role.id"), primary_key=True),
    Column("permission_id", ForeignKey("permission.id"), primary_key=True),
)


class Role(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(String(500))
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permission, back_populates="roles"
    )

    @classmethod
    async def get_default_role(cls, db: AsyncSession) -> UUID:
        """Fetch the default 'user' role ID."""
        default_role_id = (
            await db.execute(select(cls.id).where(cls.name == "user"))
        ).scalar_one_or_none()

        if not default_role_id:
            raise ValueError("Default role 'user' not found. Please seed the database.")

        return default_role_id


class Permission(Base):
    id: Mapped[UUID] = mapped_column(default=uuid7, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(String(500))
    roles: Mapped[list["Role"]] = relationship(
        secondary=role_permission, back_populates="permissions"
    )
