import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.purchase import PurchaseRead
from app.schemas.transaction import RecurrenceRule, TransactionRead, TransactionType


IntegrationScope = Literal[
    "context:read",
    "transactions:create",
    "purchases:create",
]

DEFAULT_INTEGRATION_SCOPES: list[IntegrationScope] = [
    "context:read",
    "transactions:create",
    "purchases:create",
]


class IntegrationTokenCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100, default="Mi GPT de ChatGPT")
    scopes: list[IntegrationScope] = Field(
        default_factory=lambda: list(DEFAULT_INTEGRATION_SCOPES),
        min_length=1,
    )
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def deduplicate_scopes(
        cls, value: list[IntegrationScope]
    ) -> list[IntegrationScope]:
        return list(dict.fromkeys(value))

    @field_validator('expires_at')
    @classmethod
    def validate_expiration(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('expires_at must include a timezone')
        if value <= datetime.now(timezone.utc):
            raise ValueError('expires_at must be in the future')
        return value


class IntegrationTokenRead(BaseModel):
    id: uuid.UUID
    name: str
    token_prefix: str
    scopes: list[IntegrationScope]
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class IntegrationTokenCreated(IntegrationTokenRead):
    token: str
    warning: str = (
        "Guardá este token ahora. Por seguridad no se volverá a mostrar."
    )


class ChatGPTContextAccount(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    currency: str


class ChatGPTContextCategory(BaseModel):
    id: uuid.UUID
    name: str
    type: str


class ChatGPTContextCreditCard(BaseModel):
    id: uuid.UUID
    name: str
    currency: str
    closing_day: int
    due_day: int


class ChatGPTFinanceContext(BaseModel):
    current_date: date
    timezone: str
    accounts: list[ChatGPTContextAccount]
    categories: list[ChatGPTContextCategory]
    credit_cards: list[ChatGPTContextCreditCard]


class ChatGPTTransactionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        description=(
            "Identificador único para esta operación. Reutilizalo solamente al "
            "reintentar exactamente la misma carga."
        ),
    )
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    description: str = Field(min_length=1, max_length=255)
    date: date
    is_recurring: bool = False
    recurrence_rule: RecurrenceRule | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_recurrence(self) -> "ChatGPTTransactionCreate":
        if self.is_recurring and self.recurrence_rule is None:
            raise ValueError(
                "recurrence_rule is required when is_recurring is true"
            )
        if not self.is_recurring and (
            self.recurrence_rule is not None or self.end_date is not None
        ):
            raise ValueError(
                "recurrence_rule and end_date require is_recurring=true"
            )
        if self.end_date is not None and self.end_date < self.date:
            raise ValueError("end_date cannot be before date")
        return self


class ChatGPTPurchaseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        description=(
            "Identificador único para esta operación. Reutilizalo solamente al "
            "reintentar exactamente la misma carga."
        ),
    )
    credit_card_id: uuid.UUID
    category_id: uuid.UUID | None = None
    description: str = Field(min_length=1, max_length=255)
    total_amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    installments: int = Field(ge=1, le=120, default=1)
    starting_installment: int = Field(ge=1, default=1)
    purchase_date: date

    @model_validator(mode="after")
    def validate_starting_installment(self) -> "ChatGPTPurchaseCreate":
        if self.starting_installment > self.installments:
            raise ValueError(
                "starting_installment cannot be greater than installments"
            )
        return self


ActionResultStatus = Literal["created", "already_processed"]


class ChatGPTTransactionResult(BaseModel):
    status: ActionResultStatus
    message: str
    transaction: TransactionRead


class ChatGPTPurchaseResult(BaseModel):
    status: ActionResultStatus
    message: str
    purchase: PurchaseRead
