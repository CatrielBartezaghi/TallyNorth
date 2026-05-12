import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Currency(Base):
    __tablename__ = "currencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # ISO 4217 code for fiat (ARS, USD) or common ticker for crypto (BTC, ETH)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Display symbol: $, U$D, €, ₿, etc.
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    # How many decimal places to display (2 for fiat, 8 for BTC, etc.)
    decimal_places: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    is_crypto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Currency code={self.code} symbol={self.symbol!r}>"
