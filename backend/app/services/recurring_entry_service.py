import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session, joinedload

from app.models.credit_card import CreditCard
from app.models.installment import Installment
from app.models.purchase import CreditCardPurchase
from app.models.recurring_entry import RecurringEntry
from app.models.recurring_occurrence import RecurringOccurrence
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
    """Return scheduled dates for an active entry inside an inclusive date window."""
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


def _get_or_create_occurrence(
    db: Session,
    entry: RecurringEntry,
    scheduled_date: date,
) -> tuple[RecurringOccurrence, bool]:
    occurrence = (
        db.query(RecurringOccurrence)
        .filter(
            RecurringOccurrence.recurring_entry_id == entry.id,
            RecurringOccurrence.scheduled_date == scheduled_date,
        )
        .first()
    )
    if occurrence is not None:
        return occurrence, False

    occurrence = RecurringOccurrence(
        user_id=entry.user_id,
        recurring_entry_id=entry.id,
        scheduled_date=scheduled_date,
        amount=entry.amount,
        status="pending",
    )
    db.add(occurrence)
    db.flush()
    return occurrence, True


def _materialize_account_occurrence(
    db: Session,
    occurrence: RecurringOccurrence,
    effective_date: date,
) -> None:
    entry = occurrence.entry
    existing = None
    if occurrence.transaction_id is not None:
        existing = db.query(Transaction).filter(Transaction.id == occurrence.transaction_id).first()
    if existing is None and effective_date == occurrence.scheduled_date:
        existing = (
            db.query(Transaction)
            .filter(
                Transaction.recurring_entry_id == entry.id,
                Transaction.date == occurrence.scheduled_date,
            )
            .first()
        )

    if existing is None:
        existing = Transaction(
            user_id=entry.user_id,
            account_id=entry.account_id,
            category_id=entry.category_id,
            type=entry.type,
            amount=occurrence.amount,
            description=entry.description,
            category=entry.category,
            date=effective_date,
            recurring_entry_id=entry.id,
        )
        db.add(existing)
        db.flush()

    occurrence.transaction_id = existing.id
    occurrence.status = "settled"
    occurrence.settled_at = datetime.now(timezone.utc)


def _materialize_card_occurrence(
    db: Session,
    occurrence: RecurringOccurrence,
    effective_date: date,
) -> None:
    entry = occurrence.entry
    existing = None
    if occurrence.purchase_id is not None:
        existing = db.query(CreditCardPurchase).filter(
            CreditCardPurchase.id == occurrence.purchase_id
        ).first()
    if existing is None and effective_date == occurrence.scheduled_date:
        existing = (
            db.query(CreditCardPurchase)
            .filter(
                CreditCardPurchase.recurring_entry_id == entry.id,
                CreditCardPurchase.purchase_date == occurrence.scheduled_date,
            )
            .first()
        )

    if existing is None:
        amount = Decimal(str(occurrence.amount))
        due_date = projected_card_due_date(entry, effective_date)
        existing = CreditCardPurchase(
            user_id=entry.user_id,
            credit_card_id=entry.credit_card_id,
            category_id=entry.category_id,
            description=entry.description,
            total_amount=amount,
            installments=1,
            installment_amount=amount,
            purchase_date=effective_date,
            first_installment_date=due_date,
            category=entry.category,
            recurring_entry_id=entry.id,
        )
        db.add(existing)
        db.flush()
        db.add(
            Installment(
                user_id=entry.user_id,
                purchase_id=existing.id,
                installment_number=1,
                due_date=due_date,
                amount=amount,
            )
        )

    occurrence.purchase_id = existing.id
    occurrence.status = "settled"
    occurrence.settled_at = datetime.now(timezone.utc)


def settle_occurrence(
    db: Session,
    occurrence: RecurringOccurrence,
    effective_date: date | None = None,
) -> RecurringOccurrence:
    """Materialize one pending occurrence as a real account/card movement."""
    if occurrence.status == "settled":
        return occurrence
    if occurrence.status == "skipped":
        raise ValueError("Skipped occurrences cannot be settled")

    effective_date = effective_date or date.today()
    if occurrence.entry.destination_type == "account":
        _materialize_account_occurrence(db, occurrence, effective_date)
    else:
        _materialize_card_occurrence(db, occurrence, effective_date)
    return occurrence


def sync_recurring_entries(db: Session, user_id: uuid.UUID | str) -> int:
    """Create due occurrences and auto-settle entries configured as automatic."""
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

    changed_count = 0
    changed = False
    for entry in entries:
        if entry.last_generated_date is None:
            next_date = entry.start_date
        elif entry.start_date > entry.last_generated_date:
            next_date = entry.start_date
        else:
            next_date = advance_recurrence(entry.last_generated_date, entry.frequency)

        while next_date <= today:
            if entry.end_date is not None and next_date > entry.end_date:
                break

            occurrence, created = _get_or_create_occurrence(db, entry, next_date)
            if created:
                changed_count += 1
                changed = True

            if entry.settlement_mode == "automatic" and occurrence.status == "pending":
                settle_occurrence(db, occurrence, effective_date=next_date)
                changed_count += 1
                changed = True

            entry.last_generated_date = next_date
            changed = True
            next_date = advance_recurrence(next_date, entry.frequency)

    if changed:
        db.commit()
    return changed_count
