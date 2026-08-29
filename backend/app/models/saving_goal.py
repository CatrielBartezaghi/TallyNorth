import uuid
from datetime import datetime, date

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SavingGoal(Base):
    __tablename__ = "saving_goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
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
    allocations: Mapped[list["SavingGoalAllocation"]] = relationship(
        "SavingGoalAllocation", back_populates="saving_goal", cascade="all, delete-orphan"
    )


class SavingGoalAllocation(Base):
    __tablename__ = "saving_goal_allocations"
    __table_args__ = (
        CheckConstraint(
            "(account_id IS NOT NULL AND investment_id IS NULL) OR "
            "(account_id IS NULL AND investment_id IS NOT NULL)",
            name="ck_saving_goal_allocation_one_source",
        ),
        CheckConstraint(
            "allocation_percent > 0 AND allocation_percent <= 100",
            name="ck_saving_goal_allocation_percent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    saving_goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("saving_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True
    )
    investment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investments.id", ondelete="CASCADE"), nullable=True
    )
    allocation_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    saving_goal: Mapped["SavingGoal"] = relationship("SavingGoal", back_populates="allocations")
    account: Mapped["Account | None"] = relationship("Account")  # noqa: F821
    investment: Mapped["Investment | None"] = relationship("Investment")  # noqa: F821
