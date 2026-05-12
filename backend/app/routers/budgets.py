from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.budget import Budget
from app.schemas.budget import BudgetCreate, BudgetRead, BudgetUpdate

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get("/", response_model=list[BudgetRead])
def list_budgets(
    month: Optional[str] = Query(default=None, description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    query = db.query(Budget)
    if month:
        query = query.filter(Budget.period_start == date(int(month[:4]), int(month[5:7]), 1))
    return query.order_by(Budget.period_start.desc()).all()


@router.post("/", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_budget(payload: BudgetCreate, db: Session = Depends(get_db)):
    budget = Budget(**payload.model_dump())
    budget.period_start = date(budget.period_start.year, budget.period_start.month, 1)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/{budget_id}", response_model=BudgetRead)
def get_budget(budget_id: str, db: Session = Depends(get_db)):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.put("/{budget_id}", response_model=BudgetRead)
def update_budget(budget_id: str, payload: BudgetUpdate, db: Session = Depends(get_db)):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    data = payload.model_dump(exclude_none=True)
    if "period_start" in data:
        period = data["period_start"]
        data["period_start"] = date(period.year, period.month, 1)
    for field, value in data.items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: str, db: Session = Depends(get_db)):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(budget)
    db.commit()

