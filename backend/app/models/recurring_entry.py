import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RecurringEntry(Base):
    __tablename__ = "recurring_entries"
    __table_args__ = (
        CheckConstraint(
            "(destination_type = 'account' AND account_id IS NOT NULL AND credit_card_id IS NULL) "
            "OR (destination_type = 'credit_card' AND credit_card_id IS NOT NULL AND account_id IS NULL)",
            name="ck_recurring_entry_exactly_one_destination",
        ),
        CheckConstraint(
            "type = 'expense' OR destination_type = 'account'",
            name="ck_recurring_entry_income_requires_account",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        SAEnum("income", "expense", name="recurring_entry_type_enum"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    frequency: Mapped[str] = mapped_column(
        SAEnum("weekly", "monthly", "yearly", name="recurring_frequency_enum"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    destination_type: Mapped[str] = mapped_column(
        SAEnum("account", "credit_card", name="recurring_destination_type_enum"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True
    )
    credit_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=True
    )

    last_generated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")  # noqa: F821
    account: Mapped["Account | None"] = relationship("Account")  # noqa: F821
    credit_card: Mapped["CreditCard | None"] = relationship("CreditCard")  # noqa: F821
    category_ref: Mapped["Category | None"] = relationship("Category")  # noqa: F821

    def __repr__(self) -> str:
        return f"<RecurringEntry id={self.id} description={self.description!r} destination={self.destination_type}>"
