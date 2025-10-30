"""Category model."""
from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.domain.models.base import Base

if TYPE_CHECKING:
    from src.domain.models.user import User
    from src.domain.models.activity import Activity


class Category(Base):
    """Category model for activity categories."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Unique constraint: user cannot have two categories with same name
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uix_user_category_name"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="categories")
    activities: Mapped[List["Activity"]] = relationship(
        "Activity",
        back_populates="category",
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, emoji={self.emoji})>"
