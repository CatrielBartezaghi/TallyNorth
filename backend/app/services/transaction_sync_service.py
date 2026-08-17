import uuid
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models.transaction import Transaction

def _advance_recurrence(value: date, rule: str | None) -> date | None:
    if rule == "weekly":
        return value + timedelta(weeks=1)
    if rule == "monthly":
        return value + relativedelta(months=1)
    if rule == "yearly":
        return value + relativedelta(years=1)
    return None

def sync_recurring_transactions(db: Session, user_id: uuid.UUID | str):
    """
    Checks all recurring transactions for the user and generates physical 
    child occurrences up to today.
    """
    templates = db.query(Transaction).filter(
        Transaction.user_id == user_id, 
        Transaction.is_recurring == True
    ).all()
    
    today = date.today()
    new_records = 0
    
    for t in templates:
        # Find the latest generated occurrence
        latest_child = db.query(Transaction).filter(Transaction.parent_id == t.id).order_by(Transaction.date.desc()).first()
        
        # The starting point for generating new ones
        latest_date = latest_child.date if latest_child else t.date
        
        next_date = _advance_recurrence(latest_date, t.recurrence_rule)
        
        while next_date and next_date <= today:
            if t.end_date and next_date > t.end_date:
                break
            
            # Generate occurrence
            new_tx = Transaction(
                user_id=t.user_id,
                account_id=t.account_id,
                category_id=t.category_id,
                type=t.type,
                amount=t.amount,
                description=t.description,
                category=t.category,
                date=next_date,
                is_recurring=False,  # the child is not recurring
                parent_id=t.id
            )
            db.add(new_tx)
            new_records += 1
            
            next_date = _advance_recurrence(next_date, t.recurrence_rule)

    if new_records > 0:
        db.commit()


def get_closing_date(due_date: date, closing_day: int, due_day: int) -> date:
    """Calculate the statement closing date for a given due date."""
    import calendar
    if closing_day > due_day:
        # closing date is in the previous month
        if due_date.month == 1:
            month = 12
            year = due_date.year - 1
        else:
            month = due_date.month - 1
            year = due_date.year
    else:
        # closing date is in the same month
        month = due_date.month
        year = due_date.year
        
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(closing_day, max_day))


def sync_credit_card_installments(db: Session, user_id: uuid.UUID | str):
    """
    Checks all unpaid installments for the user. If the statement closing date
    has passed (today >= closing_date), marks the installment as paid automatically.
    If the card has a payment account, the balance is effectively deducted.
    """
    from app.models.installment import Installment
    from app.models.purchase import CreditCardPurchase
    from app.models.credit_card import CreditCard

    # Fetch all unpaid installments with their related purchase and card
    unpaid_installments = db.query(Installment).join(
        CreditCardPurchase, Installment.purchase_id == CreditCardPurchase.id
    ).join(
        CreditCard, CreditCardPurchase.credit_card_id == CreditCard.id
    ).filter(
        Installment.user_id == user_id,
        Installment.is_paid == False
    ).all()

    today = date.today()
    updated = False

    for installment in unpaid_installments:
        card = installment.purchase.credit_card
        
        closing_date = get_closing_date(
            due_date=installment.due_date,
            closing_day=card.closing_day,
            due_day=card.due_day
        )

        if today >= closing_date:
            installment.is_paid = True
            installment.paid_account_id = card.payment_account_id
            installment.paid_at = today  # Or we could use closing_date, but today reflects when the system processed it
            updated = True

    if updated:
        db.commit()
