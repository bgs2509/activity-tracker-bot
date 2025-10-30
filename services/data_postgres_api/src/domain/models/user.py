"""User model."""
from datetime import datetime
from typing import List

from sqlalchemy import BigInteger, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.domain.models.base import Base


class User(Base):
    """User model for Telegram bot users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Europe/Moscow"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    categories: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    activities: Mapped[List["Activity"]] = relationship(
        "Activity",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    settings: Mapped["UserSettings"] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
