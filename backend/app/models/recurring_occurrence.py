import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RecurringOccurrence(Base):
    __tablename__ = "recurring_occurrences"
    __table_args__ = (
        UniqueConstraint(
            "recurring_entry_id",
            "scheduled_date",
            name="uq_recurring_occurrence_entry_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    recurring_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recurring_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "settled", "skipped", name="recurring_occurrence_status_enum"),
        nullable=False,
        default="pending",
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("credit_card_purchases.id", ondelete="SET NULL"),
        nullable=True,
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")  # noqa: F821
    entry: Mapped["RecurringEntry"] = relationship(  # noqa: F821
        "RecurringEntry", back_populates="occurrences"
    )
    transaction: Mapped["Transaction | None"] = relationship("Transaction")  # noqa: F821
    purchase: Mapped["CreditCardPurchase | None"] = relationship("CreditCardPurchase")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<RecurringOccurrence id={self.id} entry={self.recurring_entry_id} "
            f"date={self.scheduled_date} status={self.status}>"
        )
