import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


INVESTMENT_TYPES = ("fixed_income", "fund", "stock", "crypto", "forex", "other")
INVESTMENT_OPERATION_TYPES = ("opening", "buy", "sell", "dividend", "interest", "fee")


class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    broker: Mapped[str | None] = mapped_column(String(80), nullable=True)
    type: Mapped[str] = mapped_column(
        SAEnum(*INVESTMENT_TYPES, name="investment_type_enum"),
        nullable=False,
        default="other",
    )
    currency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False
    )
    invested_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    current_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    quantity: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    average_cost: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    realized_gain: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    expected_return_rate: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    currency: Mapped["Currency"] = relationship("Currency")  # noqa: F821
    operations: Mapped[list["InvestmentOperation"]] = relationship(
        "InvestmentOperation", back_populates="investment", cascade="all, delete-orphan"
    )
    valuations: Mapped[list["InvestmentValuation"]] = relationship(
        "InvestmentValuation", back_populates="investment", cascade="all, delete-orphan"
    )


class InvestmentOperation(Base):
    __tablename__ = "investment_operations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_investment_operation_amount_positive"),
        CheckConstraint("fee >= 0", name="ck_investment_operation_fee_nonnegative"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_investment_operation_quantity_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    investment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(
        SAEnum(*INVESTMENT_OPERATION_TYPES, name="investment_operation_type_enum"),
        nullable=False,
    )
    quantity: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    fee: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    investment: Mapped["Investment"] = relationship("Investment", back_populates="operations")
    account: Mapped["Account | None"] = relationship("Account")  # noqa: F821


class InvestmentValuation(Base):
    __tablename__ = "investment_valuations"
    __table_args__ = (
        CheckConstraint("value >= 0", name="ck_investment_valuation_value_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    investment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    valuation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    investment: Mapped["Investment"] = relationship("Investment", back_populates="valuations")
