import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session, joinedload

from app.models.account import Account
from app.models.budget import Budget
from app.models.credit_card import CreditCard
from app.models.currency import Currency
from app.models.installment import Installment
from app.models.investment import Investment
from app.models.purchase import CreditCardPurchase
from app.models.recurring_entry import RecurringEntry
from app.models.saving_goal import SavingGoal
from app.models.transaction import Transaction
from app.schemas.integration import (
    ChatGPTCashflowMonth,
    ChatGPTCashflowProjection,
    ChatGPTFinanceEntryRead,
    ChatGPTFinanceEntrySearchResult,
    ChatGPTInstallmentRead,
    ChatGPTInstallmentSearchResult,
    FinanceEntryKind,
)
from app.services.dashboard_service import Converter
from app.services.recurring_entry_service import (
    occurrence_dates_between,
    projected_card_due_date,
    sync_recurring_entries,
)


MONEY = Decimal("0.01")
InstallmentStatus = Literal["pending", "paid", "all"]


class CurrencySelectionRequiredError(ValueError):
    def __init__(self, allowed_codes: list[str]):
        super().__init__("A target currency is required for this request")
        self.allowed_codes = allowed_codes


class CurrencyNotFoundError(ValueError):
    pass


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _q(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def resolve_chatgpt_currency(
    db: Session,
    user_id,
    requested_code: str | None,
) -> str:
    if requested_code:
        code = requested_code.upper()
        if db.query(Currency).filter(Currency.code == code).first() is None:
            raise CurrencyNotFoundError(f"Currency {code} not found")
        return code

    currency_ids: set = set()
    for model in (Account, CreditCard, Budget, SavingGoal, Investment):
        rows = db.query(model.currency_id).filter(model.user_id == user_id).all()
        currency_ids.update(row[0] for row in rows)

    if len(currency_ids) == 1:
        currency = db.query(Currency).filter(Currency.id == next(iter(currency_ids))).one()
        return currency.code

    if not currency_ids:
        default_currency = db.query(Currency).filter(Currency.code == "ARS").first()
        if default_currency is not None:
            return default_currency.code

    allowed = [
        row[0]
        for row in db.query(Currency.code)
        .filter(Currency.id.in_(currency_ids))
        .order_by(Currency.code)
        .all()
    ]
    if not allowed:
        allowed = [row[0] for row in db.query(Currency.code).order_by(Currency.code).all()]
    raise CurrencySelectionRequiredError(allowed)


def search_chatgpt_finance_entries(
    db: Session,
    user_id,
    *,
    query_text: str | None,
    kind: FinanceEntryKind | Literal["all"],
    transaction_type: Literal["income", "expense"] | None,
    date_from: date | None,
    date_to: date | None,
    category_id,
    account_id,
    credit_card_id,
    min_amount: Decimal | None,
    max_amount: Decimal | None,
    limit: int,
    offset: int,
) -> ChatGPTFinanceEntrySearchResult:
    sync_recurring_entries(db, user_id)
    fetch_count = offset + limit + 1
    merged: list[tuple[date, object, str, ChatGPTFinanceEntryRead]] = []

    include_transactions = kind in ("all", "transaction") and credit_card_id is None
    if include_transactions:
        transaction_query = (
            db.query(Transaction)
            .options(
                joinedload(Transaction.account).joinedload(Account.currency),
                joinedload(Transaction.category_ref),
            )
            .filter(Transaction.user_id == user_id)
        )
        if query_text:
            transaction_query = transaction_query.filter(
                Transaction.description.ilike(f"%{query_text}%")
            )
        if transaction_type:
            transaction_query = transaction_query.filter(
                Transaction.type == transaction_type
            )
        if date_from:
            transaction_query = transaction_query.filter(Transaction.date >= date_from)
        if date_to:
            transaction_query = transaction_query.filter(Transaction.date <= date_to)
        if category_id:
            transaction_query = transaction_query.filter(
                Transaction.category_id == category_id
            )
        if account_id:
            transaction_query = transaction_query.filter(
                Transaction.account_id == account_id
            )
        if min_amount is not None:
            transaction_query = transaction_query.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            transaction_query = transaction_query.filter(Transaction.amount <= max_amount)

        transactions = (
            transaction_query.order_by(
                Transaction.date.desc(),
                Transaction.created_at.desc(),
            )
            .limit(fetch_count)
            .all()
        )
        for transaction in transactions:
            merged.append(
                (
                    transaction.date,
                    transaction.created_at,
                    str(transaction.id),
                    ChatGPTFinanceEntryRead(
                        kind="transaction",
                        id=transaction.id,
                        description=transaction.description,
                        type=transaction.type,
                        amount=_decimal(transaction.amount),
                        currency=transaction.account.currency.code,
                        date=transaction.date,
                        category_id=transaction.category_id,
                        category=(
                            transaction.category_ref.name
                            if transaction.category_ref
                            else transaction.category
                        ),
                        account_id=transaction.account_id,
                        account_name=transaction.account.name,
                        recurring_entry_id=transaction.recurring_entry_id,
                    ),
                )
            )

    include_purchases = (
        kind in ("all", "credit_card_purchase")
        and transaction_type != "income"
        and account_id is None
    )
    if include_purchases:
        purchase_query = (
            db.query(CreditCardPurchase)
            .options(
                joinedload(CreditCardPurchase.credit_card).joinedload(
                    CreditCard.currency
                ),
                joinedload(CreditCardPurchase.category_ref),
            )
            .filter(CreditCardPurchase.user_id == user_id)
        )
        if query_text:
            purchase_query = purchase_query.filter(
                CreditCardPurchase.description.ilike(f"%{query_text}%")
            )
        if date_from:
            purchase_query = purchase_query.filter(
                CreditCardPurchase.purchase_date >= date_from
            )
        if date_to:
            purchase_query = purchase_query.filter(
                CreditCardPurchase.purchase_date <= date_to
            )
        if category_id:
            purchase_query = purchase_query.filter(
                CreditCardPurchase.category_id == category_id
            )
        if credit_card_id:
            purchase_query = purchase_query.filter(
                CreditCardPurchase.credit_card_id == credit_card_id
            )
        if min_amount is not None:
            purchase_query = purchase_query.filter(
                CreditCardPurchase.total_amount >= min_amount
            )
        if max_amount is not None:
            purchase_query = purchase_query.filter(
                CreditCardPurchase.total_amount <= max_amount
            )

        purchases = (
            purchase_query.order_by(
                CreditCardPurchase.purchase_date.desc(),
                CreditCardPurchase.created_at.desc(),
            )
            .limit(fetch_count)
            .all()
        )
        for purchase in purchases:
            merged.append(
                (
                    purchase.purchase_date,
                    purchase.created_at,
                    str(purchase.id),
                    ChatGPTFinanceEntryRead(
                        kind="credit_card_purchase",
                        id=purchase.id,
                        description=purchase.description,
                        type="expense",
                        amount=_decimal(purchase.total_amount),
                        currency=purchase.credit_card.currency.code,
                        date=purchase.purchase_date,
                        category_id=purchase.category_id,
                        category=(
                            purchase.category_ref.name
                            if purchase.category_ref
                            else purchase.category
                        ),
                        credit_card_id=purchase.credit_card_id,
                        credit_card_name=purchase.credit_card.name,
                        installments=purchase.installments,
                        installment_amount=_decimal(purchase.installment_amount),
                        recurring_entry_id=purchase.recurring_entry_id,
                    ),
                )
            )

    merged.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    page = merged[offset : offset + limit + 1]
    return ChatGPTFinanceEntrySearchResult(
        items=[item[3] for item in page[:limit]],
        limit=limit,
        offset=offset,
        has_more=len(page) > limit,
    )


def list_chatgpt_installments(
    db: Session,
    user_id,
    *,
    date_from: date | None,
    date_to: date | None,
    credit_card_id,
    installment_status: InstallmentStatus,
    limit: int,
) -> ChatGPTInstallmentSearchResult:
    query = (
        db.query(Installment)
        .options(
            joinedload(Installment.purchase)
            .joinedload(CreditCardPurchase.credit_card)
            .joinedload(CreditCard.currency)
        )
        .filter(Installment.user_id == user_id)
    )
    if date_from:
        query = query.filter(Installment.due_date >= date_from)
    if date_to:
        query = query.filter(Installment.due_date <= date_to)
    if credit_card_id:
        query = query.join(Installment.purchase).filter(
            CreditCardPurchase.credit_card_id == credit_card_id
        )
    if installment_status == "pending":
        query = query.filter(Installment.is_paid.is_(False))
    elif installment_status == "paid":
        query = query.filter(Installment.is_paid.is_(True))

    rows = query.order_by(Installment.due_date, Installment.id).limit(limit + 1).all()
    items = []
    for installment in rows[:limit]:
        purchase = installment.purchase
        card = purchase.credit_card
        items.append(
            ChatGPTInstallmentRead(
                id=installment.id,
                purchase_id=purchase.id,
                description=purchase.description,
                installment_number=installment.installment_number,
                total_installments=purchase.installments,
                due_date=installment.due_date,
                amount=_decimal(installment.amount),
                currency=card.currency.code,
                is_paid=installment.is_paid,
                credit_card_id=card.id,
                credit_card_name=card.name,
                paid_account_id=installment.paid_account_id,
                paid_at=installment.paid_at,
            )
        )
    return ChatGPTInstallmentSearchResult(
        items=items,
        limit=limit,
        has_more=len(rows) > limit,
    )


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _month_end(value: date) -> date:
    return date(value.year, value.month, calendar.monthrange(value.year, value.month)[1])


def build_chatgpt_cashflow_projection(
    db: Session,
    user_id,
    *,
    target_currency: str,
    months: int,
    current_date: date,
) -> ChatGPTCashflowProjection:
    sync_recurring_entries(db, user_id)
    window_start = _month_start(current_date)
    final_month = window_start + relativedelta(months=months - 1)
    window_end = _month_end(final_month)
    converter = Converter(db, target_currency, current_date)

    month_map: dict[str, dict[str, Decimal]] = {}
    cursor = window_start
    for _ in range(months):
        month_map[f"{cursor.year:04d}-{cursor.month:02d}"] = {
            "income": Decimal("0"),
            "expenses": Decimal("0"),
            "installments": Decimal("0"),
        }
        cursor = cursor + relativedelta(months=1)

    transactions = (
        db.query(Transaction)
        .options(joinedload(Transaction.account).joinedload(Account.currency))
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= window_start,
            Transaction.date <= window_end,
        )
        .all()
    )
    for transaction in transactions:
        converted = converter.convert(transaction.amount, transaction.account.currency)
        if converted is None:
            continue
        key = f"{transaction.date.year:04d}-{transaction.date.month:02d}"
        bucket = "income" if transaction.type == "income" else "expenses"
        month_map[key][bucket] += converted

    installments = (
        db.query(Installment)
        .options(
            joinedload(Installment.purchase)
            .joinedload(CreditCardPurchase.credit_card)
            .joinedload(CreditCard.currency)
        )
        .filter(
            Installment.user_id == user_id,
            Installment.due_date >= window_start,
            Installment.due_date <= window_end,
            Installment.is_paid.is_(False),
        )
        .all()
    )
    for installment in installments:
        currency = installment.purchase.credit_card.currency
        converted = converter.convert(installment.amount, currency)
        if converted is None:
            continue
        key = f"{installment.due_date.year:04d}-{installment.due_date.month:02d}"
        month_map[key]["installments"] += converted

    future_from = max(window_start, current_date + timedelta(days=1))
    if future_from <= window_end:
        recurring_entries = (
            db.query(RecurringEntry)
            .options(
                joinedload(RecurringEntry.account).joinedload(Account.currency),
                joinedload(RecurringEntry.credit_card).joinedload(CreditCard.currency),
            )
            .filter(
                RecurringEntry.user_id == user_id,
                RecurringEntry.active.is_(True),
            )
            .all()
        )
        for entry in recurring_entries:
            for occurrence_date in occurrence_dates_between(entry, future_from, window_end):
                if entry.destination_type == "account":
                    converted = converter.convert(entry.amount, entry.account.currency)
                    if converted is None:
                        continue
                    key = f"{occurrence_date.year:04d}-{occurrence_date.month:02d}"
                    bucket = "income" if entry.type == "income" else "expenses"
                    month_map[key][bucket] += converted
                else:
                    due_date = projected_card_due_date(entry, occurrence_date)
                    if not (window_start <= due_date <= window_end):
                        continue
                    converted = converter.convert(entry.amount, entry.credit_card.currency)
                    if converted is None:
                        continue
                    key = f"{due_date.year:04d}-{due_date.month:02d}"
                    month_map[key]["installments"] += converted

    result_months = []
    for month, values in month_map.items():
        income = _q(values["income"])
        expenses = _q(values["expenses"])
        installments_total = _q(values["installments"])
        result_months.append(
            ChatGPTCashflowMonth(
                month=month,
                total_income=income,
                total_expenses=expenses,
                total_installments=installments_total,
                net=_q(income - expenses - installments_total),
            )
        )

    return ChatGPTCashflowProjection(
        currency=target_currency,
        warnings=sorted(set(converter.warnings)),
        months=result_months,
    )
