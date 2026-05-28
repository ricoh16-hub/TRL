from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ReferenceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None


__all__ = ["ReferenceItemResponse"]
