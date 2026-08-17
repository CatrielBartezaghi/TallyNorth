import uuid
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session, joinedload

from app.models.credit_card import CreditCard
from app.models.installment import Installment
from app.models.purchase import CreditCardPurchase
from app.models.recurring_entry import RecurringEntry
from app.models.transaction import Transaction
from app.services.installment_service import compute_first_installment_date


def advance_recurrence(value: date, frequency: str) -> date:
    if frequency == "weekly":
        return value + timedelta(weeks=1)
    if frequency == "monthly":
        return value + relativedelta(months=1)
    if frequency == "yearly":
        return value + relativedelta(years=1)
    raise ValueError(f"Unsupported recurring frequency: {frequency}")


def occurrence_dates_between(entry: RecurringEntry, start: date, end: date) -> list[date]:
    """Return scheduled dates for an entry inside an inclusive date window."""
    if end < start or not entry.active:
        return []

    current = entry.start_date
    while current < start:
        current = advance_recurrence(current, entry.frequency)

    result: list[date] = []
    while current <= end:
        if entry.end_date is not None and current > entry.end_date:
            break
        result.append(current)
        current = advance_recurrence(current, entry.frequency)
    return result


def projected_card_due_date(entry: RecurringEntry, occurrence_date: date) -> date:
    card: CreditCard = entry.credit_card
    return compute_first_installment_date(
        purchase_date=occurrence_date,
        closing_day=card.closing_day,
        due_day=card.due_day,
    )


def _materialize_account_occurrence(
    db: Session,
    entry: RecurringEntry,
    occurrence_date: date,
) -> None:
    existing = (
        db.query(Transaction)
        .filter(
            Transaction.recurring_entry_id == entry.id,
            Transaction.date == occurrence_date,
        )
        .first()
    )
    if existing is not None:
        return

    db.add(
        Transaction(
            user_id=entry.user_id,
            account_id=entry.account_id,
            category_id=entry.category_id,
            type=entry.type,
            amount=entry.amount,
            description=entry.description,
            category=entry.category,
            date=occurrence_date,
            is_recurring=False,
            recurring_entry_id=entry.id,
        )
    )


def _materialize_card_occurrence(
    db: Session,
    entry: RecurringEntry,
    occurrence_date: date,
) -> None:
    existing = (
        db.query(CreditCardPurchase)
        .filter(
            CreditCardPurchase.recurring_entry_id == entry.id,
            CreditCardPurchase.purchase_date == occurrence_date,
        )
        .first()
    )
    if existing is not None:
        return

    amount = Decimal(str(entry.amount))
    due_date = projected_card_due_date(entry, occurrence_date)
    purchase = CreditCardPurchase(
        user_id=entry.user_id,
        credit_card_id=entry.credit_card_id,
        category_id=entry.category_id,
        description=entry.description,
        total_amount=amount,
        installments=1,
        installment_amount=amount,
        purchase_date=occurrence_date,
        first_installment_date=due_date,
        category=entry.category,
        recurring_entry_id=entry.id,
    )
    db.add(purchase)
    db.flush()
    db.add(
        Installment(
            user_id=entry.user_id,
            purchase_id=purchase.id,
            installment_number=1,
            due_date=due_date,
            amount=amount,
        )
    )


def sync_recurring_entries(db: Session, user_id: uuid.UUID | str) -> int:
    """Materialize all active recurring occurrences up to today, idempotently."""
    today = date.today()
    entries = (
        db.query(RecurringEntry)
        .options(joinedload(RecurringEntry.credit_card))
        .filter(
            RecurringEntry.user_id == user_id,
            RecurringEntry.active.is_(True),
            RecurringEntry.start_date <= today,
        )
        .all()
    )

    generated = 0
    changed = False
    for entry in entries:
        next_date = (
            entry.start_date
            if entry.last_generated_date is None
            else advance_recurrence(entry.last_generated_date, entry.frequency)
        )

        while next_date <= today:
            if entry.end_date is not None and next_date > entry.end_date:
                break

            if entry.destination_type == "account":
                before = db.query(Transaction.id).filter(
                    Transaction.recurring_entry_id == entry.id,
                    Transaction.date == next_date,
                ).first()
                _materialize_account_occurrence(db, entry, next_date)
                if before is None:
                    generated += 1
            else:
                before = db.query(CreditCardPurchase.id).filter(
                    CreditCardPurchase.recurring_entry_id == entry.id,
                    CreditCardPurchase.purchase_date == next_date,
                ).first()
                _materialize_card_occurrence(db, entry, next_date)
                if before is None:
                    generated += 1

            entry.last_generated_date = next_date
            changed = True
            next_date = advance_recurrence(next_date, entry.frequency)

    if changed:
        db.commit()
    return generated
