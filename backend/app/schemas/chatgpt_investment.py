import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.investment import (
    InvestmentOperationRead,
    InvestmentOperationType,
    InvestmentRead,
    InvestmentType,
    InvestmentValuationRead,
)
from app.schemas.saving_goal import SavingGoalAllocationRead, SavingGoalRead


ActionStatus = Literal["created", "updated", "already_processed"]


class ChatGPTInvestmentAssetCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    name: str = Field(min_length=1, max_length=120)
    symbol: str | None = Field(default=None, max_length=32)
    broker: str | None = Field(default=None, max_length=80)
    type: InvestmentType = "other"
    currency_id: uuid.UUID
    opening_invested_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    opening_current_value: Decimal = Field(default=Decimal("0.00"), ge=0)
    opening_date: date | None = None
    expected_return_rate: Decimal | None = None
    notes: str | None = Field(default=None, max_length=255)


class ChatGPTInvestmentAssetResult(BaseModel):
    status: ActionStatus
    investment: InvestmentRead


class ChatGPTInvestmentOperationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    investment_id: uuid.UUID
    type: Literal["buy", "sell", "dividend", "interest", "fee"]
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


class ChatGPTInvestmentOperationResult(BaseModel):
    status: ActionStatus
    operation: InvestmentOperationRead
    investment: InvestmentRead


class ChatGPTInvestmentValuationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    investment_id: uuid.UUID
    value: Decimal = Field(ge=0)
    valuation_date: date
    source: str = Field(default="manual", min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=255)


class ChatGPTInvestmentValuationResult(BaseModel):
    status: ActionStatus
    valuation: InvestmentValuationRead
    investment: InvestmentRead


class ChatGPTSavingGoalAllocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    saving_goal_id: uuid.UUID
    account_id: uuid.UUID | None = None
    investment_id: uuid.UUID | None = None
    allocation_percent: Decimal = Field(default=Decimal("100.00"), gt=0, le=100)

    @model_validator(mode="after")
    def validate_source(self):
        if (self.account_id is None) == (self.investment_id is None):
            raise ValueError("exactly one of account_id or investment_id is required")
        return self


class ChatGPTSavingGoalAllocationResult(BaseModel):
    status: ActionStatus
    allocation: SavingGoalAllocationRead


class ChatGPTSavingGoalWithAllocations(BaseModel):
    goal: SavingGoalRead
    allocations: list[SavingGoalAllocationRead]
