from typing import Literal

from pydantic import BaseModel, Field


AssistantOperation = Literal[
    "create_transaction",
    "create_purchase",
    "create_budget",
    "cashflow_summary",
    "mark_installment_paid",
]

DraftStatus = Literal["draft", "needs_clarification", "rejected"]


class AssistantDraftRequest(BaseModel):
    message: str = Field(min_length=1, max_length=800)


class DraftField(BaseModel):
    key: str
    label: str
    value: str | int | float | bool | None


class AssistantDraftResponse(BaseModel):
    status: DraftStatus
    operation: AssistantOperation | None = None
    confidence: float = Field(ge=0, le=1, default=0)
    title: str
    summary: str
    preview: list[DraftField] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confirmation_required: bool = True
