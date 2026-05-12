"""
Installment generation service.

Business rules (Argentine credit card convention):
- If the purchase_date is ON or BEFORE the closing_day of the current month,
  the first installment appears on the CURRENT billing period (due on due_day of that month).
- If the purchase_date is AFTER the closing_day, the first installment is pushed to the
  NEXT billing period (due on due_day of the following month).

Example:
  closing_day = 5, due_day = 20, purchase_date = 2026-05-03 → first installment due 2026-05-20
  closing_day = 5, due_day = 20, purchase_date = 2026-05-10 → first installment due 2026-06-20
"""

import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def compute_first_installment_date(
    purchase_date: date,
    closing_day: int,
    due_day: int,
) -> date:
    """
    Return the due_date of the first installment based on card closing/due rules.
    """
    if purchase_date.day <= closing_day:
        # Same billing period
        target_month = purchase_date.month
        target_year = purchase_date.year
    else:
        # Next billing period
        if purchase_date.month == 12:
            target_month = 1
            target_year = purchase_date.year + 1
        else:
            target_month = purchase_date.month + 1
            target_year = purchase_date.year

    # Clamp due_day to actual days in month (e.g. due_day=31 in April → 30)
    max_day = calendar.monthrange(target_year, target_month)[1]
    clamped_due_day = min(due_day, max_day)
    return date(target_year, target_month, clamped_due_day)


def _advance_one_month(d: date, due_day: int) -> date:
    """Move forward exactly one month, clamping to last day if needed."""
    if d.month == 12:
        year, month = d.year + 1, 1
    else:
        year, month = d.year, d.month + 1

    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(due_day, max_day))


def generate_installment_dates(
    first_installment_date: date,
    num_installments: int,
    due_day: int,
) -> list[date]:
    """
    Return a list of `num_installments` due dates starting from `first_installment_date`,
    advancing one calendar month per installment.
    """
    dates: list[date] = [first_installment_date]
    current = first_installment_date
    for _ in range(num_installments - 1):
        current = _advance_one_month(current, due_day)
        dates.append(current)
    return dates


def compute_installment_amount(total_amount: Decimal, num_installments: int) -> Decimal:
    """
    Divide total_amount evenly. Uses ROUND_HALF_UP to 2 decimal places.
    Any rounding difference is ignored at MVP stage.
    """
    per_installment = (total_amount / num_installments).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return per_installment
