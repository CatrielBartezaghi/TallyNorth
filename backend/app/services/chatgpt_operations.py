from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.installment import Installment
from app.models.purchase import CreditCardPurchase
from app.models.transaction import Transaction
from app.schemas.integration import ChatGPTPurchaseCreate, ChatGPTTransactionCreate
from app.services.installment_service import (
    compute_first_installment_date,
    compute_installment_amount,
    generate_installment_dates,
)


class OwnedResourceNotFoundError(ValueError):
    pass


class InvalidCategoryError(ValueError):
    pass


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
        is_recurring=payload.is_recurring,
        recurrence_rule=payload.recurrence_rule,
        end_date=payload.end_date,
    )
    db.add(transaction)
    db.flush()
    return transaction


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
