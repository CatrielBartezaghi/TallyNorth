import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.integration_token import IntegrationToken
from app.models.user import User
from app.schemas.integration import IntegrationTokenCreate


TOKEN_PREFIX = "tn_gpt_"


@dataclass(frozen=True)
class IntegrationPrincipal:
    user: User
    token: IntegrationToken
    scopes: frozenset[str]


def generate_integration_token() -> str:
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_integration_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def parse_scopes(scopes: str) -> frozenset[str]:
    return frozenset(scope for scope in scopes.split(" ") if scope)


def create_integration_token(
    db: Session,
    user_id,
    payload: IntegrationTokenCreate,
) -> tuple[IntegrationToken, str]:
    raw_token = generate_integration_token()
    token = IntegrationToken(
        user_id=user_id,
        name=payload.name,
        token_hash=hash_integration_token(raw_token),
        token_prefix=raw_token[:16],
        scopes=" ".join(payload.scopes),
        expires_at=payload.expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token, raw_token


def authenticate_integration_token(
    db: Session, raw_token: str
) -> IntegrationPrincipal | None:
    if not raw_token.startswith(TOKEN_PREFIX):
        return None

    token = (
        db.query(IntegrationToken)
        .filter(
            IntegrationToken.token_hash == hash_integration_token(raw_token),
            IntegrationToken.revoked_at.is_(None),
        )
        .first()
    )
    if token is None:
        return None

    now = datetime.now(timezone.utc)
    if token.expires_at is not None and token.expires_at <= now:
        return None

    user = (
        db.query(User)
        .filter(User.id == token.user_id, User.is_active.is_(True))
        .first()
    )
    if user is None:
        return None

    token.last_used_at = now
    db.commit()
    return IntegrationPrincipal(
        user=user,
        token=token,
        scopes=parse_scopes(token.scopes),
    )
