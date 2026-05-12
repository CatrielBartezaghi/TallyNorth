import uuid
from datetime import datetime, date

from sqlalchemy import Integer, Numeric, DateTime, Date, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Installment(Base):
    __tablename__ = "installments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("credit_card_purchases.id", ondelete="CASCADE"),
        nullable=False,
    )
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # The billing period due date for this installment (card due_day of that month)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paid_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    purchase: Mapped["CreditCardPurchase"] = relationship(  # noqa: F821
        "CreditCardPurchase", back_populates="installment_rows"
    )
    paid_account: Mapped["Account | None"] = relationship("Account")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Installment #{self.installment_number} due={self.due_date} paid={self.is_paid}>"
