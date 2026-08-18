import uuid
from datetime import date

from sqlalchemy.orm import Session


def sync_credit_card_installments(db: Session, user_id: uuid.UUID | str) -> None:
    """Automatically pay due installments using the card's configured payment account."""
    from app.models.credit_card import CreditCard
    from app.models.installment import Installment
    from app.models.purchase import CreditCardPurchase

    unpaid_installments = (
        db.query(Installment)
        .join(CreditCardPurchase, Installment.purchase_id == CreditCardPurchase.id)
        .join(CreditCard, CreditCardPurchase.credit_card_id == CreditCard.id)
        .filter(
            Installment.user_id == user_id,
            Installment.is_paid.is_(False),
        )
        .all()
    )

    today = date.today()
    updated = False
    for installment in unpaid_installments:
        card = installment.purchase.credit_card
        if card.payment_account_id is None or today < installment.due_date:
            continue
        installment.is_paid = True
        installment.paid_account_id = card.payment_account_id
        installment.paid_at = today
        updated = True

    if updated:
        db.commit()
