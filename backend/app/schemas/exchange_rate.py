import uuid
from datetime import datetime
from datetime import date as DateType
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.currency import CurrencyRead


class ExchangeRateBase(BaseModel):
    from_currency_id: uuid.UUID
    to_currency_id: uuid.UUID
    rate: Decimal = Field(gt=0)
    date: DateType


class ExchangeRateCreate(ExchangeRateBase):
    pass


class ExchangeRateUpdate(BaseModel):
    rate: Decimal | None = Field(default=None, gt=0)
    date: DateType | None = None


class ExchangeRateRead(ExchangeRateBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    from_currency: CurrencyRead
    to_currency: CurrencyRead
