from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.investment import Investment
from app.models.user import User
from app.schemas.investment import InvestmentCreate, InvestmentRead, InvestmentUpdate
from app.routers.deps import get_current_active_user

router = APIRouter(prefix="/investments", tags=["Investments"])


@router.get("/", response_model=list[InvestmentRead])
def list_investments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return db.query(Investment).filter(Investment.user_id == current_user.id).order_by(Investment.created_at.desc()).all()


@router.post("/", response_model=InvestmentRead, status_code=status.HTTP_201_CREATED)
def create_investment(
    payload: InvestmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    investment_data = payload.model_dump()
    investment_data["user_id"] = current_user.id
    investment = Investment(**investment_data)
    db.add(investment)
    db.commit()
    db.refresh(investment)
    return investment


@router.get("/{investment_id}", response_model=InvestmentRead)
def get_investment(
    investment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    investment = db.query(Investment).filter(Investment.id == investment_id, Investment.user_id == current_user.id).first()
    if not investment:
        raise HTTPException(status_code=404, detail="Investment not found")
    return investment


@router.put("/{investment_id}", response_model=InvestmentRead)
def update_investment(
    investment_id: str,
    payload: InvestmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    investment = db.query(Investment).filter(Investment.id == investment_id, Investment.user_id == current_user.id).first()
    if not investment:
        raise HTTPException(status_code=404, detail="Investment not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(investment, field, value)
    db.commit()
    db.refresh(investment)
    return investment


@router.delete("/{investment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investment(
    investment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    investment = db.query(Investment).filter(Investment.id == investment_id, Investment.user_id == current_user.id).first()
    if not investment:
        raise HTTPException(status_code=404, detail="Investment not found")
    db.delete(investment)
    db.commit()
