import uuid
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.installment import InstallmentRead


class PurchaseBase(BaseModel):
    credit_card_id: uuid.UUID
    category_id: uuid.UUID | None = None
    description: str
    total_amount: Decimal = Field(gt=0)
    installments: int = Field(ge=1, default=1)
    starting_installment: int = Field(ge=1, default=1)
    purchase_date: date
    category: str | None = None


class PurchaseCreate(PurchaseBase):
    pass


class PurchaseUpdate(BaseModel):
    description: str | None = None
    category_id: uuid.UUID | None = None
    category: str | None = None


class PurchaseRead(PurchaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    installment_amount: Decimal
    first_installment_date: date
    created_at: datetime
    installment_rows: list[InstallmentRead] = []
