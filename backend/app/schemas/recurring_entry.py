import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


RecurringFrequency = Literal["weekly", "monthly", "yearly"]
RecurringDestinationType = Literal["account", "credit_card"]
RecurringEntryType = Literal["income", "expense"]
RecurringSettlementMode = Literal["automatic", "manual"]
RecurringOccurrenceStatus = Literal["pending", "settled", "skipped"]


class RecurringEntryBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: RecurringEntryType
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    description: str = Field(min_length=1, max_length=255)
    category_id: uuid.UUID | None = None
    frequency: RecurringFrequency
    start_date: date
    end_date: date | None = None
    active: bool = True
    settlement_mode: RecurringSettlementMode = "automatic"
    destination_type: RecurringDestinationType
    account_id: uuid.UUID | None = None
    credit_card_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_destination(self) -> "RecurringEntryBase":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")

        if self.destination_type == "account":
            if self.account_id is None or self.credit_card_id is not None:
                raise ValueError("account destination requires only account_id")
        else:
            if self.credit_card_id is None or self.account_id is not None:
                raise ValueError("credit card destination requires only credit_card_id")
            if self.type != "expense":
                raise ValueError("credit card recurring entries must be expenses")

        return self


class RecurringEntryCreate(RecurringEntryBase):
    pass


class RecurringEntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: RecurringEntryType | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=15, decimal_places=2)
    description: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: uuid.UUID | None = None
    frequency: RecurringFrequency | None = None
    start_date: date | None = None
    end_date: date | None = None
    active: bool | None = None
    settlement_mode: RecurringSettlementMode | None = None
    destination_type: RecurringDestinationType | None = None
    account_id: uuid.UUID | None = None
    credit_card_id: uuid.UUID | None = None


class RecurringEntryRead(RecurringEntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str | None = None
    last_generated_date: date | None = None
    created_at: datetime


class RecurringOccurrenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recurring_entry_id: uuid.UUID
    scheduled_date: date
    amount: Decimal
    status: RecurringOccurrenceStatus
    transaction_id: uuid.UUID | None = None
    purchase_id: uuid.UUID | None = None
    settled_at: datetime | None = None
    created_at: datetime
    entry: RecurringEntryRead


class RecurringOccurrenceSettle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effective_date: date | None = None
