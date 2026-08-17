import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatGPTAccountBalanceRead(BaseModel):
    id: uuid.UUID
    name: str
    currency: str
    current_balance: Decimal


class ChatGPTAccountBalanceList(BaseModel):
    accounts: list[ChatGPTAccountBalanceRead]


class ChatGPTAccountBalanceSet(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        description=(
            "Identificador único para este ajuste. Reutilizalo solamente al "
            "reintentar exactamente el mismo saldo objetivo."
        ),
    )
    account_id: uuid.UUID
    expected_current_balance: Decimal = Field(
        max_digits=15,
        decimal_places=2,
        description=(
            "Saldo observado inmediatamente antes de confirmar el ajuste. "
            "La operación falla si el saldo cambió."
        ),
    )
    new_current_balance: Decimal = Field(
        max_digits=15,
        decimal_places=2,
        description="Nuevo saldo real que debe quedar en la cuenta.",
    )


AccountBalanceActionStatus = Literal["updated", "unchanged", "already_processed"]


class ChatGPTAccountBalanceSetResult(BaseModel):
    status: AccountBalanceActionStatus
    account: ChatGPTAccountBalanceRead
    previous_balance: Decimal
    adjustment: Decimal
