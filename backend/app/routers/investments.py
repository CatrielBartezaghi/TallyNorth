from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.investment import Investment, InvestmentOperation, InvestmentValuation
from app.models.user import User
from app.schemas.investment import (
    InvestmentCreate,
    InvestmentOperationCreate,
    InvestmentOperationRead,
    InvestmentRead,
    InvestmentUpdate,
    InvestmentValuationCreate,
    InvestmentValuationRead,
)
from app.routers.deps import get_current_active_user
from app.services.investment_service import create_operation, get_owned_investment, record_valuation


router = APIRouter(prefix="/investments", tags=["Investments"])


@router.get("/", response_model=list[InvestmentRead])
def list_investments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return (
        db.query(Investment)
        .filter(Investment.user_id == current_user.id)
        .order_by(Investment.created_at.desc())
        .all()
    )


@router.post("/", response_model=InvestmentRead, status_code=status.HTTP_201_CREATED)
def create_investment(
    payload: InvestmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data = payload.model_dump(exclude={"invested_amount", "current_value", "opening_quantity"})
    investment = Investment(
        **data,
        user_id=current_user.id,
        invested_amount=0,
        current_value=0,
    )
    db.add(investment)
    db.flush()

    if payload.invested_amount > 0:
        create_operation(
            db,
            user_id=current_user.id,
            investment=investment,
            payload=InvestmentOperationCreate(
                type="opening",
                quantity=payload.opening_quantity,
                unit_price=(
                    payload.invested_amount / payload.opening_quantity
                    if payload.opening_quantity is not None
                    else None
                ),
                amount=payload.invested_amount,
                date=date.today(),
                notes="Opening position",
            ),
        )
    if payload.current_value > 0 or payload.invested_amount > 0:
        initial_value = payload.current_value if payload.current_value > 0 else payload.invested_amount
        record_valuation(
            db,
            user_id=current_user.id,
            investment=investment,
            payload=InvestmentValuationCreate(
                value=initial_value,
                valuation_date=date.today(),
                source="manual",
                notes="Initial valuation",
            ),
        )

    db.commit()
    db.refresh(investment)
    return investment


@router.get("/{investment_id}", response_model=InvestmentRead)
def get_investment(
    investment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        return get_owned_investment(db, current_user.id, investment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{investment_id}", response_model=InvestmentRead)
def update_investment(
    investment_id: str,
    payload: InvestmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        investment = get_owned_investment(db, current_user.id, investment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(investment, field, value)
    db.commit()
    db.refresh(investment)
    return investment


@router.delete("/{investment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investment(
    investment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        investment = get_owned_investment(db, current_user.id, investment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.delete(investment)
    db.commit()


@router.get("/{investment_id}/operations", response_model=list[InvestmentOperationRead])
def list_operations(
    investment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        investment = get_owned_investment(db, current_user.id, investment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return (
        db.query(InvestmentOperation)
        .filter(InvestmentOperation.investment_id == investment.id)
        .order_by(InvestmentOperation.date.desc(), InvestmentOperation.created_at.desc())
        .all()
    )


@router.post(
    "/{investment_id}/operations",
    response_model=InvestmentOperationRead,
    status_code=status.HTTP_201_CREATED,
)
def add_operation(
    investment_id: str,
    payload: InvestmentOperationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        investment = get_owned_investment(db, current_user.id, investment_id)
        operation = create_operation(
            db,
            user_id=current_user.id,
            investment=investment,
            payload=payload,
        )
        db.commit()
        db.refresh(operation)
        return operation
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{investment_id}/valuations", response_model=list[InvestmentValuationRead])
def list_valuations(
    investment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        investment = get_owned_investment(db, current_user.id, investment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return (
        db.query(InvestmentValuation)
        .filter(InvestmentValuation.investment_id == investment.id)
        .order_by(InvestmentValuation.valuation_date.desc(), InvestmentValuation.created_at.desc())
        .all()
    )


@router.post(
    "/{investment_id}/valuations",
    response_model=InvestmentValuationRead,
    status_code=status.HTTP_201_CREATED,
)
def add_valuation(
    investment_id: str,
    payload: InvestmentValuationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        investment = get_owned_investment(db, current_user.id, investment_id)
        valuation = record_valuation(
            db,
            user_id=current_user.id,
            investment=investment,
            payload=payload,
        )
        db.commit()
        db.refresh(valuation)
        return valuation
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
