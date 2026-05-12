import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.currency import CurrencyRead


AccountType = Literal["checking", "savings", "cash"]


class AccountBase(BaseModel):
    name: str
    type: AccountType
    currency_id: uuid.UUID
    initial_balance: Decimal = Decimal("0.00")


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = None
    type: AccountType | None = None
    currency_id: uuid.UUID | None = None
    initial_balance: Decimal | None = None


class AccountRead(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    currency: CurrencyRead
