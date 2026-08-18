"""Cashflow projection service."""

import calendar
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.installment import Installment
from app.models.recurring_entry import RecurringEntry
from app.models.transaction import Transaction
from app.services.recurring_entry_service import occurrence_dates_between, projected_card_due_date


def _months_range(start: date, num_months: int) -> list[tuple[int, int]]:
    result = []
    year, month = start.year, start.month
    for _ in range(num_months):
        result.append((year, month))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return result


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def get_monthly_projection(
    db: Session,
    start_date: date,
    num_months: int = 6,
    user_id: uuid.UUID | None = None,
) -> list[dict]:
    months = _months_range(start_date, num_months)
    first_month_start = date(months[0][0], months[0][1], 1)
    last_year, last_month = months[-1]
    last_month_end = date(last_year, last_month, _last_day(last_year, last_month))

    installments_q = db.query(Installment).filter(
        Installment.due_date >= first_month_start,
        Installment.due_date <= last_month_end,
        Installment.is_paid.is_(False),
    )
    if user_id:
        installments_q = installments_q.filter(Installment.user_id == user_id)
    installments = installments_q.all()

    transactions_q = db.query(Transaction).filter(
        Transaction.date >= first_month_start,
        Transaction.date <= last_month_end,
    )
    if user_id:
        transactions_q = transactions_q.filter(Transaction.user_id == user_id)
    transactions = transactions_q.all()

    recurring_q = db.query(RecurringEntry).options(
        joinedload(RecurringEntry.credit_card),
        joinedload(RecurringEntry.account),
    ).filter(RecurringEntry.active.is_(True))
    if user_id:
        recurring_q = recurring_q.filter(RecurringEntry.user_id == user_id)
    recurring_entries = recurring_q.all()

    # Today and past occurrences are already materialized as transactions or
    # purchases. Only future occurrences are projected from the recurring rule.
    future_from = max(first_month_start, date.today() + timedelta(days=1))
    projected_account_occurrences: list[tuple[RecurringEntry, date]] = []
    projected_card_installments: list[tuple[RecurringEntry, date]] = []
    if future_from <= last_month_end:
        for entry in recurring_entries:
            for occurrence_date in occurrence_dates_between(entry, future_from, last_month_end):
                if entry.destination_type == "account":
                    projected_account_occurrences.append((entry, occurrence_date))
                else:
                    due_date = projected_card_due_date(entry, occurrence_date)
                    if first_month_start <= due_date <= last_month_end:
                        projected_card_installments.append((entry, due_date))

    projection = []
    for year, month in months:
        month_start = date(year, month, 1)
        month_end = date(year, month, _last_day(year, month))
        month_key = f"{year:04d}-{month:02d}"

        income = sum(
            Decimal(str(t.amount))
            for t in transactions
            if t.type == "income" and month_start <= t.date <= month_end
        )
        expenses = sum(
            Decimal(str(t.amount))
            for t in transactions
            if t.type == "expense" and month_start <= t.date <= month_end
        )

        income += sum(
            Decimal(str(entry.amount))
            for entry, occurrence_date in projected_account_occurrences
            if entry.type == "income" and month_start <= occurrence_date <= month_end
        )
        expenses += sum(
            Decimal(str(entry.amount))
            for entry, occurrence_date in projected_account_occurrences
            if entry.type == "expense" and month_start <= occurrence_date <= month_end
        )

        month_installments = sum(
            Decimal(str(i.amount))
            for i in installments
            if i.due_date.year == year and i.due_date.month == month
        )
        month_installments += sum(
            Decimal(str(entry.amount))
            for entry, due_date in projected_card_installments
            if month_start <= due_date <= month_end
        )

        projection.append(
            {
                "month": month_key,
                "total_income": income,
                "total_expenses": expenses,
                "total_installments": month_installments,
                "net": income - expenses - month_installments,
            }
        )

    return projection


def get_month_summary(
    db: Session,
    year: int,
    month: int,
    user_id: uuid.UUID | None = None,
) -> dict:
    result = get_monthly_projection(
        db,
        start_date=date(year, month, 1),
        num_months=1,
        user_id=user_id,
    )
    return result[0] if result else {}
