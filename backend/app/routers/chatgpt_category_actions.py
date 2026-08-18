from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.routers.chatgpt_actions import (
    WRITE_ACTION,
    _conflict,
    _existing_action_request,
    _owned_resource,
    require_integration_scope,
)
from app.schemas.chatgpt_category import ChatGPTCategoryCreate, ChatGPTCategoryResult
from app.services.gpt_action_idempotency import (
    action_request_hash,
    record_action_request,
)
from app.services.integration_tokens import IntegrationPrincipal


router = APIRouter(prefix="/integrations/chatgpt", tags=["ChatGPT Actions"])


def _existing_category_result(
    db: Session,
    user_id,
    payload: ChatGPTCategoryCreate,
    request_hash: str,
) -> ChatGPTCategoryResult | None:
    action_request = _existing_action_request(
        db,
        user_id,
        "createCategory",
        payload.idempotency_key,
        request_hash,
    )
    if action_request is None:
        return None
    category = _owned_resource(
        db,
        Category,
        action_request.resource_id,
        user_id,
        "category",
    )
    return ChatGPTCategoryResult(
        status="already_processed",
        message="This request was already processed; no duplicate was created.",
        category=category,
    )


@router.post(
    "/categories",
    response_model=ChatGPTCategoryResult,
    operation_id="createCategory",
    summary="Crear una categoría financiera",
    description=(
        "Crea una categoría confirmada para usarla luego en movimientos o compras. "
        "Si ya existe con el mismo nombre y tipo, devuelve la existente."
    ),
    openapi_extra=WRITE_ACTION,
)
def create_category_action(
    payload: ChatGPTCategoryCreate,
    db: Session = Depends(get_db),
    principal: IntegrationPrincipal = Depends(
        require_integration_scope("transactions:create")
    ),
):
    user_id = principal.user.id
    request_hash = action_request_hash(payload)
    existing_request = _existing_category_result(db, user_id, payload, request_hash)
    if existing_request is not None:
        return existing_request

    existing_category = (
        db.query(Category)
        .filter(
            Category.user_id == user_id,
            func.lower(Category.name) == payload.name.lower(),
        )
        .first()
    )
    if existing_category is not None:
        if existing_category.type != payload.type:
            raise _conflict(
                f"Category '{existing_category.name}' already exists with type "
                f"'{existing_category.type}'",
                "category_name_conflict",
            )
        if not existing_category.is_active:
            existing_category.is_active = True
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="createCategory",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=existing_category.id,
        )
        db.commit()
        db.refresh(existing_category)
        return ChatGPTCategoryResult(
            status="existing",
            message="Category already existed; no duplicate was created.",
            category=existing_category,
        )

    category = Category(
        user_id=user_id,
        name=payload.name,
        type=payload.type,
        color=payload.color,
        icon=payload.icon,
        is_active=True,
    )
    try:
        db.add(category)
        db.flush()
        record_action_request(
            db,
            user_id=user_id,
            integration_token_id=principal.token.id,
            operation="createCategory",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            resource_id=category.id,
        )
        db.commit()
        db.refresh(category)
    except IntegrityError as exc:
        db.rollback()
        existing_request = _existing_category_result(db, user_id, payload, request_hash)
        if existing_request is not None:
            return existing_request
        raise _conflict(
            "The category could not be created because its name already exists",
            "category_name_conflict",
        ) from exc

    return ChatGPTCategoryResult(
        status="created",
        message="Category created successfully.",
        category=category,
    )
