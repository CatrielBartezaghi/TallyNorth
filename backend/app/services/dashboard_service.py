import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session, joinedload

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.currency import Currency
from app.models.exchange_rate import ExchangeRate
from app.models.installment import Installment
from app.models.investment import Investment, InvestmentOperation
from app.models.purchase import CreditCardPurchase
from app.models.recurring_entry import RecurringEntry
from app.models.saving_goal import SavingGoal, SavingGoalAllocation
from app.models.transaction import Transaction
from app.services.account_balance_service import get_account_current_balance
from app.services.recurring_entry_service import occurrence_dates_between, projected_card_due_date


MONEY = Decimal("0.01")


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _q(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _pct(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return _q(((current - previous) / previous) * Decimal("100"))


def _ratio_pct(value: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return Decimal("0")
    return _q((value / total) * Decimal("100"))


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _month_end(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _months_between(start: date, end: date) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        result.append((y, m))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return result


class Converter:
    def __init__(self, db: Session, target_code: str, as_of: date):
        self.db = db
        self.as_of = as_of
        self.target = db.query(Currency).filter(Currency.code == target_code).first()
        if not self.target:
            raise ValueError(f"Currency {target_code} not found")
        self.warnings: list[str] = []
        self._cache: dict[str, Decimal | None] = {}

    def _latest_rate(self, from_currency_id, to_currency_id) -> Decimal | None:
        rate = (
            self.db.query(ExchangeRate)
            .filter(
                ExchangeRate.from_currency_id == from_currency_id,
                ExchangeRate.to_currency_id == to_currency_id,
                ExchangeRate.date <= self.as_of,
            )
            .order_by(ExchangeRate.date.desc())
            .first()
        )
        return _decimal(rate.rate) if rate else None

    def _conversion_rate(self, currency: Currency) -> Decimal | None:
        direct = self._latest_rate(currency.id, self.target.id)
        if direct is not None:
            return direct

        inverse = self._latest_rate(self.target.id, currency.id)
        if inverse not in (None, Decimal("0")):
            return Decimal("1") / inverse

        ars = self.db.query(Currency).filter(Currency.code == "ARS").first()
        if ars and currency.id != ars.id and self.target.id != ars.id:
            source_to_ars = self._latest_rate(currency.id, ars.id)
            target_to_ars = self._latest_rate(self.target.id, ars.id)
            if source_to_ars is not None and target_to_ars not in (None, Decimal("0")):
                return source_to_ars / target_to_ars

        return None

    def convert(self, amount, currency: Currency | None) -> Decimal | None:
        value = _decimal(amount)
        if not currency or currency.id == self.target.id:
            return _q(value)

        cache_key = str(currency.id)
        if cache_key not in self._cache:
            self._cache[cache_key] = self._conversion_rate(currency)
            if self._cache[cache_key] is None:
                self.warnings.append(f"Missing {currency.code}->{self.target.code} exchange rate")

        rate_value = self._cache[cache_key]
        if rate_value is None:
            return None
        return _q(value * rate_value)


def build_dashboard_summary(
    db: Session,
    date_from: date,
    date_to: date,
    currency_code: str,
    user_id: str,
) -> dict:
    converter = Converter(db, currency_code, date_to)
    prev_days = (date_to - date_from).days + 1
    previous_to = date_from - timedelta(days=1)
    previous_from = previous_to - timedelta(days=prev_days - 1)

    categories = {
        c.id: c for c in db.query(Category).filter(Category.user_id == user_id).all()
    }
    categories_by_name = {c.name.lower(): c for c in categories.values()}

    transactions = (
        db.query(Transaction)
        .options(joinedload(Transaction.account), joinedload(Transaction.category_ref))
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= previous_from,
            Transaction.date <= date_to,
        )
        .all()
    )
    installments = (
        db.query(Installment)
        .options(
            joinedload(Installment.purchase).joinedload(CreditCardPurchase.credit_card),
            joinedload(Installment.purchase).joinedload(CreditCardPurchase.category_ref),
        )
        .filter(
            Installment.user_id == user_id,
            Installment.due_date >= previous_from,
            Installment.due_date <= date_to,
        )
        .all()
    )

    def period_totals(start: date, end: date) -> tuple[Decimal, Decimal]:
        income = Decimal("0")
        expenses = Decimal("0")
        for tx in transactions:
            if start <= tx.date <= end:
                converted = converter.convert(tx.amount, tx.account.currency)
                if converted is None:
                    continue
                if tx.type == "income":
                    income += converted
                else:
                    expenses += converted
        for installment in installments:
            if start <= installment.due_date <= end:
                converted = converter.convert(
                    installment.amount,
                    installment.purchase.credit_card.currency,
                )
                if converted is not None:
                    expenses += converted
        return _q(income), _q(expenses)

    investment_operations = (
        db.query(InvestmentOperation)
        .options(joinedload(InvestmentOperation.investment).joinedload(Investment.currency))
        .filter(
            InvestmentOperation.user_id == user_id,
            InvestmentOperation.date >= previous_from,
            InvestmentOperation.date <= date_to,
        )
        .all()
    )

    def investment_period_totals(start: date, end: date) -> tuple[Decimal, Decimal]:
        investment_income = Decimal("0")
        investment_expenses = Decimal("0")
        for operation in investment_operations:
            if not (start <= operation.date <= end):
                continue
            if operation.type in {"dividend", "interest"}:
                converted = converter.convert(
                    _decimal(operation.amount) - _decimal(operation.fee),
                    operation.investment.currency,
                )
                if converted is not None:
                    investment_income += converted
            elif operation.type == "fee":
                converted = converter.convert(operation.amount, operation.investment.currency)
                if converted is not None:
                    investment_expenses += converted
        return _q(investment_income), _q(investment_expenses)

    income, expenses = period_totals(date_from, date_to)
    inv_income, inv_expenses = investment_period_totals(date_from, date_to)
    income = _q(income + inv_income)
    expenses = _q(expenses + inv_expenses)

    previous_income, previous_expenses = period_totals(previous_from, previous_to)
    prev_inv_income, prev_inv_expenses = investment_period_totals(previous_from, previous_to)
    previous_income = _q(previous_income + prev_inv_income)
    previous_expenses = _q(previous_expenses + prev_inv_expenses)
    net = _q(income - expenses)
    previous_net = _q(previous_income - previous_expenses)

    monthly_map: dict[str, dict[str, Decimal]] = {
        f"{year:04d}-{month:02d}": {
            "income": Decimal("0"),
            "expenses": Decimal("0"),
        }
        for year, month in _months_between(_month_start(date_from), _month_start(date_to))
    }
    for tx in transactions:
        if date_from <= tx.date <= date_to:
            converted = converter.convert(tx.amount, tx.account.currency)
            if converted is None:
                continue
            key = f"{tx.date.year:04d}-{tx.date.month:02d}"
            monthly_map[key]["income" if tx.type == "income" else "expenses"] += converted
    for installment in installments:
        if date_from <= installment.due_date <= date_to:
            converted = converter.convert(
                installment.amount,
                installment.purchase.credit_card.currency,
            )
            if converted is not None:
                key = f"{installment.due_date.year:04d}-{installment.due_date.month:02d}"
                monthly_map[key]["expenses"] += converted
    for operation in investment_operations:
        if not (date_from <= operation.date <= date_to):
            continue
        key = f"{operation.date.year:04d}-{operation.date.month:02d}"
        if operation.type in {"dividend", "interest"}:
            converted = converter.convert(
                _decimal(operation.amount) - _decimal(operation.fee),
                operation.investment.currency,
            )
            if converted is not None:
                monthly_map[key]["income"] += converted
        elif operation.type == "fee":
            converted = converter.convert(operation.amount, operation.investment.currency)
            if converted is not None:
                monthly_map[key]["expenses"] += converted

    future_from = max(date_from, date.today() + timedelta(days=1))
    if future_from <= date_to:
        recurring_entries = (
            db.query(RecurringEntry)
            .options(
                joinedload(RecurringEntry.account).joinedload(Account.currency),
                joinedload(RecurringEntry.credit_card),
            )
            .filter(
                RecurringEntry.user_id == user_id,
                RecurringEntry.active.is_(True),
            )
            .all()
        )
        for entry in recurring_entries:
            for occurrence_date in occurrence_dates_between(entry, future_from, date_to):
                if entry.destination_type == "account":
                    converted = converter.convert(entry.amount, entry.account.currency)
                    if converted is None:
                        continue
                    key = f"{occurrence_date.year:04d}-{occurrence_date.month:02d}"
                    if key in monthly_map:
                        monthly_map[key]["income" if entry.type == "income" else "expenses"] += converted
                else:
                    due_date = projected_card_due_date(entry, occurrence_date)
                    if not (date_from <= due_date <= date_to):
                        continue
                    converted = converter.convert(entry.amount, entry.credit_card.currency)
                    if converted is None:
                        continue
                    key = f"{due_date.year:04d}-{due_date.month:02d}"
                    if key in monthly_map:
                        monthly_map[key]["expenses"] += converted

    expenses_by_category: defaultdict[str, Decimal] = defaultdict(Decimal)
    category_colors: dict[str, str] = {}
    for tx in transactions:
        if tx.type != "expense" or not (date_from <= tx.date <= date_to):
            continue
        name = tx.category_ref.name if tx.category_ref else (tx.category or "Sin categoría")
        converted = converter.convert(tx.amount, tx.account.currency)
        if converted is not None:
            expenses_by_category[name] += converted
            category_colors[name] = (
                tx.category_ref.color
                if tx.category_ref
                else categories_by_name[name.lower()].color
                if name.lower() in categories_by_name
                else "#64748b"
            )
    for installment in installments:
        if not (date_from <= installment.due_date <= date_to):
            continue
        purchase = installment.purchase
        name = purchase.category_ref.name if purchase.category_ref else (purchase.category or "Cuotas")
        converted = converter.convert(installment.amount, purchase.credit_card.currency)
        if converted is not None:
            expenses_by_category[name] += converted
            category_colors[name] = purchase.category_ref.color if purchase.category_ref else "#f59e0b"

    accounts = (
        db.query(Account)
        .options(joinedload(Account.currency))
        .filter(Account.user_id == user_id)
        .all()
    )
    account_balances = []
    account_total = Decimal("0")
    for account in accounts:
        balance = get_account_current_balance(db, account)
        converted_balance = converter.convert(balance, account.currency)
        if converted_balance is not None:
            account_total += converted_balance
        account_balances.append(
            {
                "account_id": str(account.id),
                "name": account.name,
                "type": account.type,
                "balance": _q(balance),
                "currency_code": account.currency.code,
                "converted_balance": converted_balance,
            }
        )

    investments = (
        db.query(Investment)
        .options(joinedload(Investment.currency))
        .filter(Investment.user_id == user_id)
        .all()
    )
    investment_rows = []
    investment_total = Decimal("0")
    for inv in investments:
        current = _decimal(inv.current_value)
        invested = _decimal(inv.invested_amount)
        converted_current = converter.convert(current, inv.currency)
        if converted_current is not None:
            investment_total += converted_current
        unrealized_gain = _q(current - invested)
        realized_gain = _decimal(inv.realized_gain)
        total_gain = _q(unrealized_gain + realized_gain)
        investment_rows.append(
            {
                "investment_id": str(inv.id),
                "name": inv.name,
                "type": inv.type,
                "invested_amount": invested,
                "current_value": current,
                "realized_gain": realized_gain,
                "unrealized_gain": unrealized_gain,
                "gain": total_gain,
                "return_pct": _ratio_pct(total_gain, invested),
                "converted_current_value": converted_current,
            }
        )

    goals = (
        db.query(SavingGoal)
        .options(joinedload(SavingGoal.currency))
        .filter(SavingGoal.user_id == user_id)
        .all()
    )
    goal_rows = []
    for goal in goals:
        allocations = (
            db.query(SavingGoalAllocation)
            .options(
                joinedload(SavingGoalAllocation.account).joinedload(Account.currency),
                joinedload(SavingGoalAllocation.investment).joinedload(Investment.currency),
            )
            .filter(SavingGoalAllocation.saving_goal_id == goal.id)
            .all()
        )
        tracking_mode = "allocated" if allocations else "manual"
        if allocations:
            current = Decimal("0")
            goal_converter = Converter(db, goal.currency.code, date_to)
            for allocation in allocations:
                if allocation.account is not None:
                    source_value = get_account_current_balance(db, allocation.account)
                    source_currency = allocation.account.currency
                else:
                    source_value = _decimal(allocation.investment.current_value)
                    source_currency = allocation.investment.currency
                converted_source = goal_converter.convert(source_value, source_currency)
                if converted_source is not None:
                    current += converted_source * _decimal(allocation.allocation_percent) / Decimal("100")
            converter.warnings.extend(goal_converter.warnings)
            current = _q(current)
        else:
            current = _decimal(goal.current_amount)

        target = _decimal(goal.target_amount)
        converted_current = converter.convert(current, goal.currency)
        converted_target = converter.convert(target, goal.currency)
        goal_rows.append(
            {
                "goal_id": str(goal.id),
                "name": goal.name,
                "tracking_mode": tracking_mode,
                "current_amount": current,
                "target_amount": target,
                "converted_current_amount": converted_current,
                "converted_target_amount": converted_target,
                "progress_pct": min(_ratio_pct(current, target), Decimal("100")),
                "target_date": goal.target_date,
                "color": goal.color,
                "icon": goal.icon,
            }
        )

    # Saving goals are labels/allocation views over assets, not additional assets.
    wealth = _q(account_total + investment_total)
    previous_wealth = wealth - previous_net

    upcoming = (
        db.query(Installment)
        .options(joinedload(Installment.purchase).joinedload(CreditCardPurchase.credit_card))
        .filter(
            Installment.user_id == user_id,
            Installment.due_date >= date.today(),
            Installment.is_paid.is_(False),
        )
        .order_by(Installment.due_date)
        .limit(8)
        .all()
    )
    upcoming_rows = [
        {
            "installment_id": str(inst.id),
            "description": inst.purchase.description,
            "current_installment": inst.installment_number,
            "total_installments": inst.purchase.installments,
            "due_date": inst.due_date,
            "amount": _decimal(inst.amount),
            "converted_amount": converter.convert(
                inst.amount,
                inst.purchase.credit_card.currency,
            ),
            "card_name": inst.purchase.credit_card.name,
        }
        for inst in upcoming
    ]

    recent_movements = []
    for tx in sorted(
        [t for t in transactions if date_from <= t.date <= date_to],
        key=lambda t: t.date,
        reverse=True,
    )[:10]:
        recent_movements.append(
            {
                "id": str(tx.id),
                "type": tx.type,
                "description": tx.description,
                "category": tx.category_ref.name if tx.category_ref else tx.category,
                "account": tx.account.name,
                "date": tx.date,
                "amount": _decimal(tx.amount),
                "converted_amount": converter.convert(tx.amount, tx.account.currency),
            }
        )

    period_start = _month_start(date_from)
    period_end = _month_end(date_from)
    budgets = (
        db.query(Budget)
        .options(joinedload(Budget.category), joinedload(Budget.currency))
        .filter(Budget.user_id == user_id, Budget.period_start == period_start)
        .all()
    )
    budget_rows = []
    for budget in budgets:
        actual = Decimal("0")
        for tx in transactions:
            matches_id = tx.category_id == budget.category_id
            matches_name = (tx.category or "").lower() == budget.category.name.lower()
            if (
                tx.type == "expense"
                and period_start <= tx.date <= period_end
                and (matches_id or matches_name)
            ):
                converted = converter.convert(tx.amount, tx.account.currency)
                if converted is not None:
                    actual += converted
        budget_amount = converter.convert(budget.amount, budget.currency) or Decimal("0")
        budget_rows.append(
            {
                "budget_id": str(budget.id),
                "category": budget.category.name,
                "budget_amount": budget_amount,
                "actual_amount": _q(actual),
                "percent_used": min(_ratio_pct(actual, budget_amount), Decimal("999")),
                "color": budget.category.color,
            }
        )

    category_total = sum(expenses_by_category.values(), Decimal("0"))
    category_rows = [
        {
            "category": name,
            "amount": _q(amount),
            "percent": _q((amount / category_total) * Decimal("100"))
            if category_total
            else Decimal("0"),
            "color": category_colors.get(name, "#64748b"),
        }
        for name, amount in sorted(
            expenses_by_category.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    return {
        "currency": converter.target.code,
        "date_from": date_from,
        "date_to": date_to,
        "warnings": sorted(set(converter.warnings)),
        "kpis": {
            "income": {
                "value": income,
                "previous_value": previous_income,
                "change_pct": _pct(income, previous_income),
            },
            "expenses": {
                "value": expenses,
                "previous_value": previous_expenses,
                "change_pct": _pct(expenses, previous_expenses),
            },
            "net_savings": {
                "value": net,
                "previous_value": previous_net,
                "change_pct": _pct(net, previous_net),
            },
            "wealth": {
                "value": wealth,
                "previous_value": previous_wealth,
                "change_pct": _pct(wealth, previous_wealth),
            },
        },
        "monthly_flow": [
            {
                "month": month,
                "income": _q(values["income"]),
                "expenses": _q(values["expenses"]),
                "net": _q(values["income"] - values["expenses"]),
            }
            for month, values in monthly_map.items()
        ],
        "expenses_by_category": category_rows,
        "account_balances": account_balances,
        "upcoming_installments": upcoming_rows,
        "investments": investment_rows,
        "recent_movements": recent_movements,
        "budgets": budget_rows,
        "saving_goals": goal_rows,
    }
