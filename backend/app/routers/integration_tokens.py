from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.integration_token import IntegrationToken
from app.models.user import User
from app.routers.deps import get_current_active_user
from app.schemas.integration import (
    IntegrationTokenCreate,
    IntegrationTokenCreated,
    IntegrationTokenRead,
)
from app.services.integration_tokens import (
    create_integration_token,
    parse_scopes,
)


router = APIRouter(prefix="/integration-tokens", tags=["Integration Tokens"])


def _token_read(token: IntegrationToken) -> IntegrationTokenRead:
    return IntegrationTokenRead(
        id=token.id,
        name=token.name,
        token_prefix=token.token_prefix,
        scopes=list(parse_scopes(token.scopes)),
        expires_at=token.expires_at,
        revoked_at=token.revoked_at,
        last_used_at=token.last_used_at,
        created_at=token.created_at,
    )


@router.get("/", response_model=list[IntegrationTokenRead])
def list_integration_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    tokens = (
        db.query(IntegrationToken)
        .filter(IntegrationToken.user_id == current_user.id)
        .order_by(IntegrationToken.created_at.desc())
        .all()
    )
    return [_token_read(token) for token in tokens]


@router.post(
    "/",
    response_model=IntegrationTokenCreated,
    status_code=status.HTTP_201_CREATED,
)
def issue_integration_token(
    payload: IntegrationTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    token, raw_token = create_integration_token(db, current_user.id, payload)
    return IntegrationTokenCreated(
        **_token_read(token).model_dump(),
        token=raw_token,
    )


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_integration_token(
    token_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    token = (
        db.query(IntegrationToken)
        .filter(
            IntegrationToken.id == token_id,
            IntegrationToken.user_id == current_user.id,
        )
        .first()
    )
    if token is None:
        raise HTTPException(status_code=404, detail="Integration token not found")

    if token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return None
