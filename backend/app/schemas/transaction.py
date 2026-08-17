import uuid
from datetime import datetime
from datetime import date as DateType
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TransactionType = Literal["income", "expense"]
RecurrenceRule = Literal["monthly", "weekly", "yearly"]


class TransactionBase(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    type: TransactionType
    amount: Decimal = Field(gt=0)
    description: str
    category: str | None = None
    date: DateType
    is_recurring: bool = False
    recurrence_rule: RecurrenceRule | None = None
    end_date: DateType | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    type: TransactionType | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = None
    category: str | None = None
    date: DateType | None = None
    is_recurring: bool | None = None
    recurrence_rule: RecurrenceRule | None = None
    end_date: DateType | None = None


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
