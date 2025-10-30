"""UserSettings model for poll configuration."""
from datetime import time

from sqlalchemy import Boolean, ForeignKey, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.models.base import Base


class UserSettings(Base):
    """User settings model for automatic poll configuration."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Poll intervals (in minutes)
    poll_interval_weekday: Mapped[int] = mapped_column(
        Integer, nullable=False, default=120  # 2 hours
    )
    poll_interval_weekend: Mapped[int] = mapped_column(
        Integer, nullable=False, default=180  # 3 hours
    )

    # Quiet hours (when bot should not poll)
    quiet_hours_start: Mapped[time | None] = mapped_column(
        Time, nullable=True, default=time(23, 0)  # 23:00
    )
    quiet_hours_end: Mapped[time | None] = mapped_column(
        Time, nullable=True, default=time(7, 0)  # 07:00
    )

    # Reminder settings
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    reminder_delay_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return (
            f"<UserSettings(id={self.id}, user_id={self.user_id}, "
            f"weekday={self.poll_interval_weekday}m, weekend={self.poll_interval_weekend}m)>"
        )
