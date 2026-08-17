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
