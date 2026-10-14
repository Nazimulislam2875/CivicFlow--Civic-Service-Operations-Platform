
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    action: str
    resource_type: str
    resource_id: int | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AuditLogList(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int


class AuditLogFilters(BaseModel):
    actor_id: int | None = None
    action: str | None = Field(default=None, max_length=100)
    resource_type: str | None = Field(default=None, max_length=100)
    resource_id: int | None = None
