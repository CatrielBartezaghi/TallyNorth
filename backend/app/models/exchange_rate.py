import uuid
from datetime import datetime, date

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("from_currency_id", "to_currency_id", "date", name="uq_exchange_rate_pair_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    from_currency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False
    )
    to_currency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False
    )
    rate: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    from_currency: Mapped["Currency"] = relationship("Currency", foreign_keys=[from_currency_id])  # noqa: F821
    to_currency: Mapped["Currency"] = relationship("Currency", foreign_keys=[to_currency_id])  # noqa: F821
