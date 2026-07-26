from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.purchase import CreditCardPurchase
from app.models.transaction import Transaction
from app.schemas.integration import (
    ChatGPTContextAccount,
    ChatGPTContextCategory,
    ChatGPTContextCreditCard,
    ChatGPTFinanceContext,
    ChatGPTPurchaseCreate,
    ChatGPTPurchaseResult,
    ChatGPTTransactionCreate,
    ChatGPTTransactionResult,
)
from app.services.chatgpt_openapi import build_chatgpt_action_openapi
from app.services.chatgpt_operations import (
    InvalidCategoryError,
    OwnedResourceNotFoundError,
    create_chatgpt_purchase,
    create_chatgpt_transaction,
)
from app.services.gpt_action_idempotency import (
    action_request_hash,
    find_action_request,
    record_action_request,
)
from app.services.integration_tokens import (
    IntegrationPrincipal,
    authenticate_integration_token,
)


router = APIRouter(prefix="/integrations/chatgpt", tags=["ChatGPT Actions"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_integration_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> IntegrationPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid TallyNorth integration token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    principal = authenticate_integration_token(db, credentials.credentials)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked integration token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_integration_scope(
    required_scope: str,
) -> Callable[..., IntegrationPrincipal]:
    def dependency(
        principal: IntegrationPrincipal = Depends(get_integration_principal),
    ) -> IntegrationPrincipal:
        if required_scope not in principal.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Integration token requires scope: {required_scope}",
            )
        return principal

    return dependency


def _schema_server_url(request: Request) -> str:
    if settings.chatgpt_action_base_url:
        return settings.chatgpt_action_base_url.rstrip("/")

    suffix = "/integrations/chatgpt/openapi.json"
    request_url = str(request.url)
    if request_url.endswith(suffix):
        return request_url[: -len(suffix)]
    return str(request.base_url).rstrip("/")


@router.get("/openapi.json", include_in_schema=False)
def chatgpt_action_openapi(request: Request):
    return build_chatgpt_action_openapi(_schema_server_url(request))


@router.get("/context", response_model=ChatGPTFinanceContext)
def get_finance_context(
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(
        require_integration_scope("context:read")
    ),
):
    user_id = principal.user.id
    accounts = (
        db.query(Account)
        .filter(Account.user_id == user_id)
        .order_by(Account.name)
        .all()
    )
    categories = (
        db.query(Category)
        .filter(
            Category.user_id == user_id,
            Category.is_active.is_(True),
        )
        .order_by(Category.type, Category.name)
        .all()
    )
    cards = (
        db.query(CreditCard)
        .filter(CreditCard.user_id == user_id)
        .order_by(CreditCard.name)
        .all()
    )

    return ChatGPTFinanceContext(
        current_date=datetime.now(ZoneInfo(settings.app_timezone)).date(),
        timezone=settings.app_timezone,
        accounts=[
            ChatGPTContextAccount(
                id=account.id,
                name=account.name,
                type=account.type,
                currency=account.currency.code,
            )
            for account in accounts
        ],
        categories=[
            ChatGPTContextCategory(
                id=category.id,
                name=category.name,
                type=category.type,
            )
            for category in categories
        ],
        credit_cards=[
            ChatGPTContextCreditCard(
                id=card.id,
                name=card.name,
                currency=card.currency.code,
                closing_day=card.closing_day,
                due_day=card.due_day,
            )
            for card in cards
        ],
    )


def _existing_transaction_result(
    db: Session,
    user_id,
    payload: ChatGPTTransactionCreate,
    request_hash: str,
) -> ChatGPTTransactionResult | None:
    action_request = find_action_request(
        db,
        user_id,
        "createTransaction",
        payload.idempotency_key,
    )
    if action_request is None:
        return None
    if action_request.request_hash != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The idempotency key was already used with different transaction data"
            ),
        )

    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == action_request.resource_id,
            Transaction.user_id == user_id,
        )
        .first()
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The original transaction no longer exists",
        )
    return ChatGPTTransactionResult(
        status="already_processed",
        message="This request was already processed; no duplicate was created.",
        transaction=transaction,
    )


@router.post("/transactions", response_model=ChatGPTTransactionResult)
def create_transaction_action(
    payload: ChatGPTTransactionCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(
        require_integration_scope("transactions:create")
    ),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_transaction_result(db, user_id, payload, request_hash)
    if existing is not None:
        return existing

    try:
        transaction = create_chatgpt_transaction(db, user_id, payload)
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="createTransaction",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=transaction.id,
        )
        db.commit()
        db.refresh(transaction)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidCategoryError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_transaction_result(
            db,
            user_id,
            payload,
            request_hash,
        )
        if existing is not None:
            return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The transaction could not be created due to a data conflict",
        ) from exc

    return ChatGPTTransactionResult(
        status="created",
        message="Transaction created successfully.",
        transaction=transaction,
    )


def _existing_purchase_result(
    db: Session,
    user_id,
    payload: ChatGPTPurchaseCreate,
    request_hash: str,
) -> ChatGPTPurchaseResult | None:
    action_request = find_action_request(
        db,
        user_id,
        "createCreditCardPurchase",
        payload.idempotency_key,
    )
    if action_request is None:
        return None
    if action_request.request_hash != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The idempotency key was already used with different purchase data"
            ),
        )

    purchase = (
        db.query(CreditCardPurchase)
        .filter(
            CreditCardPurchase.id == action_request.resource_id,
            CreditCardPurchase.user_id == user_id,
        )
        .first()
    )
    if purchase is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The original purchase no longer exists",
        )
    return ChatGPTPurchaseResult(
        status="already_processed",
        message="This request was already processed; no duplicate was created.",
        purchase=purchase,
    )


@router.post("/purchases", response_model=ChatGPTPurchaseResult)
def create_purchase_action(
    payload: ChatGPTPurchaseCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(
        require_integration_scope("purchases:create")
    ),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_purchase_result(db, user_id, payload, request_hash)
    if existing is not None:
        return existing

    try:
        purchase = create_chatgpt_purchase(db, user_id, payload)
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="createCreditCardPurchase",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=purchase.id,
        )
        db.commit()
        db.refresh(purchase)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidCategoryError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_purchase_result(
            db,
            user_id,
            payload,
            request_hash,
        )
        if existing is not None:
            return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The purchase could not be created due to a data conflict",
        ) from exc

    return ChatGPTPurchaseResult(
        status="created",
        message="Credit card purchase created successfully.",
        purchase=purchase,
    )
