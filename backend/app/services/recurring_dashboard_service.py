from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.account import Account
from app.models.credit_card import CreditCard
from app.models.recurring_entry import RecurringEntry
from app.models.recurring_occurrence import RecurringOccurrence
from app.services.dashboard_service import Converter, _pct, _q


def augment_dashboard_with_pending_occurrences(
    db: Session,
    summary: dict,
    *,
    date_from: date,
    date_to: date,
    currency_code: str,
    user_id,
) -> dict:
    """Add accrued manual occurrences to dashboard flow without touching balances.

    Future recurring dates are already projected by ``build_dashboard_summary``.
    This function only adds due manual occurrences that are still pending, because
    they have no Transaction/Purchase yet and would otherwise disappear from the
    dashboard on their scheduled date.
    """
    period_days = (date_to - date_from).days + 1
    previous_to = date_from - timedelta(days=1)
    previous_from = previous_to - timedelta(days=period_days - 1)
    query_to = min(date_to, date.today())
    if query_to < previous_from:
        return summary

    occurrences = (
        db.query(RecurringOccurrence)
        .options(
            joinedload(RecurringOccurrence.entry)
            .joinedload(RecurringEntry.account)
            .joinedload(Account.currency),
            joinedload(RecurringOccurrence.entry)
            .joinedload(RecurringEntry.credit_card)
            .joinedload(CreditCard.currency),
            joinedload(RecurringOccurrence.entry).joinedload(RecurringEntry.category_ref),
        )
        .filter(
            RecurringOccurrence.user_id == user_id,
            RecurringOccurrence.status == "pending",
            RecurringOccurrence.scheduled_date >= previous_from,
            RecurringOccurrence.scheduled_date <= query_to,
        )
        .all()
    )
    if not occurrences:
        return summary

    converter = Converter(db, currency_code, date_to)
    current_income = Decimal("0")
    current_expenses = Decimal("0")
    previous_income = Decimal("0")
    previous_expenses = Decimal("0")
    monthly_additions: defaultdict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"income": Decimal("0"), "expenses": Decimal("0")}
    )
    pending_expenses_by_category: defaultdict[str, Decimal] = defaultdict(Decimal)
    pending_category_colors: dict[str, str] = {}

    for occurrence in occurrences:
        entry = occurrence.entry
        currency = (
            entry.account.currency
            if entry.destination_type == "account" and entry.account is not None
            else entry.credit_card.currency
            if entry.credit_card is not None
            else None
        )
        converted = converter.convert(occurrence.amount, currency)
        if converted is None:
            continue

        is_current = date_from <= occurrence.scheduled_date <= date_to
        is_previous = previous_from <= occurrence.scheduled_date <= previous_to
        if is_current:
            if entry.type == "income":
                current_income += converted
            else:
                current_expenses += converted
                category_name = (
                    entry.category_ref.name
                    if entry.category_ref is not None
                    else entry.category or "Sin categoría"
                )
                pending_expenses_by_category[category_name] += converted
                pending_category_colors[category_name] = (
                    entry.category_ref.color if entry.category_ref is not None else "#64748b"
                )

            month_key = f"{occurrence.scheduled_date.year:04d}-{occurrence.scheduled_date.month:02d}"
            monthly_additions[month_key][entry.type] += converted
        elif is_previous:
            if entry.type == "income":
                previous_income += converted
            else:
                previous_expenses += converted

    income_kpi = summary["kpis"]["income"]
    expenses_kpi = summary["kpis"]["expenses"]
    net_kpi = summary["kpis"]["net_savings"]

    income_kpi["value"] = _q(Decimal(str(income_kpi["value"])) + current_income)
    income_kpi["previous_value"] = _q(
        Decimal(str(income_kpi["previous_value"])) + previous_income
    )
    income_kpi["change_pct"] = _pct(income_kpi["value"], income_kpi["previous_value"])

    expenses_kpi["value"] = _q(Decimal(str(expenses_kpi["value"])) + current_expenses)
    expenses_kpi["previous_value"] = _q(
        Decimal(str(expenses_kpi["previous_value"])) + previous_expenses
    )
    expenses_kpi["change_pct"] = _pct(
        expenses_kpi["value"], expenses_kpi["previous_value"]
    )

    net_kpi["value"] = _q(income_kpi["value"] - expenses_kpi["value"])
    net_kpi["previous_value"] = _q(
        income_kpi["previous_value"] - expenses_kpi["previous_value"]
    )
    net_kpi["change_pct"] = _pct(net_kpi["value"], net_kpi["previous_value"])

    for row in summary["monthly_flow"]:
        addition = monthly_additions.get(row["month"])
        if not addition:
            continue
        row["income"] = _q(Decimal(str(row["income"])) + addition["income"])
        row["expenses"] = _q(Decimal(str(row["expenses"])) + addition["expenses"])
        row["net"] = _q(row["income"] - row["expenses"])

    if pending_expenses_by_category:
        amounts: defaultdict[str, Decimal] = defaultdict(Decimal)
        colors: dict[str, str] = {}
        for row in summary["expenses_by_category"]:
            amounts[row["category"]] += Decimal(str(row["amount"]))
            colors[row["category"]] = row["color"]
        for category_name, amount in pending_expenses_by_category.items():
            amounts[category_name] += amount
            colors.setdefault(category_name, pending_category_colors[category_name])

        total = sum(amounts.values(), Decimal("0"))
        summary["expenses_by_category"] = [
            {
                "category": category_name,
                "amount": _q(amount),
                "percent": _q((amount / total) * Decimal("100")) if total else Decimal("0"),
                "color": colors.get(category_name, "#64748b"),
            }
            for category_name, amount in sorted(
                amounts.items(), key=lambda item: item[1], reverse=True
            )
        ]

    summary["warnings"] = sorted(set(summary["warnings"] + converter.warnings))
    return summary
