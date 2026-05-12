from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.credit_card import CreditCard
from app.models.installment import Installment
from app.models.purchase import CreditCardPurchase
from app.schemas.purchase import PurchaseCreate, PurchaseRead, PurchaseUpdate
from app.services.installment_service import (
    compute_first_installment_date,
    compute_installment_amount,
    generate_installment_dates,
)

router = APIRouter(prefix="/purchases", tags=["Credit Card Purchases"])


@router.get("/", response_model=list[PurchaseRead])
def list_purchases(db: Session = Depends(get_db)):
    return db.query(CreditCardPurchase).order_by(CreditCardPurchase.created_at.desc()).all()


@router.post("/", response_model=PurchaseRead, status_code=status.HTTP_201_CREATED)
def create_purchase(payload: PurchaseCreate, db: Session = Depends(get_db)):
    """
    Create a credit card purchase and automatically generate all installment rows.
    Uses the card's closing_day and due_day to compute installment dates.
    """
    card = db.query(CreditCard).filter(CreditCard.id == str(payload.credit_card_id)).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found")

    installment_amount = compute_installment_amount(
        Decimal(str(payload.total_amount)), payload.installments
    )
    first_date = compute_first_installment_date(
        purchase_date=payload.purchase_date,
        closing_day=card.closing_day,
        due_day=card.due_day,
    )
    num_installments_to_generate = payload.installments - payload.starting_installment + 1
    due_dates = generate_installment_dates(first_date, num_installments_to_generate, card.due_day)

    purchase = CreditCardPurchase(
        credit_card_id=payload.credit_card_id,
        description=payload.description,
        total_amount=payload.total_amount,
        installments=payload.installments,
        installment_amount=installment_amount,
        purchase_date=payload.purchase_date,
        first_installment_date=first_date,
        category=payload.category,
    )
    db.add(purchase)
    db.flush()  # get purchase.id before creating children

    for i, due_date in enumerate(due_dates, start=payload.starting_installment):
        installment = Installment(
            purchase_id=purchase.id,
            installment_number=i,
            due_date=due_date,
            amount=installment_amount,
        )
        db.add(installment)

    db.commit()
    db.refresh(purchase)
    return purchase

@router.post("/bulk", response_model=list[PurchaseRead], status_code=status.HTTP_201_CREATED)
def create_purchases_bulk(payload: list[PurchaseCreate], db: Session = Depends(get_db)):
    """
    Create multiple credit card purchases and automatically generate all installment rows for each.
    """
    if not payload:
        return []

    card_ids = {str(p.credit_card_id) for p in payload}
    cards = {str(c.id): c for c in db.query(CreditCard).filter(CreditCard.id.in_(card_ids)).all()}

    missing_cards = card_ids - set(cards.keys())
    if missing_cards:
        raise HTTPException(status_code=404, detail=f"Credit card(s) not found: {missing_cards}")

    created_purchases = []

    for item in payload:
        card = cards[str(item.credit_card_id)]
        installment_amount = compute_installment_amount(
            Decimal(str(item.total_amount)), item.installments
        )
        first_date = compute_first_installment_date(
            purchase_date=item.purchase_date,
            closing_day=card.closing_day,
            due_day=card.due_day,
        )
        num_installments_to_generate = item.installments - item.starting_installment + 1
        due_dates = generate_installment_dates(first_date, num_installments_to_generate, card.due_day)

        purchase = CreditCardPurchase(
            credit_card_id=item.credit_card_id,
            description=item.description,
            total_amount=item.total_amount,
            installments=item.installments,
            installment_amount=installment_amount,
            purchase_date=item.purchase_date,
            first_installment_date=first_date,
            category=item.category,
        )
        db.add(purchase)
        db.flush()

        for i, due_date in enumerate(due_dates, start=item.starting_installment):
            installment = Installment(
                purchase_id=purchase.id,
                installment_number=i,
                due_date=due_date,
                amount=installment_amount,
            )
            db.add(installment)
        
        created_purchases.append(purchase)

    db.commit()
    for p in created_purchases:
        db.refresh(p)
    return created_purchases


@router.get("/{purchase_id}", response_model=PurchaseRead)
def get_purchase(purchase_id: str, db: Session = Depends(get_db)):
    purchase = db.query(CreditCardPurchase).filter(CreditCardPurchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


@router.put("/{purchase_id}", response_model=PurchaseRead)
def update_purchase(purchase_id: str, payload: PurchaseUpdate, db: Session = Depends(get_db)):
    purchase = db.query(CreditCardPurchase).filter(CreditCardPurchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(purchase, field, value)
    db.commit()
    db.refresh(purchase)
    return purchase


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase(purchase_id: str, db: Session = Depends(get_db)):
    """Deleting a purchase cascades to its installment rows."""
    purchase = db.query(CreditCardPurchase).filter(CreditCardPurchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    db.delete(purchase)
    db.commit()
