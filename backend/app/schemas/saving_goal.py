import uuid
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.currency import CurrencyRead


class SavingGoalBase(BaseModel):
    name: str
    currency_id: uuid.UUID
    target_amount: Decimal = Field(gt=0)
    current_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    target_date: date | None = None
    color: str = "#22c55e"
    icon: str | None = None


class SavingGoalCreate(SavingGoalBase):
    pass


class SavingGoalUpdate(BaseModel):
    name: str | None = None
    currency_id: uuid.UUID | None = None
    target_amount: Decimal | None = Field(default=None, gt=0)
    current_amount: Decimal | None = Field(default=None, ge=0)
    target_date: date | None = None
    color: str | None = None
    icon: str | None = None


class SavingGoalRead(SavingGoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    currency: CurrencyRead

