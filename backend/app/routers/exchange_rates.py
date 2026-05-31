from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.currency import Currency
from app.models.exchange_rate import ExchangeRate
from app.models.user import User
from app.schemas.exchange_rate import ExchangeRateCreate, ExchangeRateQuote, ExchangeRateRead, ExchangeRateUpdate
from app.routers.deps import get_current_active_user
from app.services.exchange_rate_provider import ExchangeRateProviderError, fetch_yahoo_rate
from app.services.exchange_rate_sync import sync_market_rates

router = APIRouter(prefix="/exchange-rates", tags=["Exchange Rates"])


@router.get("/", response_model=list[ExchangeRateRead])
def list_exchange_rates(
    from_currency_id: Optional[str] = Query(default=None),
    to_currency_id: Optional[str] = Query(default=None),
    latest_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(ExchangeRate)
    if from_currency_id:
        query = query.filter(ExchangeRate.from_currency_id == from_currency_id)
    if to_currency_id:
        query = query.filter(ExchangeRate.to_currency_id == to_currency_id)
    rows = query.order_by(ExchangeRate.date.desc(), ExchangeRate.created_at.desc()).all()
    if not latest_only:
        return rows

    latest_by_pair: dict[tuple[str, str], ExchangeRate] = {}
    for row in rows:
        key = (str(row.from_currency_id), str(row.to_currency_id))
        if key not in latest_by_pair:
            latest_by_pair[key] = row
    return list(latest_by_pair.values())


@router.get("/quote", response_model=ExchangeRateQuote)
def quote_exchange_rate(
    from_currency_id: str,
    to_currency_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    source = db.query(Currency).filter(Currency.id == from_currency_id).first()
    target = db.query(Currency).filter(Currency.id == to_currency_id).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="Currency not found")

    try:
        value = fetch_yahoo_rate(source.code, target.code)
    except ExchangeRateProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "from_currency_id": source.id,
        "to_currency_id": target.id,
        "rate": value.quantize(Decimal("0.01")),
        "date": date.today(),
    }


@router.post("/", response_model=ExchangeRateRead, status_code=status.HTTP_201_CREATED)
def create_exchange_rate(
    payload: ExchangeRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    existing = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.from_currency_id == payload.from_currency_id,
            ExchangeRate.to_currency_id == payload.to_currency_id,
            ExchangeRate.date == payload.date,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Exchange rate already exists for this pair and date")

    rate = ExchangeRate(**payload.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.post("/sync", response_model=list[ExchangeRateRead])
def sync_exchange_rates(
    to: str = Query(default="ARS", min_length=3, max_length=10),
    from_codes: str = Query(default="USD"),
    rate_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    synced, errors = sync_market_rates(
        db,
        to_code=to,
        from_codes=[code.strip().upper() for code in from_codes.split(",") if code.strip()],
        rate_date=rate_date,
    )

    if errors and not synced:
        raise HTTPException(status_code=502, detail="; ".join(errors))
    return synced


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
    update_data = payload.model_dump(exclude_none=True)
    next_date = update_data.get("date", rate.date)
    if next_date != rate.date:
        existing = (
            db.query(ExchangeRate)
            .filter(
                ExchangeRate.id != rate.id,
                ExchangeRate.from_currency_id == rate.from_currency_id,
                ExchangeRate.to_currency_id == rate.to_currency_id,
                ExchangeRate.date == next_date,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Exchange rate already exists for this pair and date")

    for field, value in update_data.items():
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
