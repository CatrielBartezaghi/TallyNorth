import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Callable, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.currency import Currency
from app.models.installment import Installment
from app.models.investment import Investment
from app.models.purchase import CreditCardPurchase
from app.models.saving_goal import SavingGoal
from app.models.transaction import Transaction
from app.schemas.dashboard import DashboardSummary
from app.schemas.integration import (
    ChatGPTBudgetResult,
    ChatGPTBudgetSet,
    ChatGPTCashflowProjection,
    ChatGPTContextAccount,
    ChatGPTContextCategory,
    ChatGPTContextCreditCard,
    ChatGPTContextCurrency,
    ChatGPTFinanceBatchCreate,
    ChatGPTFinanceBatchResult,
    ChatGPTFinanceContext,
    ChatGPTFinanceEntrySearchResult,
    ChatGPTInstallmentPaymentCreate,
    ChatGPTInstallmentPaymentResult,
    ChatGPTInstallmentSearchResult,
    ChatGPTInvestmentCreate,
    ChatGPTInvestmentResult,
    ChatGPTInvestmentValueUpdate,
    ChatGPTPurchaseCreate,
    ChatGPTPurchaseResult,
    ChatGPTSavingGoalCreate,
    ChatGPTSavingGoalProgressUpdate,
    ChatGPTSavingGoalResult,
    ChatGPTTransactionCreate,
    ChatGPTTransactionResult,
)
from app.services.chatgpt_openapi import build_chatgpt_action_openapi
from app.services.chatgpt_operations import (
    ActionConflictError,
    BatchItemError,
    InvalidCategoryError,
    OwnedResourceNotFoundError,
    create_chatgpt_finance_batch,
    create_chatgpt_investment,
    create_chatgpt_purchase,
    create_chatgpt_saving_goal,
    create_chatgpt_transaction,
    mark_chatgpt_installment_paid,
    set_chatgpt_budget,
    update_chatgpt_investment_value,
    update_chatgpt_saving_goal_progress,
)
from app.services.chatgpt_queries import (
    CurrencyNotFoundError,
    CurrencySelectionRequiredError,
    build_chatgpt_cashflow_projection,
    list_chatgpt_installments,
    resolve_chatgpt_currency,
    search_chatgpt_finance_entries,
)
from app.services.dashboard_service import build_dashboard_summary
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
READ_ACTION = {"x-openai-isConsequential": False}
WRITE_ACTION = {"x-openai-isConsequential": True}


def get_integration_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> IntegrationPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "A valid TallyNorth integration token is required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    principal = authenticate_integration_token(db, credentials.credentials)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_integration_token", "message": "Invalid, expired, or revoked integration token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_integration_scope(required_scope: str) -> Callable[..., IntegrationPrincipal]:
    def dependency(
        principal: IntegrationPrincipal = Depends(get_integration_principal),
    ) -> IntegrationPrincipal:
        if required_scope not in principal.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "missing_scope", "message": f"Integration token requires scope: {required_scope}"},
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


def _today() -> date:
    return datetime.now(ZoneInfo(settings.app_timezone)).date()


def _conflict(message: str, code: str = "data_conflict") -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "resource_not_found", "message": message})


def _unprocessable(message: str, *, issues: list[dict] | None = None) -> HTTPException:
    detail: dict = {"code": "invalid_request", "message": message}
    if issues:
        detail["issues"] = issues
    return HTTPException(status_code=422, detail=detail)


def _existing_action_request(db: Session, user_id, operation: str, idempotency_key: str, request_hash: str):
    action_request = find_action_request(db, user_id, operation, idempotency_key)
    if action_request is None:
        return None
    if action_request.request_hash != request_hash:
        raise _conflict("The idempotency key was already used with different data", "idempotency_key_reused")
    return action_request


def _owned_resource(db: Session, model, resource_id, user_id, label: str):
    resource = db.query(model).filter(model.id == resource_id, model.user_id == user_id).first()
    if resource is None:
        raise _conflict(f"The original {label} no longer exists")
    return resource


def _currency_code_or_http_error(db: Session, user_id, requested_code: str | None) -> str:
    try:
        return resolve_chatgpt_currency(db, user_id, requested_code)
    except CurrencySelectionRequiredError as exc:
        raise HTTPException(status_code=422, detail={"code": "currency_required", "message": str(exc), "allowed_currencies": exc.allowed_codes}) from exc
    except CurrencyNotFoundError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/openapi.json", include_in_schema=False)
def chatgpt_action_openapi(request: Request):
    return build_chatgpt_action_openapi(_schema_server_url(request), request.app.openapi())


@router.get(
    "/context",
    response_model=ChatGPTFinanceContext,
    operation_id="getFinanceContext",
    summary="Obtener contexto financiero",
    description="Devuelve IDs válidos de cuentas, categorías, tarjetas y monedas.",
    openapi_extra=READ_ACTION,
)
def get_finance_context(
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("context:read")),
):
    user_id = principal.user.id
    accounts = db.query(Account).filter(Account.user_id == user_id).order_by(Account.name).all()
    categories = db.query(Category).filter(Category.user_id == user_id, Category.is_active.is_(True)).order_by(Category.type, Category.name).all()
    cards = db.query(CreditCard).filter(CreditCard.user_id == user_id).order_by(CreditCard.name).all()
    currencies = db.query(Currency).order_by(Currency.code).all()
    return ChatGPTFinanceContext(
        current_date=_today(),
        timezone=settings.app_timezone,
        accounts=[ChatGPTContextAccount(id=item.id, name=item.name, type=item.type, currency=item.currency.code) for item in accounts],
        categories=[ChatGPTContextCategory(id=item.id, name=item.name, type=item.type) for item in categories],
        credit_cards=[ChatGPTContextCreditCard(id=item.id, name=item.name, currency=item.currency.code, closing_day=item.closing_day, due_day=item.due_day, payment_account_id=item.payment_account_id) for item in cards],
        currencies=[ChatGPTContextCurrency(id=item.id, code=item.code, name=item.name, symbol=item.symbol, decimal_places=item.decimal_places, is_crypto=item.is_crypto) for item in currencies],
    )


@router.get(
    "/summary",
    response_model=DashboardSummary,
    operation_id="getFinancialSummary",
    summary="Consultar resumen financiero",
    description="Devuelve KPIs, saldos, presupuestos, metas, inversiones y actividad reciente.",
    openapi_extra=READ_ACTION,
)
def get_financial_summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    currency: str | None = Query(default=None, min_length=3, max_length=10),
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("context:read")),
):
    today = _today()
    resolved_from = date_from or date(today.year, today.month, 1)
    resolved_to = date_to or today
    if resolved_to < resolved_from:
        raise _unprocessable("date_to cannot be before date_from")
    target_currency = _currency_code_or_http_error(db, principal.user.id, currency)
    try:
        return build_dashboard_summary(db, date_from=resolved_from, date_to=resolved_to, currency_code=target_currency, user_id=principal.user.id)
    except ValueError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get(
    "/cashflow",
    response_model=ChatGPTCashflowProjection,
    operation_id="getCashflowProjection",
    summary="Consultar proyección de flujo de caja",
    description="Proyecta ingresos, gastos y cuotas de los próximos meses en una moneda.",
    openapi_extra=READ_ACTION,
)
def get_cashflow_projection(
    months: int = Query(default=6, ge=1, le=12),
    currency: str | None = Query(default=None, min_length=3, max_length=10),
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("context:read")),
):
    target_currency = _currency_code_or_http_error(db, principal.user.id, currency)
    return build_chatgpt_cashflow_projection(db, principal.user.id, target_currency=target_currency, months=months, current_date=_today())
@router.get(
    "/entries",
    response_model=ChatGPTFinanceEntrySearchResult,
    operation_id="searchFinanceEntries",
    summary="Buscar movimientos y compras",
    description="Busca ingresos, gastos y compras con filtros financieros.",
    openapi_extra=READ_ACTION,
)
def search_finance_entries(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    kind: Literal["all", "transaction", "credit_card_purchase"] = Query(default="all"),
    type: Literal["income", "expense"] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    account_id: uuid.UUID | None = Query(default=None),
    credit_card_id: uuid.UUID | None = Query(default=None),
    min_amount: Decimal | None = Query(default=None, ge=0),
    max_amount: Decimal | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=5000),
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("context:read")),
):
    if date_from and date_to and date_to < date_from:
        raise _unprocessable("date_to cannot be before date_from")
    if min_amount is not None and max_amount is not None and max_amount < min_amount:
        raise _unprocessable("max_amount cannot be lower than min_amount")
    return search_chatgpt_finance_entries(
        db,
        principal.user.id,
        query_text=q,
        kind=kind,
        transaction_type=type,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        account_id=account_id,
        credit_card_id=credit_card_id,
        min_amount=min_amount,
        max_amount=max_amount,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/installments",
    response_model=ChatGPTInstallmentSearchResult,
    operation_id="getUpcomingInstallments",
    summary="Consultar cuotas",
    description="Lista cuotas por período, tarjeta y estado; por defecto muestra pendientes.",
    openapi_extra=READ_ACTION,
)
def get_upcoming_installments(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    credit_card_id: uuid.UUID | None = Query(default=None),
    installment_status: Literal["pending", "paid", "all"] = Query(default="pending", alias="status"),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("context:read")),
):
    effective_from = date_from
    if effective_from is None and installment_status == "pending":
        effective_from = _today()
    if effective_from and date_to and date_to < effective_from:
        raise _unprocessable("date_to cannot be before date_from")
    return list_chatgpt_installments(
        db,
        principal.user.id,
        date_from=effective_from,
        date_to=date_to,
        credit_card_id=credit_card_id,
        installment_status=installment_status,
        limit=limit,
    )


def _existing_transaction_result(db: Session, user_id, payload: ChatGPTTransactionCreate, request_hash: str) -> ChatGPTTransactionResult | None:
    action_request = _existing_action_request(db, user_id, "createTransaction", payload.idempotency_key, request_hash)
    if action_request is None:
        return None
    transaction = _owned_resource(db, Transaction, action_request.resource_id, user_id, "transaction")
    return ChatGPTTransactionResult(status="already_processed", message="This request was already processed; no duplicate was created.", transaction=transaction)


@router.post(
    "/transactions",
    response_model=ChatGPTTransactionResult,
    operation_id="createTransaction",
    summary="Crear un ingreso o gasto",
    description="Crea una transacción confirmada sobre una cuenta del usuario.",
    openapi_extra=WRITE_ACTION,
)
def create_transaction_action(
    payload: ChatGPTTransactionCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("transactions:create")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_transaction_result(db, user_id, payload, request_hash)
    if existing is not None:
        return existing
    try:
        transaction = create_chatgpt_transaction(db, user_id, payload)
        record_action_request(db, user_id=user_id, integration_token_id=principal.token.id, operation="createTransaction", idempotency_key=payload.idempotency_key, request_hash=request_hash, resource_id=transaction.id)
        db.commit()
        db.refresh(transaction)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise _not_found(str(exc)) from exc
    except InvalidCategoryError as exc:
        db.rollback()
        raise _unprocessable(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_transaction_result(db, user_id, payload, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The transaction could not be created") from exc
    return ChatGPTTransactionResult(status="created", message="Transaction created successfully.", transaction=transaction)


def _existing_purchase_result(db: Session, user_id, payload: ChatGPTPurchaseCreate, request_hash: str) -> ChatGPTPurchaseResult | None:
    action_request = _existing_action_request(db, user_id, "createCreditCardPurchase", payload.idempotency_key, request_hash)
    if action_request is None:
        return None
    purchase = _owned_resource(db, CreditCardPurchase, action_request.resource_id, user_id, "purchase")
    return ChatGPTPurchaseResult(status="already_processed", message="This request was already processed; no duplicate was created.", purchase=purchase)


@router.post(
    "/purchases",
    response_model=ChatGPTPurchaseResult,
    operation_id="createCreditCardPurchase",
    summary="Crear una compra con tarjeta",
    description="Crea una compra confirmada y genera sus cuotas.",
    openapi_extra=WRITE_ACTION,
)
def create_purchase_action(
    payload: ChatGPTPurchaseCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("purchases:create")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_purchase_result(db, user_id, payload, request_hash)
    if existing is not None:
        return existing
    try:
        purchase = create_chatgpt_purchase(db, user_id, payload)
        record_action_request(db, user_id=user_id, integration_token_id=principal.token.id, operation="createCreditCardPurchase", idempotency_key=payload.idempotency_key, request_hash=request_hash, resource_id=purchase.id)
        db.commit()
        db.refresh(purchase)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise _not_found(str(exc)) from exc
    except InvalidCategoryError as exc:
        db.rollback()
        raise _unprocessable(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_purchase_result(db, user_id, payload, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The purchase could not be created") from exc
    return ChatGPTPurchaseResult(status="created", message="Credit card purchase created successfully.", purchase=purchase)
def _existing_batch_result(db: Session, user_id, payload: ChatGPTFinanceBatchCreate, request_hash: str) -> ChatGPTFinanceBatchResult | None:
    action_request = _existing_action_request(db, user_id, "createFinanceEntriesBatch", payload.idempotency_key, request_hash)
    if action_request is None:
        return None
    if not action_request.response_payload:
        raise _conflict("The cached batch result is unavailable")
    return ChatGPTFinanceBatchResult(status="already_processed", items=action_request.response_payload["items"])


@router.post(
    "/entries/batch",
    response_model=ChatGPTFinanceBatchResult,
    operation_id="createFinanceEntriesBatch",
    summary="Crear un lote financiero mixto",
    description="Crea atómicamente hasta 50 transacciones y compras confirmadas.",
    openapi_extra=WRITE_ACTION,
)
def create_finance_entries_batch(
    payload: ChatGPTFinanceBatchCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(get_integration_principal),
):
    required_scopes = {"transactions:create" if entry.kind == "transaction" else "purchases:create" for entry in payload.entries}
    missing_scopes = sorted(required_scopes - principal.scopes)
    if missing_scopes:
        raise HTTPException(status_code=403, detail={"code": "missing_scope", "message": "Integration token lacks required batch scopes", "missing_scopes": missing_scopes})
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_batch_result(db, user_id, payload, request_hash)
    if existing is not None:
        return existing
    try:
        items = create_chatgpt_finance_batch(db, user_id, payload)
        cached_payload = {"items": [item.model_dump(mode="json") for item in items]}
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="createFinanceEntriesBatch",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=uuid.uuid4(),
            response_payload=cached_payload,
        )
        db.commit()
    except BatchItemError as exc:
        db.rollback()
        raise _unprocessable("The batch was not created because one item is invalid", issues=[{"index": exc.index, "message": exc.message}]) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_batch_result(db, user_id, payload, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The batch could not be created") from exc
    return ChatGPTFinanceBatchResult(status="created", items=items)


def _existing_budget_result(db: Session, user_id, payload: ChatGPTBudgetSet, request_hash: str) -> ChatGPTBudgetResult | None:
    action_request = _existing_action_request(db, user_id, "setBudget", payload.idempotency_key, request_hash)
    if action_request is None:
        return None
    return ChatGPTBudgetResult(status="already_processed", budget=_owned_resource(db, Budget, action_request.resource_id, user_id, "budget"))


@router.post(
    "/budgets",
    response_model=ChatGPTBudgetResult,
    operation_id="setBudget",
    summary="Fijar un presupuesto mensual",
    description="Crea o actualiza un presupuesto con control del importe anterior.",
    openapi_extra=WRITE_ACTION,
)
def set_budget_action(
    payload: ChatGPTBudgetSet,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("budgets:write")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_budget_result(db, user_id, payload, request_hash)
    if existing is not None:
        return existing
    try:
        budget, action_status = set_chatgpt_budget(db, user_id, payload)
        record_action_request(db, user_id=user_id, integration_token_id=principal.token.id, operation="setBudget", idempotency_key=payload.idempotency_key, request_hash=request_hash, resource_id=budget.id)
        db.commit()
        db.refresh(budget)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise _not_found(str(exc)) from exc
    except InvalidCategoryError as exc:
        db.rollback()
        raise _unprocessable(str(exc)) from exc
    except ActionConflictError as exc:
        db.rollback()
        raise _conflict(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_budget_result(db, user_id, payload, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The budget could not be saved") from exc
    return ChatGPTBudgetResult(status=action_status, budget=budget)


def _existing_saving_goal_result(db: Session, user_id, operation: str, idempotency_key: str, request_hash: str) -> ChatGPTSavingGoalResult | None:
    action_request = _existing_action_request(db, user_id, operation, idempotency_key, request_hash)
    if action_request is None:
        return None
    return ChatGPTSavingGoalResult(status="already_processed", saving_goal=_owned_resource(db, SavingGoal, action_request.resource_id, user_id, "saving goal"))


@router.post(
    "/saving-goals",
    response_model=ChatGPTSavingGoalResult,
    operation_id="createSavingGoal",
    summary="Crear una meta de ahorro",
    description="Crea una meta de ahorro confirmada.",
    openapi_extra=WRITE_ACTION,
)
def create_saving_goal_action(
    payload: ChatGPTSavingGoalCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("saving_goals:write")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_saving_goal_result(db, user_id, "createSavingGoal", payload.idempotency_key, request_hash)
    if existing is not None:
        return existing
    try:
        goal = create_chatgpt_saving_goal(db, user_id, payload)
        record_action_request(db, user_id=user_id, integration_token_id=principal.token.id, operation="createSavingGoal", idempotency_key=payload.idempotency_key, request_hash=request_hash, resource_id=goal.id)
        db.commit()
        db.refresh(goal)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise _not_found(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_saving_goal_result(db, user_id, "createSavingGoal", payload.idempotency_key, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The saving goal could not be created") from exc
    return ChatGPTSavingGoalResult(status="created", saving_goal=goal)
@router.post(
    "/saving-goal-progress",
    response_model=ChatGPTSavingGoalResult,
    operation_id="updateSavingGoalProgress",
    summary="Actualizar avance de una meta",
    description="Establece el avance absoluto cuando coincide el valor anterior.",
    openapi_extra=WRITE_ACTION,
)
def update_saving_goal_progress_action(
    payload: ChatGPTSavingGoalProgressUpdate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("saving_goals:write")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_saving_goal_result(db, user_id, "updateSavingGoalProgress", payload.idempotency_key, request_hash)
    if existing is not None:
        return existing
    try:
        goal = update_chatgpt_saving_goal_progress(db, user_id, payload)
        record_action_request(db, user_id=user_id, integration_token_id=principal.token.id, operation="updateSavingGoalProgress", idempotency_key=payload.idempotency_key, request_hash=request_hash, resource_id=goal.id)
        db.commit()
        db.refresh(goal)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise _not_found(str(exc)) from exc
    except ActionConflictError as exc:
        db.rollback()
        raise _conflict(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_saving_goal_result(db, user_id, "updateSavingGoalProgress", payload.idempotency_key, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The saving goal could not be updated") from exc
    return ChatGPTSavingGoalResult(status="updated", saving_goal=goal)


def _existing_investment_result(db: Session, user_id, operation: str, idempotency_key: str, request_hash: str) -> ChatGPTInvestmentResult | None:
    action_request = _existing_action_request(db, user_id, operation, idempotency_key, request_hash)
    if action_request is None:
        return None
    return ChatGPTInvestmentResult(status="already_processed", investment=_owned_resource(db, Investment, action_request.resource_id, user_id, "investment"))


@router.post(
    "/investments",
    response_model=ChatGPTInvestmentResult,
    operation_id="createInvestment",
    summary="Crear una inversión",
    description="Crea una inversión confirmada con su valuación actual.",
    openapi_extra=WRITE_ACTION,
)
def create_investment_action(
    payload: ChatGPTInvestmentCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("investments:write")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_investment_result(db, user_id, "createInvestment", payload.idempotency_key, request_hash)
    if existing is not None:
        return existing
    try:
        investment = create_chatgpt_investment(db, user_id, payload)
        record_action_request(db, user_id=user_id, integration_token_id=principal.token.id, operation="createInvestment", idempotency_key=payload.idempotency_key, request_hash=request_hash, resource_id=investment.id)
        db.commit()
        db.refresh(investment)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise _not_found(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_investment_result(db, user_id, "createInvestment", payload.idempotency_key, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The investment could not be created") from exc
    return ChatGPTInvestmentResult(status="created", investment=investment)


@router.post(
    "/investment-valuations",
    response_model=ChatGPTInvestmentResult,
    operation_id="updateInvestmentValue",
    summary="Actualizar valuación de una inversión",
    description="Actualiza la valuación cuando coincide el valor anterior.",
    openapi_extra=WRITE_ACTION,
)
def update_investment_value_action(
    payload: ChatGPTInvestmentValueUpdate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("investments:write")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_investment_result(db, user_id, "updateInvestmentValue", payload.idempotency_key, request_hash)
    if existing is not None:
        return existing
    try:
        investment = update_chatgpt_investment_value(db, user_id, payload)
        record_action_request(db, user_id=user_id, integration_token_id=principal.token.id, operation="updateInvestmentValue", idempotency_key=payload.idempotency_key, request_hash=request_hash, resource_id=investment.id)
        db.commit()
        db.refresh(investment)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise _not_found(str(exc)) from exc
    except ActionConflictError as exc:
        db.rollback()
        raise _conflict(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_investment_result(db, user_id, "updateInvestmentValue", payload.idempotency_key, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The investment could not be updated") from exc
    return ChatGPTInvestmentResult(status="updated", investment=investment)
def _existing_installment_payment_result(db: Session, user_id, payload: ChatGPTInstallmentPaymentCreate, request_hash: str) -> ChatGPTInstallmentPaymentResult | None:
    action_request = _existing_action_request(db, user_id, "markInstallmentPaid", payload.idempotency_key, request_hash)
    if action_request is None:
        return None
    return ChatGPTInstallmentPaymentResult(status="already_processed", installment=_owned_resource(db, Installment, action_request.resource_id, user_id, "installment"))


@router.post(
    "/installment-payments",
    response_model=ChatGPTInstallmentPaymentResult,
    operation_id="markInstallmentPaid",
    summary="Marcar una cuota como pagada",
    description="Registra el pago confirmado de una cuota desde una cuenta compatible.",
    openapi_extra=WRITE_ACTION,
)
def mark_installment_paid_action(
    payload: ChatGPTInstallmentPaymentCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("installments:pay")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_installment_payment_result(db, user_id, payload, request_hash)
    if existing is not None:
        return existing
    try:
        installment, action_status = mark_chatgpt_installment_paid(db, user_id, payload)
        record_action_request(db, user_id=user_id, integration_token_id=principal.token.id, operation="markInstallmentPaid", idempotency_key=payload.idempotency_key, request_hash=request_hash, resource_id=installment.id)
        db.commit()
        db.refresh(installment)
    except OwnedResourceNotFoundError as exc:
        db.rollback()
        raise _not_found(str(exc)) from exc
    except ActionConflictError as exc:
        db.rollback()
        raise _conflict(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_installment_payment_result(db, user_id, payload, request_hash)
        if existing is not None:
            return existing
        raise _conflict("The installment payment could not be recorded") from exc
    return ChatGPTInstallmentPaymentResult(status=action_status, installment=installment)
