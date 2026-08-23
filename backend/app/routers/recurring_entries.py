from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.recurring_entry import RecurringEntry
from app.models.recurring_occurrence import RecurringOccurrence
from app.models.user import User
from app.routers.deps import get_current_active_user
from app.schemas.recurring_entry import (
    RecurringEntryCreate,
    RecurringEntryRead,
    RecurringEntryUpdate,
    RecurringOccurrenceRead,
    RecurringOccurrenceSettle,
)
from app.services.recurring_entry_service import settle_occurrence, sync_recurring_entries

router = APIRouter(prefix="/recurring-entries", tags=["Recurring Entries"])


def _validate_references(db: Session, user_id, payload: RecurringEntryCreate) -> str | None:
    if payload.destination_type == "account":
        target = db.query(Account).filter(Account.id == payload.account_id, Account.user_id == user_id).first()
        if target is None:
            raise HTTPException(status_code=404, detail="Account not found")
    else:
        target = db.query(CreditCard).filter(CreditCard.id == payload.credit_card_id, CreditCard.user_id == user_id).first()
        if target is None:
            raise HTTPException(status_code=404, detail="Credit card not found")

    if payload.category_id is None:
        return None
    category = db.query(Category).filter(
        Category.id == payload.category_id,
        Category.user_id == user_id,
        Category.is_active.is_(True),
    ).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.type not in (payload.type, "both"):
        raise HTTPException(status_code=422, detail="Category does not match recurring entry type")
    return category.name


@router.get("/", response_model=list[RecurringEntryRead])
def list_recurring_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    sync_recurring_entries(db, current_user.id)
    return db.query(RecurringEntry).filter(RecurringEntry.user_id == current_user.id).order_by(RecurringEntry.created_at.desc()).all()


@router.post("/", response_model=RecurringEntryRead, status_code=status.HTTP_201_CREATED)
def create_recurring_entry(
    payload: RecurringEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    category_name = _validate_references(db, current_user.id, payload)
    entry = RecurringEntry(user_id=current_user.id, category=category_name, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    sync_recurring_entries(db, current_user.id)
    db.refresh(entry)
    return entry


@router.get("/occurrences/", response_model=list[RecurringOccurrenceRead])
def list_recurring_occurrences(
    occurrence_status: str | None = Query(default=None, alias="status", pattern="^(pending|settled|skipped)$"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    sync_recurring_entries(db, current_user.id)
    query = (
        db.query(RecurringOccurrence)
        .options(joinedload(RecurringOccurrence.entry))
        .filter(RecurringOccurrence.user_id == current_user.id)
    )
    if occurrence_status:
        query = query.filter(RecurringOccurrence.status == occurrence_status)
    if date_from:
        query = query.filter(RecurringOccurrence.scheduled_date >= date_from)
    if date_to:
        query = query.filter(RecurringOccurrence.scheduled_date <= date_to)
    return query.order_by(RecurringOccurrence.scheduled_date.desc()).all()


@router.post("/occurrences/{occurrence_id}/settle", response_model=RecurringOccurrenceRead)
def settle_recurring_occurrence(
    occurrence_id: str,
    payload: RecurringOccurrenceSettle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    occurrence = (
        db.query(RecurringOccurrence)
        .options(
            joinedload(RecurringOccurrence.entry).joinedload(RecurringEntry.credit_card),
        )
        .filter(
            RecurringOccurrence.id == occurrence_id,
            RecurringOccurrence.user_id == current_user.id,
        )
        .first()
    )
    if occurrence is None:
        raise HTTPException(status_code=404, detail="Recurring occurrence not found")

    try:
        settle_occurrence(db, occurrence, effective_date=payload.effective_date)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(occurrence)
    return occurrence


@router.post("/occurrences/{occurrence_id}/skip", response_model=RecurringOccurrenceRead)
def skip_recurring_occurrence(
    occurrence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    occurrence = (
        db.query(RecurringOccurrence)
        .options(joinedload(RecurringOccurrence.entry))
        .filter(
            RecurringOccurrence.id == occurrence_id,
            RecurringOccurrence.user_id == current_user.id,
        )
        .first()
    )
    if occurrence is None:
        raise HTTPException(status_code=404, detail="Recurring occurrence not found")
    if occurrence.status == "settled":
        raise HTTPException(status_code=409, detail="Settled occurrences cannot be skipped")
    occurrence.status = "skipped"
    db.commit()
    db.refresh(occurrence)
    return occurrence


@router.put("/{entry_id}", response_model=RecurringEntryRead)
def update_recurring_entry(
    entry_id: str,
    payload: RecurringEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    entry = db.query(RecurringEntry).filter(RecurringEntry.id == entry_id, RecurringEntry.user_id == current_user.id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Recurring entry not found")

    merged = {
        "type": entry.type,
        "amount": entry.amount,
        "description": entry.description,
        "category_id": entry.category_id,
        "frequency": entry.frequency,
        "start_date": entry.start_date,
        "end_date": entry.end_date,
        "active": entry.active,
        "settlement_mode": entry.settlement_mode,
        "destination_type": entry.destination_type,
        "account_id": entry.account_id,
        "credit_card_id": entry.credit_card_id,
    }
    merged.update(payload.model_dump(exclude_unset=True))
    validated = RecurringEntryCreate(**merged)
    category_name = _validate_references(db, current_user.id, validated)

    # Materialized and already-due occurrences are financial history. Editing
    # the rule only changes occurrences that have not been generated yet.
    for field, value in validated.model_dump().items():
        setattr(entry, field, value)
    entry.category = category_name
    db.commit()
    db.refresh(entry)
    sync_recurring_entries(db, current_user.id)
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    entry = db.query(RecurringEntry).filter(RecurringEntry.id == entry_id, RecurringEntry.user_id == current_user.id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Recurring entry not found")
    db.delete(entry)
    db.commit()
