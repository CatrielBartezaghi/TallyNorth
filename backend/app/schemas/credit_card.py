import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.currency import CurrencyRead


class CreditCardBase(BaseModel):
    name: str
    closing_day: int = Field(ge=1, le=31)
    due_day: int = Field(ge=1, le=31)
    currency_id: uuid.UUID
    payment_account_id: uuid.UUID | None = None
    credit_limit: Decimal | None = None


class CreditCardCreate(CreditCardBase):
    pass


class CreditCardUpdate(BaseModel):
    name: str | None = None
    closing_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)
    currency_id: uuid.UUID | None = None
    payment_account_id: uuid.UUID | None = None
    credit_limit: Decimal | None = None


class CreditCardRead(CreditCardBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    currency: CurrencyRead
