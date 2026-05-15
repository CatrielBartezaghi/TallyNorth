import uuid
from datetime import datetime

from sqlalchemy import String, Numeric, DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(
        SAEnum("checking", "savings", "cash", name="account_type_enum"),
        nullable=False,
    )
    currency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False
    )
    initial_balance: Mapped[float] = mapped_column(
        Numeric(15, 2), nullable=False, default=0.00
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")  # noqa: F821
    currency: Mapped["Currency"] = relationship("Currency")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.name!r} type={self.type}>"
