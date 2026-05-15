from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account import Account
from app.models.user import User
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.routers.deps import get_current_active_user

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/", response_model=list[AccountRead])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return db.query(Account).filter(Account.user_id == current_user.id).order_by(Account.created_at.desc()).all()


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
    return account


@router.get("/{account_id}", response_model=AccountRead)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
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
    db.refresh(account)
    return account


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
