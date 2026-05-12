import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CurrencyBase(BaseModel):
    code: str
    name: str
    symbol: str
    decimal_places: int = 2
    is_crypto: bool = False


class CurrencyCreate(CurrencyBase):
    pass


class CurrencyUpdate(BaseModel):
    name: str | None = None
    symbol: str | None = None
    decimal_places: int | None = None
    is_crypto: bool | None = None


class CurrencyRead(CurrencyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
