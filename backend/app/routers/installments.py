from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.installment import Installment
from app.models.user import User
from app.schemas.installment import InstallmentRead, InstallmentUpdate
from app.routers.deps import get_current_active_user

router = APIRouter(prefix="/installments", tags=["Installments"])


@router.put("/{installment_id}", response_model=InstallmentRead)
def update_installment(
    installment_id: str,
    payload: InstallmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    installment = db.query(Installment).filter(
        Installment.id == installment_id,
        Installment.user_id == current_user.id,
    ).first()
    if not installment:
        raise HTTPException(status_code=404, detail="Installment not found")

    installment.is_paid = payload.is_paid
    installment.paid_account_id = payload.paid_account_id if payload.is_paid else None
    installment.paid_at = datetime.now(timezone.utc) if payload.is_paid else None
    db.commit()
    db.refresh(installment)
    return installment
