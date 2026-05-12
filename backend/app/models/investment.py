import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(
        SAEnum("fixed_income", "fund", "stock", "crypto", "forex", "other", name="investment_type_enum"),
        nullable=False,
        default="other",
    )
    currency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False
    )
    invested_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    current_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    expected_return_rate: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    currency: Mapped["Currency"] = relationship("Currency")  # noqa: F821

