from datetime import datetime, timezone
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    declared_attr,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import DateTime, Boolean, and_, func, select


class Base(DeclarativeBase):
    __abstract__ = True

    # Generate __tablename__ automatically
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            deferred=True,
            deferred_raiseload=True,
            deferred_group="timestamps",
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            deferred=True,
            deferred_raiseload=True,
            deferred_group="timestamps",
        )

    @declared_attr
    def deleted_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            nullable=True,
            default=None,
            deferred=True,
            deferred_raiseload=True,
            deferred_group="timestamps",
        )

    @declared_attr
    def is_deleted(cls) -> Mapped[bool]:
        return mapped_column(
            Boolean,
            default=False,
            nullable=False,
            deferred=True,
            deferred_raiseload=True,
            deferred_group="status",
        )

    @declared_attr
    def is_active(cls) -> Mapped[bool]:
        return mapped_column(
            Boolean,
            default=True,
            nullable=False,
            deferred=True,
            deferred_raiseload=True,
            deferred_group="status",
        )

    async def create(self, db: AsyncSession):
        db.add(self)
        await db.commit()
        await db.refresh(self)
        return self

    async def update(self, db: AsyncSession):
        db.add(self)
        await db.commit()
        await db.refresh(self)
        return self

    async def soft_delete(self, db: AsyncSession):
        self.is_deleted = True
        self.deleted_at = datetime.now(tz=timezone.utc)
        self.is_active = False  # Optional: You can choose to deactivate it
        return await self.update(db)

    async def hard_delete(self, db: AsyncSession):
        await db.delete(self)
        await db.commit()

    @classmethod
    async def get_one(cls, db, id):
        result = await db.execute(
            select(cls).where(
                and_(cls.id == id, and_(cls.is_deleted.is_(False), cls.is_active))  # type: ignore
            )
        )
        return result.scalars().first()

    @classmethod
    async def get(cls, db, id=None, page=1, offset=20):
        page = max(page, 1)
        offset = max(offset, 1)
        filters = and_(cls.is_deleted.is_(False), cls.is_active)

        if id is None:
            skip = (page - 1) * offset
            total = await db.scalar(
                select(func.count()).select_from(cls).where(filters)
            )
            result = await db.execute(
                select(cls).where(filters).offset(skip).limit(offset)
            )
            return {
                "total": total or 0,
                "page": page,
                "size": offset,
                "results": result.scalars().all(),
            }

        result = await db.execute(
            select(cls).where(and_(cls.id == id, filters))  # type: ignore
        )
        return result.scalars().first()
