from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import build_dashboard_summary
from app.routers.deps import get_current_active_user
from app.services.transaction_sync_service import sync_recurring_transactions

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    currency: str = Query(default="USD", min_length=3, max_length=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="to must be after from")
    
    sync_recurring_transactions(db, current_user.id)
    
    try:
        return build_dashboard_summary(db, date_from=date_from, date_to=date_to, currency_code=currency.upper(), user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
