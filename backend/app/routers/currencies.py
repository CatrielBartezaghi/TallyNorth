from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.currency import Currency
from app.models.user import User
from app.schemas.currency import CurrencyCreate, CurrencyRead, CurrencyUpdate
from app.routers.deps import get_current_active_user

router = APIRouter(prefix="/currencies", tags=["Currencies"])


@router.get("/", response_model=list[CurrencyRead])
def list_currencies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return db.query(Currency).order_by(Currency.code).all()


@router.post("/", response_model=CurrencyRead, status_code=status.HTTP_201_CREATED)
def create_currency(
    payload: CurrencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    existing = db.query(Currency).filter(Currency.code == payload.code.upper()).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Currency with code '{payload.code}' already exists")
    currency = Currency(**payload.model_dump() | {"code": payload.code.upper()})
    db.add(currency)
    db.commit()
    db.refresh(currency)
    return currency


@router.get("/{currency_id}", response_model=CurrencyRead)
def get_currency(
    currency_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    return currency


@router.put("/{currency_id}", response_model=CurrencyRead)
def update_currency(
    currency_id: str,
    payload: CurrencyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(currency, field, value)
    db.commit()
    db.refresh(currency)
    return currency


@router.delete("/{currency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_currency(
    currency_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    db.delete(currency)
    db.commit()
