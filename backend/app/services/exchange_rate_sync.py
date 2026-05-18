from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.currency import Currency
from app.models.exchange_rate import ExchangeRate
from app.services.exchange_rate_provider import ExchangeRateProviderError, fetch_yahoo_rate


def sync_market_rates(
    db: Session,
    to_code: str = "ARS",
    from_codes: list[str] | None = None,
    rate_date: date | None = None,
) -> tuple[list[ExchangeRate], list[str]]:
    target = db.query(Currency).filter(Currency.code == to_code.upper()).first()
    if not target:
        return [], [f"Currency '{to_code.upper()}' not found"]

    synced: list[ExchangeRate] = []
    errors: list[str] = []
    codes = from_codes or ["USD", "EUR", "BTC"]
    current_date = rate_date or date.today()

    for code in [item.strip().upper() for item in codes if item.strip()]:
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
                ExchangeRate.date == current_date,
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
                date=current_date,
            )
            db.add(rate)
        synced.append(rate)

    db.commit()
    for rate in synced:
        db.refresh(rate)
    return synced, errors
