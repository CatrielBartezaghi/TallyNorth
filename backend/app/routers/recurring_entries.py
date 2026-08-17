from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.recurring_entry import RecurringEntry
from app.models.user import User
from app.routers.deps import get_current_active_user
from app.schemas.recurring_entry import RecurringEntryCreate, RecurringEntryRead, RecurringEntryUpdate
from app.services.recurring_entry_service import sync_recurring_entries

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
        "destination_type": entry.destination_type,
        "account_id": entry.account_id,
        "credit_card_id": entry.credit_card_id,
    }
    merged.update(payload.model_dump(exclude_unset=True))
    validated = RecurringEntryCreate(**merged)
    category_name = _validate_references(db, current_user.id, validated)

    schedule_fields = {"frequency", "start_date", "destination_type", "account_id", "credit_card_id"}
    if schedule_fields.intersection(payload.model_dump(exclude_unset=True)):
        entry.last_generated_date = None

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
