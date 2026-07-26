from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.finance_agent import build_assistant_draft
from app.agents.schemas import AssistantDraftRequest, AssistantDraftResponse
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.routers.deps import get_current_active_user

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/draft", response_model=AssistantDraftResponse)
async def create_assistant_draft(
    payload: AssistantDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured",
        )

    try:
        return await build_assistant_draft(db, current_user.id, payload.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Assistant draft failed: {exc}",
        ) from exc
