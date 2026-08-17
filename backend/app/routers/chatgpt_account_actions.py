from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account import Account
from app.routers.chatgpt_actions import require_integration_scope
from app.schemas.chatgpt_account import (
    ChatGPTAccountBalanceList,
    ChatGPTAccountBalanceRead,
    ChatGPTAccountBalanceSet,
    ChatGPTAccountBalanceSetResult,
)
from app.services.account_balance_service import (
    get_account_current_balance,
    reconcile_account_balance,
)
from app.services.gpt_action_idempotency import (
    action_request_hash,
    find_action_request,
    record_action_request,
)
from app.services.integration_tokens import IntegrationPrincipal


router = APIRouter(prefix="/integrations/chatgpt", tags=["ChatGPT Actions"])
READ_ACTION = {"x-openai-isConsequential": False}
WRITE_ACTION = {"x-openai-isConsequential": True}
OPERATION = "setAccountBalance"


def _account_read(db: Session, account: Account) -> ChatGPTAccountBalanceRead:
    return ChatGPTAccountBalanceRead(
        id=account.id,
        name=account.name,
        currency=account.currency.code,
        current_balance=get_account_current_balance(db, account),
    )


def _conflict(message: str, code: str = "data_conflict") -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={"code": code, "message": message},
    )


def _existing_result(
    db: Session,
    user_id,
    payload: ChatGPTAccountBalanceSet,
    request_hash: str,
) -> ChatGPTAccountBalanceSetResult | None:
    request = find_action_request(
        db,
        user_id,
        OPERATION,
        payload.idempotency_key,
    )
    if request is None:
        return None
    if request.request_hash != request_hash:
        raise _conflict(
            "The idempotency key was already used with different data",
            "idempotency_key_reused",
        )
    if not request.response_payload:
        raise _conflict("The cached account balance result is unavailable")

    cached = dict(request.response_payload)
    cached["status"] = "already_processed"
    return ChatGPTAccountBalanceSetResult.model_validate(cached)


@router.get(
    "/account-balances",
    response_model=ChatGPTAccountBalanceList,
    operation_id="getAccountBalances",
    summary="Consultar saldos actuales de cuentas",
    description=(
        "Devuelve el saldo calculado de cada cuenta para confirmar un ajuste "
        "sin inventar importes ni identificadores."
    ),
    openapi_extra=READ_ACTION,
)
def get_account_balances(
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(
        require_integration_scope("context:read")
    ),
):
    accounts = (
        db.query(Account)
        .filter(Account.user_id == principal.user.id)
        .order_by(Account.name)
        .all()
    )
    return ChatGPTAccountBalanceList(
        accounts=[_account_read(db, account) for account in accounts]
    )


@router.post(
    "/account-balances",
    response_model=ChatGPTAccountBalanceSetResult,
    operation_id="setAccountBalance",
    summary="Ajustar saldo actual de una cuenta",
    description=(
        "Reconcilia el saldo real de una cuenta sin crear un ingreso o gasto "
        "artificial. Requiere el saldo vigente previamente consultado."
    ),
    openapi_extra=WRITE_ACTION,
)
def set_account_balance(
    payload: ChatGPTAccountBalanceSet,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(
        require_integration_scope("transactions:create")
    ),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_result(db, user_id, payload, request_hash)
    if existing is not None:
        return existing

    account = (
        db.query(Account)
        .filter(
            Account.id == payload.account_id,
            Account.user_id == user_id,
        )
        .with_for_update()
        .first()
    )
    if account is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "resource_not_found",
                "message": "Account not found for the authenticated user",
            },
        )

    try:
        previous_balance, adjustment = reconcile_account_balance(
            db,
            account,
            expected_current_balance=payload.expected_current_balance,
            new_current_balance=payload.new_current_balance,
        )
        result = ChatGPTAccountBalanceSetResult(
            status="unchanged" if adjustment == Decimal("0") else "updated",
            account=_account_read(db, account),
            previous_balance=previous_balance,
            adjustment=adjustment,
        )
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation=OPERATION,
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=account.id,
            response_payload=result.model_dump(mode="json"),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise _conflict(str(exc), "account_balance_changed") from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_result(db, user_id, payload, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The account balance could not be adjusted") from exc

    return result
