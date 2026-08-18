from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.credit_card import CreditCard
from app.models.installment import Installment
from app.models.user import User
from app.routers.deps import get_current_active_user
from app.schemas.cashflow import DashboardSummary, MonthlyProjection
from app.services import cashflow_service
from app.services.recurring_entry_service import sync_recurring_entries
from app.services.transaction_sync_service import sync_credit_card_installments

router = APIRouter(prefix="/cashflow", tags=["Cashflow"])


def _sync_financial_state(db: Session, user_id) -> None:
    sync_recurring_entries(db, user_id)
    sync_credit_card_installments(db, user_id)


@router.get("/projection", response_model=list[MonthlyProjection])
def get_projection(
    months: int = Query(default=6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _sync_financial_state(db, current_user.id)
    today = date.today()
    start = date(today.year, today.month, 1)
    raw = cashflow_service.get_monthly_projection(
        db,
        start_date=start,
        num_months=months,
        user_id=current_user.id,
    )
    return [MonthlyProjection(**row) for row in raw]


@router.get("/summary", response_model=MonthlyProjection)
def get_month_summary(
    month: Optional[str] = Query(default=None, description="YYYY-MM, defaults to current month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _sync_financial_state(db, current_user.id)
    today = date.today()
    if month:
        year, m = int(month[:4]), int(month[5:7])
    else:
        year, m = today.year, today.month

    raw = cashflow_service.get_month_summary(
        db,
        year=year,
        month=m,
        user_id=current_user.id,
    )
    return MonthlyProjection(**raw)


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    projection_months: int = Query(default=6, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _sync_financial_state(db, current_user.id)
    today = date.today()
    current_month_str = f"{today.year:04d}-{today.month:02d}"

    summary_raw = cashflow_service.get_month_summary(
        db,
        year=today.year,
        month=today.month,
        user_id=current_user.id,
    )
    start = date(today.year, today.month, 1)
    projection_raw = cashflow_service.get_monthly_projection(
        db,
        start_date=start,
        num_months=projection_months,
        user_id=current_user.id,
    )
    projection = [MonthlyProjection(**row) for row in projection_raw]

    upcoming_raw = (
        db.query(Installment)
        .filter(
            Installment.user_id == current_user.id,
            Installment.due_date >= today,
            Installment.is_paid.is_(False),
        )
        .order_by(Installment.due_date)
        .limit(50)
        .all()
    )

    cards_map: dict[str, dict] = {}
    for inst in upcoming_raw:
        card: CreditCard = inst.purchase.credit_card
        card_key = str(card.id)
        if card_key not in cards_map:
            cards_map[card_key] = {
                "card_id": card_key,
                "card_name": card.name,
                "total_pending": Decimal("0"),
                "next_due_date": str(inst.due_date),
            }
        cards_map[card_key]["total_pending"] += Decimal(str(inst.amount))

    return DashboardSummary(
        current_month=current_month_str,
        total_income_mtd=Decimal(str(summary_raw.get("total_income", 0))),
        total_expenses_mtd=Decimal(str(summary_raw.get("total_expenses", 0))),
        total_installments_mtd=Decimal(str(summary_raw.get("total_installments", 0))),
        net_mtd=Decimal(str(summary_raw.get("net", 0))),
        upcoming_installments=list(cards_map.values()),
        projection=projection,
    )
