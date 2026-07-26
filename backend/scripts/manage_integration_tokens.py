"""Create, list, and revoke TallyNorth integration tokens.

Run from the backend directory, for example:
    python scripts/manage_integration_tokens.py create --email you@example.com
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models.integration_token import IntegrationToken
from app.models.user import User
from app.schemas.integration import (
    DEFAULT_INTEGRATION_SCOPES,
    IntegrationTokenCreate,
)
from app.services.integration_tokens import (
    create_integration_token,
    parse_scopes,
)


def _find_user(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise ValueError(f"No TallyNorth user exists with email: {email}")
    return user


def create_token(args) -> int:
    with SessionLocal() as db:
        user = _find_user(db, args.email)
        expires_at = None
        if args.expires_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=args.expires_days
            )
        payload = IntegrationTokenCreate(
            name=args.name,
            scopes=args.scopes,
            expires_at=expires_at,
        )
        token, raw_token = create_integration_token(db, user.id, payload)

    print(f"Token ID: {token.id}")
    print(f"Name: {token.name}")
    print(f"Scopes: {token.scopes}")
    print("")
    print("Copy this token now; it will not be shown again:")
    print(raw_token)
    return 0


def list_tokens(args) -> int:
    with SessionLocal() as db:
        user = _find_user(db, args.email)
        tokens = (
            db.query(IntegrationToken)
            .filter(IntegrationToken.user_id == user.id)
            .order_by(IntegrationToken.created_at.desc())
            .all()
        )
        if not tokens:
            print("No integration tokens found.")
            return 0

        for token in tokens:
            state = "revoked" if token.revoked_at else "active"
            print(
                f"{token.id}  {token.token_prefix}...  {state}  "
                f"{','.join(sorted(parse_scopes(token.scopes)))}  {token.name}"
            )
    return 0


def revoke_token(args) -> int:
    with SessionLocal() as db:
        user = _find_user(db, args.email)
        token = (
            db.query(IntegrationToken)
            .filter(
                IntegrationToken.id == args.token_id,
                IntegrationToken.user_id == user.id,
            )
            .first()
        )
        if token is None:
            raise ValueError("Integration token not found for this user")
        if token.revoked_at is None:
            token.revoked_at = datetime.now(timezone.utc)
            db.commit()
        print(f"Revoked token: {token.id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage TallyNorth integration tokens"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--email", required=True)
    create_parser.add_argument("--name", default="Mi GPT de ChatGPT")
    create_parser.add_argument(
        "--scope",
        dest="scopes",
        action="append",
        choices=DEFAULT_INTEGRATION_SCOPES,
        default=None,
        help="Repeat this option to grant multiple scopes.",
    )
    create_parser.add_argument("--expires-days", type=int, default=None)
    create_parser.set_defaults(handler=create_token)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--email", required=True)
    list_parser.set_defaults(handler=list_tokens)

    revoke_parser = subparsers.add_parser("revoke")
    revoke_parser.add_argument("--email", required=True)
    revoke_parser.add_argument("--token-id", required=True)
    revoke_parser.set_defaults(handler=revoke_token)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "scopes", None) is None:
        args.scopes = list(DEFAULT_INTEGRATION_SCOPES)
    try:
        return args.handler(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
