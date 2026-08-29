from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.currency import Currency
from app.models.installment import Installment
from app.models.investment import Investment
from app.models.purchase import CreditCardPurchase
from app.models.recurring_entry import RecurringEntry
from app.models.saving_goal import SavingGoal
from app.models.transaction import Transaction
from app.schemas.investment import InvestmentOperationCreate, InvestmentValuationCreate
from app.schemas.integration import (
    ChatGPTBatchPurchaseCreate,
    ChatGPTBatchTransactionCreate,
    ChatGPTBudgetSet,
    ChatGPTFinanceBatchCreate,
    ChatGPTFinanceBatchItemResult,
    ChatGPTInstallmentPaymentCreate,
    ChatGPTInvestmentCreate,
    ChatGPTInvestmentValueUpdate,
    ChatGPTPurchaseCreate,
    ChatGPTRecurringEntryCreate,
    ChatGPTSavingGoalCreate,
    ChatGPTSavingGoalProgressUpdate,
    ChatGPTTransactionCreate,
)
from app.services.investment_service import create_operation, record_valuation
from app.services.installment_service import (
    compute_first_installment_date,
    compute_installment_amount,
    generate_installment_dates,
)


class OwnedResourceNotFoundError(ValueError):
    pass


class InvalidCategoryError(ValueError):
    pass


class ActionConflictError(ValueError):
    pass


class BatchItemError(ValueError):
    def __init__(self, index: int, message: str):
        super().__init__(message)
        self.index = index
        self.message = message


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _get_owned_category(
    db: Session,
    user_id,
    category_id,
    operation_type: str,
) -> Category | None:
    if category_id is None:
        return None

    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.user_id == user_id,
            Category.is_active.is_(True),
        )
        .first()
    )
    if category is None:
        raise OwnedResourceNotFoundError(
            "Category not found for the authenticated user"
        )
    if category.type not in (operation_type, "both"):
        raise InvalidCategoryError(
            f"Category '{category.name}' cannot be used for {operation_type} operations"
        )
    return category


def _get_currency(db: Session, currency_id) -> Currency:
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if currency is None:
        raise OwnedResourceNotFoundError("Currency not found")
    return currency


def create_chatgpt_transaction(
    db: Session,
    user_id,
    payload: ChatGPTTransactionCreate,
) -> Transaction:
    account = (
        db.query(Account)
        .filter(Account.id == payload.account_id, Account.user_id == user_id)
        .first()
    )
    if account is None:
        raise OwnedResourceNotFoundError(
            "Account not found for the authenticated user"
        )

    category = _get_owned_category(
        db,
        user_id,
        payload.category_id,
        payload.type,
    )

    transaction = Transaction(
        user_id=user_id,
        account_id=payload.account_id,
        category_id=payload.category_id,
        type=payload.type,
        amount=payload.amount,
        description=payload.description,
        category=category.name if category else None,
        date=payload.date,
    )
    db.add(transaction)
    db.flush()
    return transaction


def create_chatgpt_recurring_entry(
    db: Session,
    user_id,
    payload: ChatGPTRecurringEntryCreate,
) -> RecurringEntry:
    if payload.destination_type == "account":
        account = (
            db.query(Account)
            .filter(Account.id == payload.account_id, Account.user_id == user_id)
            .first()
        )
        if account is None:
            raise OwnedResourceNotFoundError(
                "Account not found for the authenticated user"
            )
    else:
        card = (
            db.query(CreditCard)
            .filter(
                CreditCard.id == payload.credit_card_id,
                CreditCard.user_id == user_id,
            )
            .first()
        )
        if card is None:
            raise OwnedResourceNotFoundError(
                "Credit card not found for the authenticated user"
            )

    category = _get_owned_category(
        db,
        user_id,
        payload.category_id,
        payload.type,
    )

    entry = RecurringEntry(
        user_id=user_id,
        category=category.name if category else None,
        **payload.model_dump(exclude={"idempotency_key"}),
    )
    db.add(entry)
    db.flush()
    return entry


def create_chatgpt_purchase(
    db: Session,
    user_id,
    payload: ChatGPTPurchaseCreate,
) -> CreditCardPurchase:
    card = (
        db.query(CreditCard)
        .filter(
            CreditCard.id == payload.credit_card_id,
            CreditCard.user_id == user_id,
        )
        .first()
    )
    if card is None:
        raise OwnedResourceNotFoundError(
            "Credit card not found for the authenticated user"
        )

    category = _get_owned_category(
        db,
        user_id,
        payload.category_id,
        "expense",
    )

    installment_amount = compute_installment_amount(
        Decimal(str(payload.total_amount)),
        payload.installments,
    )
    first_date = compute_first_installment_date(
        purchase_date=payload.purchase_date,
        closing_day=card.closing_day,
        due_day=card.due_day,
    )
    installment_count = payload.installments - payload.starting_installment + 1
    due_dates = generate_installment_dates(
        first_date,
        installment_count,
        card.due_day,
    )

    purchase = CreditCardPurchase(
        user_id=user_id,
        credit_card_id=payload.credit_card_id,
        category_id=payload.category_id,
        description=payload.description,
        total_amount=payload.total_amount,
        installments=payload.installments,
        installment_amount=installment_amount,
        purchase_date=payload.purchase_date,
        first_installment_date=first_date,
        category=category.name if category else None,
    )
    db.add(purchase)
    db.flush()

    for installment_number, due_date in enumerate(
        due_dates,
        start=payload.starting_installment,
    ):
        db.add(
            Installment(
                user_id=user_id,
                purchase_id=purchase.id,
                installment_number=installment_number,
                due_date=due_date,
                amount=installment_amount,
            )
        )

    db.flush()
    return purchase


def create_chatgpt_finance_batch(
    db: Session,
    user_id,
    payload: ChatGPTFinanceBatchCreate,
) -> list[ChatGPTFinanceBatchItemResult]:
    results: list[ChatGPTFinanceBatchItemResult] = []
    for index, entry in enumerate(payload.entries):
        try:
            if isinstance(entry, ChatGPTBatchTransactionCreate):
                transaction = create_chatgpt_transaction(
                    db,
                    user_id,
                    ChatGPTTransactionCreate(
                        idempotency_key=payload.idempotency_key,
                        **entry.model_dump(exclude={"kind"}),
                    ),
                )
                results.append(
                    ChatGPTFinanceBatchItemResult(
                        index=index,
                        kind="transaction",
                        resource_id=transaction.id,
                    )
                )
            elif isinstance(entry, ChatGPTBatchPurchaseCreate):
                purchase = create_chatgpt_purchase(
                    db,
                    user_id,
                    ChatGPTPurchaseCreate(
                        idempotency_key=payload.idempotency_key,
                        **entry.model_dump(exclude={"kind"}),
                    ),
                )
                results.append(
                    ChatGPTFinanceBatchItemResult(
                        index=index,
                        kind="credit_card_purchase",
                        resource_id=purchase.id,
                    )
                )
        except (OwnedResourceNotFoundError, InvalidCategoryError) as exc:
            raise BatchItemError(index, str(exc)) from exc
    return results


def set_chatgpt_budget(
    db: Session,
    user_id,
    payload: ChatGPTBudgetSet,
) -> tuple[Budget, str]:
    category = _get_owned_category(
        db,
        user_id,
        payload.category_id,
        "expense",
    )
    _get_currency(db, payload.currency_id)
    year, month = (int(part) for part in payload.period_month.split("-"))
    period_start = date(year, month, 1)

    budget = (
        db.query(Budget)
        .filter(
            Budget.user_id == user_id,
            Budget.category_id == category.id,
            Budget.currency_id == payload.currency_id,
            Budget.period_start == period_start,
        )
        .with_for_update()
        .first()
    )
    if budget is None:
        if payload.expected_current_amount is not None:
            raise ActionConflictError(
                "Budget does not exist, so expected_current_amount must be omitted"
            )
        budget = Budget(
            user_id=user_id,
            category_id=payload.category_id,
            currency_id=payload.currency_id,
            period_start=period_start,
            amount=payload.amount,
            notes=payload.notes,
        )
        db.add(budget)
        db.flush()
        return budget, "created"

    if payload.expected_current_amount is None:
        raise ActionConflictError(
            "Budget already exists; expected_current_amount is required to update it"
        )
    if _decimal(budget.amount) != payload.expected_current_amount:
        raise ActionConflictError(
            f"Budget amount changed; current amount is {_decimal(budget.amount)}"
        )

    budget.amount = payload.amount
    budget.notes = payload.notes
    db.flush()
    return budget, "updated"


def create_chatgpt_saving_goal(
    db: Session,
    user_id,
    payload: ChatGPTSavingGoalCreate,
) -> SavingGoal:
    _get_currency(db, payload.currency_id)
    goal = SavingGoal(
        user_id=user_id,
        name=payload.name,
        currency_id=payload.currency_id,
        target_amount=payload.target_amount,
        current_amount=payload.current_amount,
        target_date=payload.target_date,
    )
    db.add(goal)
    db.flush()
    return goal


def update_chatgpt_saving_goal_progress(
    db: Session,
    user_id,
    payload: ChatGPTSavingGoalProgressUpdate,
) -> SavingGoal:
    goal = (
        db.query(SavingGoal)
        .filter(
            SavingGoal.id == payload.goal_id,
            SavingGoal.user_id == user_id,
        )
        .with_for_update()
        .first()
    )
    if goal is None:
        raise OwnedResourceNotFoundError(
            "Saving goal not found for the authenticated user"
        )
    if _decimal(goal.current_amount) != payload.expected_current_amount:
        raise ActionConflictError(
            f"Saving goal changed; current amount is {_decimal(goal.current_amount)}"
        )
    goal.current_amount = payload.new_current_amount
    db.flush()
    return goal


def create_chatgpt_investment(
    db: Session,
    user_id,
    payload: ChatGPTInvestmentCreate,
) -> Investment:
    """Compatibility path for the pre-ledger ChatGPT action.

    New GPT contracts use createInvestmentAsset. Keeping this path ledger-backed
    prevents internal/legacy callers from creating snapshot-only investments.
    """
    _get_currency(db, payload.currency_id)
    investment = Investment(
        user_id=user_id,
        name=payload.name,
        type=payload.type,
        currency_id=payload.currency_id,
        invested_amount=0,
        current_value=0,
        expected_return_rate=payload.expected_return_rate,
        notes=payload.notes,
    )
    db.add(investment)
    db.flush()

    if payload.invested_amount > 0:
        create_operation(
            db,
            user_id=user_id,
            investment=investment,
            payload=InvestmentOperationCreate(
                type="opening",
                amount=payload.invested_amount,
                date=date.today(),
                notes="Opening position from compatibility ChatGPT action",
            ),
        )

    if payload.current_value > 0 or payload.invested_amount > 0:
        initial_value = (
            payload.current_value
            if payload.current_value > 0
            else payload.invested_amount
        )
        record_valuation(
            db,
            user_id=user_id,
            investment=investment,
            payload=InvestmentValuationCreate(
                value=initial_value,
                valuation_date=date.today(),
                source="chatgpt-compat",
                notes="Initial valuation from compatibility action",
            ),
        )
    return investment


def update_chatgpt_investment_value(
    db: Session,
    user_id,
    payload: ChatGPTInvestmentValueUpdate,
) -> Investment:
    investment = (
        db.query(Investment)
        .filter(
            Investment.id == payload.investment_id,
            Investment.user_id == user_id,
        )
        .with_for_update()
        .first()
    )
    if investment is None:
        raise OwnedResourceNotFoundError(
            "Investment not found for the authenticated user"
        )
    if _decimal(investment.current_value) != payload.expected_current_value:
        raise ActionConflictError(
            f"Investment changed; current value is {_decimal(investment.current_value)}"
        )
    record_valuation(
        db,
        user_id=user_id,
        investment=investment,
        payload=InvestmentValuationCreate(
            value=payload.new_current_value,
            valuation_date=date.today(),
            source="chatgpt-compat",
            notes="Valuation from compatibility ChatGPT action",
        ),
    )
    return investment


def mark_chatgpt_installment_paid(
    db: Session,
    user_id,
    payload: ChatGPTInstallmentPaymentCreate,
) -> tuple[Installment, str]:
    installment = (
        db.query(Installment)
        .filter(
            Installment.id == payload.installment_id,
            Installment.user_id == user_id,
        )
        .with_for_update()
        .first()
    )
    if installment is None:
        raise OwnedResourceNotFoundError(
            "Installment not found for the authenticated user"
        )

    account = (
        db.query(Account)
        .filter(
            Account.id == payload.paid_account_id,
            Account.user_id == user_id,
        )
        .first()
    )
    if account is None:
        raise OwnedResourceNotFoundError(
            "Payment account not found for the authenticated user"
        )

    card = installment.purchase.credit_card
    if account.currency_id != card.currency_id:
        raise ActionConflictError(
            "Payment account and credit card must use the same currency"
        )

    if installment.is_paid:
        if installment.paid_account_id == account.id:
            return installment, "already_processed"
        raise ActionConflictError(
            "Installment is already paid from a different account"
        )

    installment.is_paid = True
    installment.paid_account_id = account.id
    installment.paid_at = datetime.now(timezone.utc)
    db.flush()
    return installment, "paid"
