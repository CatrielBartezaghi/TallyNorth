import hashlib
import json

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.integration_token import GptActionRequest


def action_request_hash(payload: BaseModel) -> str:
    serialized = json.dumps(
        payload.model_dump(
            mode="json",
            exclude={"idempotency_key"},
            exclude_none=True,
        ),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def find_action_request(
    db: Session,
    user_id,
    operation: str,
    idempotency_key: str,
) -> GptActionRequest | None:
    return (
        db.query(GptActionRequest)
        .filter(
            GptActionRequest.user_id == user_id,
            GptActionRequest.operation == operation,
            GptActionRequest.idempotency_key == idempotency_key,
        )
        .first()
    )


def record_action_request(
    db: Session,
    *,
    user_id,
    integration_token_id,
    operation: str,
    idempotency_key: str,
    request_hash: str,
    resource_id,
    response_payload: dict | None = None,
) -> GptActionRequest:
    action_request = GptActionRequest(
        user_id=user_id,
        integration_token_id=integration_token_id,
        operation=operation,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        resource_id=resource_id,
        response_payload=response_payload,
    )
    db.add(action_request)
    db.flush()
    return action_request
