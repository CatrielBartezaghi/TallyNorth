from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.recurring_entry import RecurringEntry
from app.routers.chatgpt_actions import (
    READ_ACTION,
    WRITE_ACTION,
    _conflict,
    _existing_action_request,
    _not_found,
    _owned_resource,
    _unprocessable,
    require_integration_scope,
)
from app.schemas.integration import ChatGPTRecurringEntryCreate, ChatGPTRecurringEntryResult
from app.schemas.recurring_entry import RecurringEntryRead
from app.services.chatgpt_operations import (
    InvalidCategoryError,
    OwnedResourceNotFoundError,
    create_chatgpt_recurring_entry,
)
from app.services.gpt_action_idempotency import action_request_hash, record_action_request
from app.services.integration_tokens import IntegrationPrincipal
from app.services.recurring_entry_service import sync_recurring_entries


router = APIRouter(prefix="/integrations/chatgpt", tags=["ChatGPT Actions"])


@router.get(
    "/recurring-entries",
    response_model=list[RecurringEntryRead],
    operation_id="listRecurringEntries",
    summary="Consultar recurrentes",
    description="Lista las reglas recurrentes activas e inactivas del usuario.",
    openapi_extra=READ_ACTION,
)
def list_recurring_entries_action(
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("context:read")),
):
    sync_recurring_entries(db, principal.user.id)
    return (
        db.query(RecurringEntry)
        .filter(RecurringEntry.user_id == principal.user.id)
        .order_by(RecurringEntry.created_at.desc())
        .all()
    )


def _existing_recurring_result(
    db: Session,
    user_id,
    payload: ChatGPTRecurringEntryCreate,
    request_hash: str,
) -> ChatGPTRecurringEntryResult | None:
    action_request = _existing_action_request(
        db,
        user_id,
        "createRecurringEntry",
        payload.idempotency_key,
        request_hash,
    )
    if action_request is None:
        return None
    entry = _owned_resource(
        db,
        RecurringEntry,
        action_request.resource_id,
        user_id,
        "recurring entry",
    )
    return ChatGPTRecurringEntryResult(
        status="already_processed",
        message="This request was already processed; no duplicate was created.",
        recurring_entry=entry,
    )


@router.post(
    "/recurring-entries",
    response_model=ChatGPTRecurringEntryResult,
    operation_id="createRecurringEntry",
    summary="Crear un recurrente",
    description=(
        "Crea una regla recurrente para una cuenta o tarjeta. "
        "Las ocurrencias se materializan automáticamente cuando corresponden."
    ),
    openapi_extra=WRITE_ACTION,
)
def create_recurring_entry_action(
    payload: ChatGPTRecurringEntryCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("transactions:create")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_recurring_result(db, user_id, payload, request_hash)
    if existing is not None:
        return existing

    try:
        entry = create_chatgpt_recurring_entry(db, user_id, payload)
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="createRecurringEntry",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=entry.id,
        )
        db.commit()
        db.refresh(entry)
        sync_recurring_entries(db, user_id)
        db.refresh(entry)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise _not_found(str(exc)) from exc
    except InvalidCategoryError as exc:
        db.rollback()
        raise _unprocessable(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_recurring_result(db, user_id, payload, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The recurring entry could not be created") from exc

    return ChatGPTRecurringEntryResult(
        status="created",
        message="Recurring entry created successfully.",
        recurring_entry=entry,
    )
