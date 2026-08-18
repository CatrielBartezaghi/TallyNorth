from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead, CategoryType


class ChatGPTCategoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        description=(
            "Identificador único para esta operación. Reutilizalo solamente al "
            "reintentar exactamente la misma creación."
        ),
    )
    name: str = Field(min_length=1, max_length=100)
    type: CategoryType = "expense"
    color: str = Field(default="#38bdf8", min_length=1, max_length=20)
    icon: str | None = Field(default=None, max_length=50)


CategoryActionStatus = Literal["created", "existing", "already_processed"]


class ChatGPTCategoryResult(BaseModel):
    status: CategoryActionStatus
    message: str
    category: CategoryRead
