import uuid
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead
from app.schemas.currency import CurrencyRead


class BudgetBase(BaseModel):
    category_id: uuid.UUID
    currency_id: uuid.UUID
    period_start: date
    amount: Decimal = Field(gt=0)
    notes: str | None = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    currency_id: uuid.UUID | None = None
    period_start: date | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    notes: str | None = None


class BudgetRead(BudgetBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    category: CategoryRead
    currency: CurrencyRead

