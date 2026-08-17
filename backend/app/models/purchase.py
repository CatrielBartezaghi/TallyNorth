import uuid
from datetime import datetime, date

from sqlalchemy import String, Integer, Numeric, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class CreditCardPurchase(Base):
    __tablename__ = "credit_card_purchases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    credit_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("credit_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    recurring_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_entries.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    installments: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    installment_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    first_installment_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")  # noqa: F821
    credit_card: Mapped["CreditCard"] = relationship(  # noqa: F821
        "CreditCard", back_populates="purchases"
    )
    category_ref: Mapped["Category | None"] = relationship("Category")  # noqa: F821
    recurring_entry: Mapped["RecurringEntry | None"] = relationship("RecurringEntry")  # noqa: F821
    installment_rows: Mapped[list["Installment"]] = relationship(  # noqa: F821
        back_populates="purchase", cascade="all, delete-orphan", order_by="Installment.installment_number"
    )

    def __repr__(self) -> str:
        return f"<CreditCardPurchase id={self.id} description={self.description!r} installments={self.installments}>"
