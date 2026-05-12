from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).order_by(Account.created_at.desc()).all()


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    account = Account(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.put("/{account_id}", response_model=AccountRead)
def update_account(account_id: str, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()
