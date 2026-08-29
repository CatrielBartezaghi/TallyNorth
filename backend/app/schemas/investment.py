import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.currency import CurrencyRead


InvestmentType = Literal["fixed_income", "fund", "stock", "crypto", "forex", "other"]
InvestmentOperationType = Literal["opening", "buy", "sell", "dividend", "interest", "fee"]


class InvestmentBase(BaseModel):
    name: str
    symbol: str | None = None
    broker: str | None = None
    type: InvestmentType = "other"
    currency_id: uuid.UUID
    invested_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    current_value: Decimal = Field(default=Decimal("0.00"), ge=0)
    expected_return_rate: Decimal | None = None
    notes: str | None = None


class InvestmentCreate(InvestmentBase):
    opening_quantity: Decimal | None = Field(default=None, gt=0, max_digits=24, decimal_places=8)


class InvestmentUpdate(BaseModel):
    name: str | None = None
    symbol: str | None = None
    broker: str | None = None
    type: InvestmentType | None = None
    currency_id: uuid.UUID | None = None
    expected_return_rate: Decimal | None = None
    notes: str | None = None


class InvestmentRead(InvestmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quantity: Decimal
    average_cost: Decimal | None
    realized_gain: Decimal
    created_at: datetime
    updated_at: datetime
    currency: CurrencyRead


class InvestmentOperationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    type: InvestmentOperationType
    account_id: uuid.UUID | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, gt=0)
    amount: Decimal = Field(gt=0)
    fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    date: date
    notes: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_quantity_price(self):
        if (self.quantity is None) != (self.unit_price is None):
            raise ValueError("quantity and unit_price must be provided together")
        if self.quantity is not None:
            computed = self.quantity * self.unit_price
            tolerance = max(Decimal("0.02"), self.amount * Decimal("0.001"))
            if abs(computed - self.amount) > tolerance:
                raise ValueError("amount must match quantity * unit_price")
        return self


class InvestmentOperationRead(InvestmentOperationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investment_id: uuid.UUID
    created_at: datetime


class InvestmentValuationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    value: Decimal = Field(ge=0)
    valuation_date: date
    source: str = Field(default="manual", min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=255)


class InvestmentValuationRead(InvestmentValuationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investment_id: uuid.UUID
    created_at: datetime
