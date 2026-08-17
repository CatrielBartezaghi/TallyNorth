from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.installment import Installment
from app.models.transaction import Transaction


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def get_account_current_balance(db: Session, account: Account) -> Decimal:
    transaction_total = db.query(
        func.coalesce(
            func.sum(
                case(
                    (Transaction.type == "income", Transaction.amount),
                    else_=-Transaction.amount,
                )
            ),
            0,
        )
    ).filter(Transaction.account_id == account.id).scalar()

    paid_installments_total = db.query(
        func.coalesce(func.sum(Installment.amount), 0)
    ).filter(
        Installment.paid_account_id == account.id,
        Installment.is_paid.is_(True),
    ).scalar()

    return (
        _decimal(account.initial_balance)
        + _decimal(transaction_total)
        - _decimal(paid_installments_total)
    )


def reconcile_account_balance(
    db: Session,
    account: Account,
    *,
    expected_current_balance: Decimal,
    new_current_balance: Decimal,
) -> tuple[Decimal, Decimal]:
    """Reconcile an account without creating a synthetic income/expense.

    The adjustment is applied to the account baseline so financial activity
    reports remain based only on real transactions and installment payments.
    """
    current_balance = get_account_current_balance(db, account)
    if current_balance != expected_current_balance:
        raise ValueError(
            f"Account balance changed; current balance is {current_balance}"
        )

    adjustment = new_current_balance - current_balance
    if adjustment:
        account.initial_balance = _decimal(account.initial_balance) + adjustment
        db.flush()

    return current_balance, adjustment
