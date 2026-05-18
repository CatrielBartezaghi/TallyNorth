from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta

from app.config import settings
from app.database import SessionLocal
from app.services.exchange_rate_sync import sync_market_rates


def _next_run(now: datetime, hours: list[int]) -> datetime:
    for hour in sorted(hours):
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate
    return (now + timedelta(days=1)).replace(hour=sorted(hours)[0], minute=0, second=0, microsecond=0)


async def run_exchange_rate_cron() -> None:
    hours = sorted({int(hour.strip()) for hour in settings.exchange_rate_cron_hours.split(",") if hour.strip()})
    if not hours:
        hours = [0, 8, 16]

    while True:
        now = datetime.now()
        next_run = _next_run(now, hours)
        await asyncio.sleep((next_run - now).total_seconds())

        db = SessionLocal()
        try:
            sync_market_rates(
                db,
                to_code=settings.exchange_rate_sync_to,
                from_codes=[code.strip().upper() for code in settings.exchange_rate_sync_from.split(",") if code.strip()],
            )
        except Exception:
            db.rollback()
        finally:
            db.close()


def start_exchange_rate_cron() -> asyncio.Task | None:
    if not settings.exchange_rate_cron_enabled:
        return None
    return asyncio.create_task(run_exchange_rate_cron())


async def stop_exchange_rate_cron(task: asyncio.Task | None) -> None:
    if not task:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
