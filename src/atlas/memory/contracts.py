from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

MemoryKind = Literal["session", "episodic", "semantic", "project", "operational"]


class MemoryRecord(BaseModel):
    kind: MemoryKind
    content: str = Field(min_length=1, max_length=12000)
    source: str = Field(min_length=1, max_length=200)
    scope: str = Field(default="user", min_length=1, max_length=200)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
