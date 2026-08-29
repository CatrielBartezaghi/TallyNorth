from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.investment import Investment, InvestmentOperation, InvestmentValuation
from app.schemas.investment import InvestmentOperationCreate, InvestmentValuationCreate


MONEY = Decimal("0.01")
QUANTITY = Decimal("0.00000001")
PRICE = Decimal("0.00000001")


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _quantity(value: Decimal) -> Decimal:
    return value.quantize(QUANTITY, rounding=ROUND_HALF_UP)


def _price(value: Decimal) -> Decimal:
    return value.quantize(PRICE, rounding=ROUND_HALF_UP)


def get_owned_investment(db: Session, user_id, investment_id) -> Investment:
    investment = (
        db.query(Investment)
        .filter(Investment.id == investment_id, Investment.user_id == user_id)
        .first()
    )
    if investment is None:
        raise ValueError("Investment not found for the authenticated user")
    return investment


def operation_account_delta(operation: InvestmentOperation) -> Decimal:
    amount = _decimal(operation.amount)
    fee = _decimal(operation.fee)
    if operation.type in {"opening"} or operation.account_id is None:
        return Decimal("0")
    if operation.type == "buy":
        return -(amount + fee)
    if operation.type == "sell":
        return amount - fee
    if operation.type in {"dividend", "interest"}:
        return amount - fee
    if operation.type == "fee":
        return -amount
    return Decimal("0")


def _recompute_position(db: Session, investment: Investment) -> None:
    operations = (
        db.query(InvestmentOperation)
        .filter(InvestmentOperation.investment_id == investment.id)
        .order_by(InvestmentOperation.date.asc(), InvestmentOperation.created_at.asc())
        .all()
    )
    quantity = Decimal("0")
    quantified_cost_basis = Decimal("0")
    unquantified_cost_basis = Decimal("0")
    realized_gain = Decimal("0")

    for operation in operations:
        amount = _decimal(operation.amount)
        fee = _decimal(operation.fee)
        op_quantity = _decimal(operation.quantity) if operation.quantity is not None else None

        if operation.type in {"opening", "buy"}:
            if op_quantity is not None:
                quantified_cost_basis += amount + fee
                quantity += op_quantity
            else:
                unquantified_cost_basis += amount + fee
        elif operation.type == "sell":
            proceeds = amount - fee
            if op_quantity is not None:
                if quantity <= 0 or op_quantity > quantity:
                    raise ValueError("Sell quantity exceeds current quantified position")
                average_cost = quantified_cost_basis / quantity
                removed_cost = average_cost * op_quantity
                quantity -= op_quantity
                quantified_cost_basis -= removed_cost
                realized_gain += proceeds - removed_cost
            else:
                # Amount-only positions (funds/fixed income) reduce their own open cost first.
                removed_cost = min(unquantified_cost_basis, amount)
                unquantified_cost_basis -= removed_cost
                remainder = amount - removed_cost
                if remainder > 0 and quantified_cost_basis > 0:
                    quantified_removed = min(quantified_cost_basis, remainder)
                    quantified_cost_basis -= quantified_removed
                    removed_cost += quantified_removed
                realized_gain += proceeds - removed_cost
        elif operation.type in {"dividend", "interest"}:
            realized_gain += amount - fee
        elif operation.type == "fee":
            realized_gain -= amount

    cost_basis = max(
        quantified_cost_basis + unquantified_cost_basis,
        Decimal("0"),
    )
    investment.invested_amount = _money(cost_basis)
    investment.quantity = _quantity(max(quantity, Decimal("0")))
    investment.average_cost = (
        _price(quantified_cost_basis / quantity)
        if quantity > 0 and quantified_cost_basis > 0
        else None
    )
    investment.realized_gain = _money(realized_gain)


def create_operation(
    db: Session,
    *,
    user_id,
    investment: Investment,
    payload: InvestmentOperationCreate,
) -> InvestmentOperation:
    if payload.account_id is not None:
        account = (
            db.query(Account)
            .filter(Account.id == payload.account_id, Account.user_id == user_id)
            .first()
        )
        if account is None:
            raise ValueError("Account not found for the authenticated user")
        if account.currency_id != investment.currency_id:
            raise ValueError("Investment operations currently require account and investment to use the same currency")

    operation = InvestmentOperation(
        user_id=user_id,
        investment_id=investment.id,
        **payload.model_dump(),
    )
    db.add(operation)
    db.flush()
    _recompute_position(db, investment)

    if payload.type in {"opening", "buy"}:
        investment.current_value = _money(_decimal(investment.current_value) + payload.amount)
    elif payload.type == "sell":
        investment.current_value = _money(max(
            Decimal("0"),
            _decimal(investment.current_value) - payload.amount,
        ))

    db.flush()
    return operation


def record_valuation(
    db: Session,
    *,
    user_id,
    investment: Investment,
    payload: InvestmentValuationCreate,
) -> InvestmentValuation:
    valuation = InvestmentValuation(
        user_id=user_id,
        investment_id=investment.id,
        **payload.model_dump(),
    )
    db.add(valuation)
    investment.current_value = _money(payload.value)
    db.flush()
    return valuation
