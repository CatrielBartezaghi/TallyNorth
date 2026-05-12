from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DashboardKpi(BaseModel):
    value: Decimal
    previous_value: Decimal
    change_pct: Decimal | None


class MonthlyFlowPoint(BaseModel):
    month: str
    income: Decimal
    expenses: Decimal
    net: Decimal


class CategoryExpensePoint(BaseModel):
    category: str
    amount: Decimal
    percent: Decimal
    color: str


class AccountBalancePoint(BaseModel):
    account_id: str
    name: str
    type: str
    balance: Decimal
    currency_code: str
    converted_balance: Decimal | None


class UpcomingInstallmentPoint(BaseModel):
    installment_id: str
    description: str
    current_installment: int
    total_installments: int
    due_date: date
    amount: Decimal
    converted_amount: Decimal | None
    card_name: str


class InvestmentPerformancePoint(BaseModel):
    investment_id: str
    name: str
    type: str
    invested_amount: Decimal
    current_value: Decimal
    gain: Decimal
    return_pct: Decimal
    converted_current_value: Decimal | None


class RecentMovementPoint(BaseModel):
    id: str
    type: str
    description: str
    category: str | None
    account: str | None
    date: date
    amount: Decimal
    converted_amount: Decimal | None


class BudgetVsActualPoint(BaseModel):
    budget_id: str
    category: str
    budget_amount: Decimal
    actual_amount: Decimal
    percent_used: Decimal
    color: str


class SavingGoalPoint(BaseModel):
    goal_id: str
    name: str
    current_amount: Decimal
    target_amount: Decimal
    progress_pct: Decimal
    target_date: date | None
    color: str
    icon: str | None


class DashboardSummary(BaseModel):
    currency: str
    date_from: date
    date_to: date
    warnings: list[str]
    kpis: dict[str, DashboardKpi]
    monthly_flow: list[MonthlyFlowPoint]
    expenses_by_category: list[CategoryExpensePoint]
    account_balances: list[AccountBalancePoint]
    upcoming_installments: list[UpcomingInstallmentPoint]
    investments: list[InvestmentPerformancePoint]
    recent_movements: list[RecentMovementPoint]
    budgets: list[BudgetVsActualPoint]
    saving_goals: list[SavingGoalPoint]
