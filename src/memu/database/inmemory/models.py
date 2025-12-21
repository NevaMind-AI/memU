from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, create_model

MemoryType = Literal["profile", "event", "knowledge", "behavior", "skill"]


class Resource(BaseModel):
    id: str
    url: str
    modality: str
    local_path: str
    caption: str | None = None
    embedding: list[float] | None = None
    updated_at: float | None = None


class MemoryItem(BaseModel):
    id: str
    resource_id: str
    memory_type: MemoryType
    summary: str
    embedding: list[float]
    updated_at: float | None = None


class MemoryCategory(BaseModel):
    id: str
    name: str
    description: str
    embedding: list[float] | None = None
    summary: str | None = None
    updated_at: float | None = None


class CategoryItem(BaseModel):
    item_id: str
    category_id: str


def build_memory_model(user_model: type[BaseModel], model: type[BaseModel]) -> type[BaseModel]:
    """
    Dynamically combine a user-provided model with one of the core memory models.
    The returned model inherits from both inputs so the combined schema includes fields from each.
    """
    if not issubclass(user_model, BaseModel):
        msg = "user_model must be a subclass of pydantic BaseModel"
        raise TypeError(msg)
    if not issubclass(model, BaseModel):
        msg = "model must be a subclass of pydantic BaseModel"
        raise TypeError(msg)

    if issubclass(model, user_model):
        return model

    combined_name = f"{user_model.__name__}{model.__name__}"
    base_name = f"{combined_name}Base"
    # Both user_model and model already inherit from BaseModel, so no need to include it again
    combined_base = type(base_name, (user_model, model), {"__module__": __name__})
    return create_model(combined_name, __base__=combined_base, __module__=__name__)


def build_memory_models(
    user_model: type[BaseModel],
) -> tuple[type[BaseModel], type[BaseModel], type[BaseModel], type[BaseModel], type[BaseModel]]:
    """
    Build memory models that merge the user model with each built-in memory model.
    """
    base_model_cls = build_memory_model(user_model, BaseModel)
    resource_model = build_memory_model(user_model, Resource)
    memory_item_model = build_memory_model(user_model, MemoryItem)
    memory_category_model = build_memory_model(user_model, MemoryCategory)
    category_item_model = build_memory_model(user_model, CategoryItem)
    return base_model_cls, resource_model, memory_item_model, memory_category_model, category_item_model
