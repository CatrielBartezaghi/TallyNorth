from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account import Account
from app.models.investment import Investment, InvestmentOperation, InvestmentValuation
from app.models.saving_goal import SavingGoal, SavingGoalAllocation
from app.routers.chatgpt_actions import READ_ACTION, WRITE_ACTION, require_integration_scope
from app.schemas.chatgpt_investment import (
    ChatGPTInvestmentAssetCreate,
    ChatGPTInvestmentAssetResult,
    ChatGPTInvestmentOperationCreate,
    ChatGPTInvestmentOperationResult,
    ChatGPTInvestmentValuationCreate,
    ChatGPTInvestmentValuationResult,
    ChatGPTSavingGoalAllocationCreate,
    ChatGPTSavingGoalAllocationResult,
    ChatGPTSavingGoalWithAllocations,
)
from app.schemas.investment import (
    InvestmentOperationCreate,
    InvestmentOperationRead,
    InvestmentRead,
    InvestmentValuationCreate,
)
from app.services.gpt_action_idempotency import action_request_hash, find_action_request, record_action_request
from app.services.integration_tokens import IntegrationPrincipal
from app.services.investment_service import create_operation, get_owned_investment, record_valuation


router = APIRouter(prefix="/integrations/chatgpt", tags=["ChatGPT Investment Actions"])


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": "action_conflict", "message": message})


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": "validation_error", "message": message})


def _existing_resource(db: Session, *, user_id, operation: str, idempotency_key: str, request_hash: str, model):
    request = find_action_request(db, user_id, operation, idempotency_key)
    if request is None:
        return None
    if request.request_hash != request_hash:
        raise _conflict("This idempotency key was already used with different data")
    resource = db.query(model).filter(model.id == request.resource_id, model.user_id == user_id).first()
    if resource is None:
        raise _conflict("The original action exists but its resource is no longer available")
    return resource


@router.get(
    "/investment-portfolio",
    response_model=list[InvestmentRead],
    operation_id="listInvestments",
    summary="Listar cartera de inversiones",
    description="Devuelve las posiciones actuales con costo, valuación, cantidad y resultado realizado.",
    openapi_extra=READ_ACTION,
)
def list_investments_action(
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("context:read")),
):
    return (
        db.query(Investment)
        .filter(Investment.user_id == principal.user.id)
        .order_by(Investment.created_at.desc())
        .all()
    )


@router.get(
    "/investment-operations",
    response_model=list[InvestmentOperationRead],
    operation_id="listInvestmentOperations",
    summary="Listar operaciones de inversión",
    description="Lista compras, ventas, dividendos, intereses, comisiones y saldos iniciales de una inversión.",
    openapi_extra=READ_ACTION,
)
def list_investment_operations_action(
    investment_id: str,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("context:read")),
):
    try:
        investment = get_owned_investment(db, principal.user.id, investment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": str(exc)}) from exc
    return (
        db.query(InvestmentOperation)
        .filter(InvestmentOperation.investment_id == investment.id)
        .order_by(InvestmentOperation.date.desc(), InvestmentOperation.created_at.desc())
        .all()
    )


@router.get(
    "/saving-goals",
    response_model=list[ChatGPTSavingGoalWithAllocations],
    operation_id="listSavingGoals",
    summary="Listar objetivos de ahorro",
    description="Devuelve las metas y las cuentas o inversiones asignadas a cada una.",
    openapi_extra=READ_ACTION,
)
def list_saving_goals_action(
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("context:read")),
):
    goals = (
        db.query(SavingGoal)
        .filter(SavingGoal.user_id == principal.user.id)
        .order_by(SavingGoal.created_at.desc())
        .all()
    )
    return [
        ChatGPTSavingGoalWithAllocations(
            goal=goal,
            allocations=(
                db.query(SavingGoalAllocation)
                .filter(SavingGoalAllocation.saving_goal_id == goal.id)
                .order_by(SavingGoalAllocation.created_at.asc())
                .all()
            ),
        )
        for goal in goals
    ]


@router.post(
    "/investment-assets",
    response_model=ChatGPTInvestmentAssetResult,
    operation_id="createInvestmentAsset",
    summary="Crear activo de inversión",
    description="Crea una posición. Puede registrar un saldo inicial y una valuación inicial para activos ya existentes.",
    openapi_extra=WRITE_ACTION,
)
def create_investment_asset_action(
    payload: ChatGPTInvestmentAssetCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("investments:write")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_resource(
        db, user_id=user_id, operation="createInvestmentAsset",
        idempotency_key=payload.idempotency_key, request_hash=request_hash, model=Investment,
    )
    if existing is not None:
        return ChatGPTInvestmentAssetResult(status="already_processed", investment=existing)

    investment = Investment(
        user_id=user_id,
        name=payload.name,
        symbol=payload.symbol,
        broker=payload.broker,
        type=payload.type,
        currency_id=payload.currency_id,
        invested_amount=0,
        current_value=0,
        expected_return_rate=payload.expected_return_rate,
        notes=payload.notes,
    )
    db.add(investment)
    try:
        db.flush()
        opening_date = payload.opening_date or date.today()
        if payload.opening_invested_amount > 0:
            create_operation(
                db,
                user_id=user_id,
                investment=investment,
                payload=InvestmentOperationCreate(
                    type="opening",
                    amount=payload.opening_invested_amount,
                    date=opening_date,
                    notes="Opening position registered from ChatGPT",
                ),
            )
        if payload.opening_current_value > 0 or payload.opening_invested_amount > 0:
            initial_value = (
                payload.opening_current_value
                if payload.opening_current_value > 0
                else payload.opening_invested_amount
            )
            record_valuation(
                db,
                user_id=user_id,
                investment=investment,
                payload=InvestmentValuationCreate(
                    value=initial_value,
                    valuation_date=opening_date,
                    source="chatgpt",
                    notes="Initial valuation",
                ),
            )
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="createInvestmentAsset",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=investment.id,
        )
        db.commit()
        db.refresh(investment)
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        if isinstance(exc, ValueError):
            raise _unprocessable(str(exc)) from exc
        raise _conflict("The investment could not be created") from exc
    return ChatGPTInvestmentAssetResult(status="created", investment=investment)


@router.post(
    "/investment-operations",
    response_model=ChatGPTInvestmentOperationResult,
    operation_id="createInvestmentOperation",
    summary="Registrar operación de inversión",
    description="Registra una compra, venta, dividendo, interés o comisión. Las compras/ventas mueven la cuenta vinculada sin contarse como gasto/ingreso.",
    openapi_extra=WRITE_ACTION,
)
def create_investment_operation_action(
    payload: ChatGPTInvestmentOperationCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("investments:write")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_resource(
        db, user_id=user_id, operation="createInvestmentOperation",
        idempotency_key=payload.idempotency_key, request_hash=request_hash, model=InvestmentOperation,
    )
    if existing is not None:
        investment = get_owned_investment(db, user_id, existing.investment_id)
        return ChatGPTInvestmentOperationResult(status="already_processed", operation=existing, investment=investment)

    try:
        investment = get_owned_investment(db, user_id, payload.investment_id)
        operation = create_operation(
            db,
            user_id=user_id,
            investment=investment,
            payload=InvestmentOperationCreate(
                type=payload.type,
                account_id=payload.account_id,
                quantity=payload.quantity,
                unit_price=payload.unit_price,
                amount=payload.amount,
                fee=payload.fee,
                date=payload.date,
                notes=payload.notes,
            ),
        )
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="createInvestmentOperation",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=operation.id,
        )
        db.commit()
        db.refresh(operation)
        db.refresh(investment)
    except ValueError as exc:
        db.rollback()
        raise _unprocessable(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise _conflict("The investment operation could not be recorded") from exc
    return ChatGPTInvestmentOperationResult(status="created", operation=operation, investment=investment)


@router.post(
    "/investment-valuation-records",
    response_model=ChatGPTInvestmentValuationResult,
    operation_id="recordInvestmentValuation",
    summary="Registrar valuación de inversión",
    description="Agrega una valuación histórica sin destruir las anteriores y actualiza el valor vigente de la posición.",
    openapi_extra=WRITE_ACTION,
)
def record_investment_valuation_action(
    payload: ChatGPTInvestmentValuationCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("investments:write")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_resource(
        db, user_id=user_id, operation="recordInvestmentValuation",
        idempotency_key=payload.idempotency_key, request_hash=request_hash, model=InvestmentValuation,
    )
    if existing is not None:
        investment = get_owned_investment(db, user_id, existing.investment_id)
        return ChatGPTInvestmentValuationResult(status="already_processed", valuation=existing, investment=investment)

    try:
        investment = get_owned_investment(db, user_id, payload.investment_id)
        valuation = record_valuation(
            db,
            user_id=user_id,
            investment=investment,
            payload=InvestmentValuationCreate(
                value=payload.value,
                valuation_date=payload.valuation_date,
                source=payload.source,
                notes=payload.notes,
            ),
        )
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="recordInvestmentValuation",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=valuation.id,
        )
        db.commit()
        db.refresh(valuation)
        db.refresh(investment)
    except ValueError as exc:
        db.rollback()
        raise _unprocessable(str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise _conflict("The investment valuation could not be recorded") from exc
    return ChatGPTInvestmentValuationResult(status="created", valuation=valuation, investment=investment)


@router.post(
    "/saving-goal-allocations",
    response_model=ChatGPTSavingGoalAllocationResult,
    operation_id="allocateSavingGoal",
    summary="Asignar patrimonio a un objetivo",
    description="Asigna un porcentaje de una cuenta o inversión a una meta sin sumar ese dinero nuevamente al patrimonio.",
    openapi_extra=WRITE_ACTION,
)
def allocate_saving_goal_action(
    payload: ChatGPTSavingGoalAllocationCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(require_integration_scope("saving_goals:write")),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing = _existing_resource(
        db, user_id=user_id, operation="allocateSavingGoal",
        idempotency_key=payload.idempotency_key, request_hash=request_hash, model=SavingGoalAllocation,
    )
    if existing is not None:
        return ChatGPTSavingGoalAllocationResult(status="already_processed", allocation=existing)

    goal = db.query(SavingGoal).filter(SavingGoal.id == payload.saving_goal_id, SavingGoal.user_id == user_id).first()
    if goal is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Saving goal not found"})

    if payload.account_id is not None:
        source = db.query(Account).filter(Account.id == payload.account_id, Account.user_id == user_id).first()
        source_field = SavingGoalAllocation.account_id
        source_id = payload.account_id
    else:
        source = db.query(Investment).filter(Investment.id == payload.investment_id, Investment.user_id == user_id).first()
        source_field = SavingGoalAllocation.investment_id
        source_id = payload.investment_id
    if source is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Allocation source not found"})

    allocated = sum(
        (Decimal(str(row.allocation_percent)) for row in db.query(SavingGoalAllocation).filter(
            SavingGoalAllocation.user_id == user_id,
            source_field == source_id,
        ).all()),
        Decimal("0"),
    )
    if allocated + payload.allocation_percent > 100:
        raise _unprocessable("This source would be allocated above 100% across goals")

    allocation = SavingGoalAllocation(
        user_id=user_id,
        saving_goal_id=goal.id,
        account_id=payload.account_id,
        investment_id=payload.investment_id,
        allocation_percent=payload.allocation_percent,
    )
    db.add(allocation)
    try:
        db.flush()
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="allocateSavingGoal",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=allocation.id,
        )
        db.commit()
        db.refresh(allocation)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict("The saving goal allocation could not be created") from exc
    return ChatGPTSavingGoalAllocationResult(status="created", allocation=allocation)
