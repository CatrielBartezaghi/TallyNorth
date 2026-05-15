import uuid
from datetime import datetime, date

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SavingGoal(Base):
    __tablename__ = "saving_goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    currency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False
    )
    target_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    current_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#22c55e")
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    currency: Mapped["Currency"] = relationship("Currency")  # noqa: F821

