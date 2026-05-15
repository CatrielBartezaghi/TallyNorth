from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.credit_card import CreditCard
from app.models.installment import Installment
from app.models.user import User
from app.schemas.credit_card import CreditCardCreate, CreditCardRead, CreditCardUpdate
from app.schemas.installment import InstallmentRead
from app.routers.deps import get_current_active_user

router = APIRouter(prefix="/credit-cards", tags=["Credit Cards"])


@router.get("/", response_model=list[CreditCardRead])
def list_credit_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return db.query(CreditCard).filter(CreditCard.user_id == current_user.id).order_by(CreditCard.created_at.desc()).all()


@router.post("/", response_model=CreditCardRead, status_code=status.HTTP_201_CREATED)
def create_credit_card(
    payload: CreditCardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    card_data = payload.model_dump()
    card_data["user_id"] = current_user.id
    card = CreditCard(**card_data)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.get("/{card_id}", response_model=CreditCardRead)
def get_credit_card(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    card = db.query(CreditCard).filter(CreditCard.id == card_id, CreditCard.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found")
    return card


@router.put("/{card_id}", response_model=CreditCardRead)
def update_credit_card(
    card_id: str,
    payload: CreditCardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    card = db.query(CreditCard).filter(CreditCard.id == card_id, CreditCard.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(card, field, value)
    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credit_card(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    card = db.query(CreditCard).filter(CreditCard.id == card_id, CreditCard.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found")
    db.delete(card)
    db.commit()


@router.get("/{card_id}/installments", response_model=list[InstallmentRead])
def list_card_installments(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return all pending installments for a given credit card."""
    card = db.query(CreditCard).filter(CreditCard.id == card_id, CreditCard.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found")

    installments = (
        db.query(Installment)
        .join(Installment.purchase)
        .filter(Installment.purchase.has(credit_card_id=card_id))
        .filter(Installment.is_paid == False)  # noqa: E712
        .order_by(Installment.due_date)
        .all()
    )
    return installments
