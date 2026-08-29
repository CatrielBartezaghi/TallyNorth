from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from sqlalchemy import func
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate, AccountAdjustBalance
from app.routers.deps import get_current_active_user
from app.services.account_balance_service import get_account_current_balance

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/", response_model=list[AccountRead])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    accounts = db.query(Account).filter(Account.user_id == current_user.id).order_by(Account.created_at.desc()).all()
    for account in accounts:
        account.current_balance = get_account_current_balance(db, account)
    return accounts


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    account_data = payload.model_dump()
    account_data["user_id"] = current_user.id
    account = Account(**account_data)
    db.add(account)
    db.commit()
    db.refresh(account)
    account.current_balance = account.initial_balance
    return account


@router.get("/{account_id}", response_model=AccountRead)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.current_balance = get_account_current_balance(db, account)
    return account


@router.put("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: str,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    db.commit()
    return get_account(account_id, db, current_user)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()


@router.post("/{account_id}/adjust", response_model=AccountRead)
def adjust_balance(
    account_id: str,
    payload: AccountAdjustBalance,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from decimal import Decimal
    from datetime import date
    
    account_with_balance = get_account(account_id, db, current_user)
    current_balance = Decimal(account_with_balance.current_balance)
    target_balance = Decimal(payload.target_balance)
    
    diff = target_balance - current_balance
    if diff != 0:
        tx = Transaction(
            user_id=current_user.id,
            account_id=account_with_balance.id,
            type="income" if diff > 0 else "expense",
            amount=abs(diff),
            description="Balance Adjustment",
            date=date.today()
        )
        db.add(tx)
        db.commit()
        
    return get_account(account_id, db, current_user)
