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
    rate = ExchangeRate(**payload.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.post("/sync", response_model=list[ExchangeRateRead])
def sync_exchange_rates(
    to: str = Query(default="ARS", min_length=3, max_length=10),
    from_codes: str = Query(default="USD,EUR,BTC"),
    rate_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    target = db.query(Currency).filter(Currency.code == to.upper()).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"Currency '{to.upper()}' not found")

    synced: list[ExchangeRate] = []
    errors: list[str] = []
    codes = [code.strip().upper() for code in from_codes.split(",") if code.strip()]

    for code in codes:
        source = db.query(Currency).filter(Currency.code == code).first()
        if not source:
            errors.append(f"Currency '{code}' not found")
            continue
        if source.id == target.id:
            continue

        try:
            value = fetch_yahoo_rate(source.code, target.code)
        except ExchangeRateProviderError as exc:
            errors.append(str(exc))
            continue

        rate = (
            db.query(ExchangeRate)
            .filter(
                ExchangeRate.from_currency_id == source.id,
                ExchangeRate.to_currency_id == target.id,
                ExchangeRate.date == rate_date,
            )
            .first()
        )
        if rate:
            rate.rate = value.quantize(Decimal("0.01"))
        else:
            rate = ExchangeRate(
                from_currency_id=source.id,
                to_currency_id=target.id,
                rate=value.quantize(Decimal("0.01")),
                date=rate_date,
            )
            db.add(rate)
        synced.append(rate)

    if errors and not synced:
        raise HTTPException(status_code=502, detail="; ".join(errors))

    db.commit()
    for rate in synced:
        db.refresh(rate)
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
