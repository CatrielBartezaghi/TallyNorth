import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.currency import CurrencyRead


InvestmentType = Literal["fixed_income", "fund", "stock", "crypto", "forex", "other"]


class InvestmentBase(BaseModel):
    name: str
    type: InvestmentType = "other"
    currency_id: uuid.UUID
    invested_amount: Decimal = Field(gt=0)
    current_value: Decimal = Field(ge=0)
    expected_return_rate: Decimal | None = None
    notes: str | None = None


class InvestmentCreate(InvestmentBase):
    pass


class InvestmentUpdate(BaseModel):
    name: str | None = None
    type: InvestmentType | None = None
    currency_id: uuid.UUID | None = None
    invested_amount: Decimal | None = Field(default=None, gt=0)
    current_value: Decimal | None = Field(default=None, ge=0)
    expected_return_rate: Decimal | None = None
    notes: str | None = None


class InvestmentRead(InvestmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    currency: CurrencyRead

