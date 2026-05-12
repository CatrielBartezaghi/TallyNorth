import uuid
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InstallmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_id: uuid.UUID
    installment_number: int
    due_date: date
    amount: Decimal
    is_paid: bool
    paid_account_id: uuid.UUID | None = None
    paid_at: datetime | None = None
    created_at: datetime


class InstallmentUpdate(BaseModel):
    is_paid: bool
    paid_account_id: uuid.UUID | None = None
