from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.exchange_rate import ExchangeRate
from app.models.user import User
from app.schemas.exchange_rate import ExchangeRateCreate, ExchangeRateRead, ExchangeRateUpdate
from app.routers.deps import get_current_active_user

router = APIRouter(prefix="/exchange-rates", tags=["Exchange Rates"])


@router.get("/", response_model=list[ExchangeRateRead])
def list_exchange_rates(
    from_currency_id: Optional[str] = Query(default=None),
    to_currency_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(ExchangeRate)
    if from_currency_id:
        query = query.filter(ExchangeRate.from_currency_id == from_currency_id)
    if to_currency_id:
        query = query.filter(ExchangeRate.to_currency_id == to_currency_id)
    return query.order_by(ExchangeRate.date.desc()).all()


@router.post("/", response_model=ExchangeRateRead, status_code=status.HTTP_201_CREATED)
def create_exchange_rate(
    payload: ExchangeRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rate = ExchangeRate(**payload.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.get("/{rate_id}", response_model=ExchangeRateRead)
def get_exchange_rate(
    rate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rate = db.query(ExchangeRate).filter(ExchangeRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Exchange rate not found")
    return rate


@router.put("/{rate_id}", response_model=ExchangeRateRead)
def update_exchange_rate(
    rate_id: str,
    payload: ExchangeRateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rate = db.query(ExchangeRate).filter(ExchangeRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Exchange rate not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(rate, field, value)
    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exchange_rate(
    rate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rate = db.query(ExchangeRate).filter(ExchangeRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Exchange rate not found")
    db.delete(rate)
    db.commit()
