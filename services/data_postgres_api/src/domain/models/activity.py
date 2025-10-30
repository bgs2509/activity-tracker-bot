"""Activity model."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.domain.models.base import Base

if TYPE_CHECKING:
    from src.domain.models.user import User
    from src.domain.models.category import Category


class Activity(Base):
    """Activity model for user activities."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Check constraint: end_time must be greater than start_time
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_end_time_after_start"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="activities")
    category: Mapped["Category | None"] = relationship("Category", back_populates="activities")

    def __repr__(self) -> str:
        return (
            f"<Activity(id={self.id}, user_id={self.user_id}, "
            f"description={self.description[:30]}...)>"
        )
