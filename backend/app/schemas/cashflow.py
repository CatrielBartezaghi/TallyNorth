from decimal import Decimal

from pydantic import BaseModel


class MonthlyProjection(BaseModel):
    """Projected cashflow for one calendar month."""
    month: str  # "YYYY-MM"
    total_income: Decimal
    total_expenses: Decimal
    total_installments: Decimal
    net: Decimal  # income - expenses - installments


class DashboardSummary(BaseModel):
    """Aggregated data for the dashboard."""
    current_month: str  # "YYYY-MM"
    total_income_mtd: Decimal
    total_expenses_mtd: Decimal
    total_installments_mtd: Decimal
    net_mtd: Decimal
    upcoming_installments: list[dict]  # next 3 months installments per card
    projection: list[MonthlyProjection]  # next N months
