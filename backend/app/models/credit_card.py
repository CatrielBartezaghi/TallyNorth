import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class CreditCard(Base):
    __tablename__ = "credit_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    closing_day: Mapped[int] = mapped_column(Integer, nullable=False)
    due_day: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False
    )
    payment_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True
    )
    credit_limit: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    currency: Mapped["Currency"] = relationship("Currency")  # noqa: F821
    purchases: Mapped[list["CreditCardPurchase"]] = relationship(  # noqa: F821
        back_populates="credit_card", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CreditCard id={self.id} name={self.name!r}>"
