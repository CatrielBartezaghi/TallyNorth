import uuid
from datetime import date as DateType, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TransactionType = Literal["income", "expense"]


class TransactionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    type: TransactionType
    amount: Decimal = Field(gt=0)
    description: str
    category: str | None = None
    date: DateType


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    type: TransactionType | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = None
    category: str | None = None
    date: DateType | None = None


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recurring_entry_id: uuid.UUID | None = None
    created_at: datetime
