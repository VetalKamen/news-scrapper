from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    """
    Single document stored in the vector database.
    """

    id: str = Field(..., description="Stable unique ID (usually URL)")
    text: str = Field(..., description="Text used for embedding")
    metadata: dict = Field(default_factory=dict)
