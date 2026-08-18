import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.budget import BudgetRead
from app.schemas.installment import InstallmentRead
from app.schemas.investment import InvestmentRead, InvestmentType
from app.schemas.purchase import PurchaseRead
from app.schemas.recurring_entry import RecurringEntryBase, RecurringEntryRead
from app.schemas.saving_goal import SavingGoalRead
from app.schemas.transaction import TransactionRead, TransactionType


IntegrationScope = Literal[
    "context:read",
    "transactions:create",
    "purchases:create",
    "budgets:write",
    "saving_goals:write",
    "investments:write",
    "installments:pay",
]

DEFAULT_INTEGRATION_SCOPES: list[IntegrationScope] = [
    "context:read",
    "transactions:create",
    "purchases:create",
    "budgets:write",
    "saving_goals:write",
    "investments:write",
    "installments:pay",
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

    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expires_at must include a timezone")
        if value <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")
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
    payment_account_id: uuid.UUID | None = None


class ChatGPTContextCurrency(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    symbol: str
    decimal_places: int
    is_crypto: bool


class ChatGPTFinanceContext(BaseModel):
    current_date: date
    timezone: str
    accounts: list[ChatGPTContextAccount]
    categories: list[ChatGPTContextCategory]
    credit_cards: list[ChatGPTContextCreditCard]
    currencies: list[ChatGPTContextCurrency]


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


class ChatGPTRecurringEntryCreate(RecurringEntryBase):
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


class ChatGPTRecurringEntryResult(BaseModel):
    status: ActionResultStatus
    message: str
    recurring_entry: RecurringEntryRead


class ChatGPTPurchaseResult(BaseModel):
    status: ActionResultStatus
    message: str
    purchase: PurchaseRead


FinanceEntryKind = Literal["transaction", "credit_card_purchase"]


class ChatGPTFinanceEntryRead(BaseModel):
    kind: FinanceEntryKind
    id: uuid.UUID
    description: str
    type: TransactionType
    amount: Decimal
    currency: str
    date: date
    category_id: uuid.UUID | None = None
    category: str | None = None
    account_id: uuid.UUID | None = None
    account_name: str | None = None
    credit_card_id: uuid.UUID | None = None
    credit_card_name: str | None = None
    installments: int | None = None
    installment_amount: Decimal | None = None
    recurring_entry_id: uuid.UUID | None = None


class ChatGPTFinanceEntrySearchResult(BaseModel):
    items: list[ChatGPTFinanceEntryRead]
    limit: int
    offset: int
    has_more: bool


class ChatGPTCashflowMonth(BaseModel):
    month: str
    total_income: Decimal
    total_expenses: Decimal
    total_installments: Decimal
    net: Decimal


class ChatGPTCashflowProjection(BaseModel):
    currency: str
    warnings: list[str]
    months: list[ChatGPTCashflowMonth]


class ChatGPTInstallmentRead(BaseModel):
    id: uuid.UUID
    purchase_id: uuid.UUID
    description: str
    installment_number: int
    total_installments: int
    due_date: date
    amount: Decimal
    currency: str
    is_paid: bool
    credit_card_id: uuid.UUID
    credit_card_name: str
    paid_account_id: uuid.UUID | None = None
    paid_at: datetime | None = None


class ChatGPTInstallmentSearchResult(BaseModel):
    items: list[ChatGPTInstallmentRead]
    limit: int
    has_more: bool


class ChatGPTBatchTransactionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    kind: Literal["transaction"]
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    description: str = Field(min_length=1, max_length=255)
    date: date


class ChatGPTBatchPurchaseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    kind: Literal["credit_card_purchase"]
    credit_card_id: uuid.UUID
    category_id: uuid.UUID | None = None
    description: str = Field(min_length=1, max_length=255)
    total_amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    installments: int = Field(ge=1, le=120, default=1)
    starting_installment: int = Field(ge=1, default=1)
    purchase_date: date

    @model_validator(mode="after")
    def validate_starting_installment(self) -> "ChatGPTBatchPurchaseCreate":
        if self.starting_installment > self.installments:
            raise ValueError(
                "starting_installment cannot be greater than installments"
            )
        return self


ChatGPTBatchFinanceEntry = Annotated[
    ChatGPTBatchTransactionCreate | ChatGPTBatchPurchaseCreate,
    Field(discriminator="kind"),
]


class ChatGPTFinanceBatchCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    entries: list[ChatGPTBatchFinanceEntry] = Field(
        min_length=1,
        max_length=50,
    )


class ChatGPTFinanceBatchItemResult(BaseModel):
    index: int
    kind: FinanceEntryKind
    resource_id: uuid.UUID


class ChatGPTFinanceBatchResult(BaseModel):
    status: ActionResultStatus
    items: list[ChatGPTFinanceBatchItemResult]


class ChatGPTBudgetSet(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    category_id: uuid.UUID
    currency_id: uuid.UUID
    period_month: str = Field(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Budget month in YYYY-MM format.",
    )
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    notes: str | None = Field(default=None, max_length=255)
    expected_current_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=15,
        decimal_places=2,
    )


BudgetActionStatus = Literal["created", "updated", "already_processed"]


class ChatGPTBudgetResult(BaseModel):
    status: BudgetActionStatus
    budget: BudgetRead


class ChatGPTSavingGoalCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    name: str = Field(min_length=1, max_length=120)
    currency_id: uuid.UUID
    target_amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    current_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    target_date: date | None = None


class ChatGPTSavingGoalProgressUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    goal_id: uuid.UUID
    expected_current_amount: Decimal = Field(
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    new_current_amount: Decimal = Field(
        ge=0,
        max_digits=15,
        decimal_places=2,
    )


ResourceActionStatus = Literal["created", "updated", "already_processed"]


class ChatGPTSavingGoalResult(BaseModel):
    status: ResourceActionStatus
    saving_goal: SavingGoalRead


class ChatGPTInvestmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    name: str = Field(min_length=1, max_length=120)
    type: InvestmentType = "other"
    currency_id: uuid.UUID
    invested_amount: Decimal = Field(
        gt=0,
        max_digits=15,
        decimal_places=2,
    )
    current_value: Decimal = Field(
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    expected_return_rate: Decimal | None = Field(
        default=None,
        max_digits=8,
        decimal_places=4,
    )
    notes: str | None = Field(default=None, max_length=255)


class ChatGPTInvestmentValueUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    investment_id: uuid.UUID
    expected_current_value: Decimal = Field(
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    new_current_value: Decimal = Field(
        ge=0,
        max_digits=15,
        decimal_places=2,
    )


class ChatGPTInvestmentResult(BaseModel):
    status: ResourceActionStatus
    investment: InvestmentRead


class ChatGPTInstallmentPaymentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    installment_id: uuid.UUID
    paid_account_id: uuid.UUID


InstallmentPaymentStatus = Literal["paid", "already_processed"]


class ChatGPTInstallmentPaymentResult(BaseModel):
    status: InstallmentPaymentStatus
    installment: InstallmentRead
