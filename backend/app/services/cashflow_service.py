"""
Cashflow projection service.

Computes a month-by-month projection of:
  - Total income (from transactions)
  - Total expenses (from transactions)
  - Total installment charges (from installments table)
  - Net cashflow = income - expenses - installments

Recurring transactions are expanded on-the-fly for projection purposes
(they are NOT stored as future rows in the DB).
"""

import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.installment import Installment
from app.models.transaction import Transaction


def _months_range(start: date, num_months: int) -> list[tuple[int, int]]:
    """Return a list of (year, month) tuples starting from the given date."""
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
    """
    Return a list of monthly projection dictionaries for `num_months` starting
    from `start_date`.

    Each dict has:
      month         : "YYYY-MM"
      total_income  : Decimal
      total_expenses: Decimal
      total_installments: Decimal
      net           : Decimal
    """
    months = _months_range(start_date, num_months)

    # Load all non-paid installments whose due_date falls in our window
    first_month_start = date(months[0][0], months[0][1], 1)
    last_year, last_month = months[-1]
    last_month_end = date(last_year, last_month, _last_day(last_year, last_month))

    installments_q = db.query(Installment).filter(
        Installment.due_date >= first_month_start,
        Installment.due_date <= last_month_end,
        Installment.is_paid == False,  # noqa: E712
    )
    if user_id:
        installments_q = installments_q.filter(Installment.user_id == user_id)
    installments = installments_q.all()

    # Load all transactions in the window
    transactions_q = db.query(Transaction).filter(
        Transaction.date >= first_month_start,
        Transaction.date <= last_month_end,
    )
    if user_id:
        transactions_q = transactions_q.filter(Transaction.user_id == user_id)
    transactions = transactions_q.all()

    # Load recurring transactions (they repeat every month)
    recurring_q = db.query(Transaction).filter(
        Transaction.is_recurring == True, Transaction.recurrence_rule == "monthly"  # noqa: E712
    )
    if user_id:
        recurring_q = recurring_q.filter(Transaction.user_id == user_id)
    recurring = recurring_q.all()

    projection = []

    for year, month in months:
        month_start = date(year, month, 1)
        month_end = date(year, month, _last_day(year, month))
        month_key = f"{year:04d}-{month:02d}"

        # Income from actual transactions this month
        income = sum(
            Decimal(str(t.amount))
            for t in transactions
            if t.type == "income" and month_start <= t.date <= month_end
        )

        # Recurring income
        income += sum(
            Decimal(str(t.amount))
            for t in recurring
            if t.type == "income"
            and t.date <= month_end
            and (t.end_date is None or t.end_date >= month_start)
        )

        # Expenses from actual transactions this month
        expenses = sum(
            Decimal(str(t.amount))
            for t in transactions
            if t.type == "expense" and month_start <= t.date <= month_end
        )

        # Recurring expenses
        expenses += sum(
            Decimal(str(t.amount))
            for t in recurring
            if t.type == "expense"
            and t.date <= month_end
            and (t.end_date is None or t.end_date >= month_start)
        )

        # Installments due this month
        month_installments = sum(
            Decimal(str(i.amount))
            for i in installments
            if i.due_date.year == year and i.due_date.month == month
        )

        net = income - expenses - month_installments

        projection.append(
            {
                "month": month_key,
                "total_income": income,
                "total_expenses": expenses,
                "total_installments": month_installments,
                "net": net,
            }
        )

    return projection


def get_month_summary(db: Session, year: int, month: int, user_id: uuid.UUID | None = None) -> dict:
    """Return a cashflow summary for a single month."""
    result = get_monthly_projection(db, start_date=date(year, month, 1), num_months=1, user_id=user_id)
    return result[0] if result else {}
