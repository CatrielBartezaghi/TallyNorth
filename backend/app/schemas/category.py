import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


CategoryType = Literal["income", "expense", "both"]


class CategoryBase(BaseModel):
    name: str
    type: CategoryType = "expense"
    color: str = "#38bdf8"
    icon: str | None = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    type: CategoryType | None = None
    color: str | None = None
    icon: str | None = None
    is_active: bool | None = None


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime

