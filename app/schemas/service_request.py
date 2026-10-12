
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RequestStatus = Literal["SUBMITTED", "IN_PROGRESS", "RESOLVED", "REJECTED"]
RequestPriority = Literal["LOW", "MEDIUM", "HIGH"]


class ServiceRequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    category_id: int = Field(gt=0)
    priority: RequestPriority = "MEDIUM"
    location: str | None = Field(default=None, max_length=300)


class ServiceRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=5)
    category_id: int | None = Field(default=None, gt=0)
    priority: RequestPriority | None = None
    location: str | None = Field(default=None, max_length=300)


class ServiceRequestResponse(BaseModel):
    id: int
    title: str
    description: str
    status: RequestStatus
    priority: RequestPriority
    citizen_id: int
    assigned_staff_id: int | None = None
    category_id: int
    department_id: int | None
    location: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceRequestListResponse(BaseModel):
    items: list[ServiceRequestResponse]
    total: int
    page: int
    page_size: int


class StaffAssignment(BaseModel):
    staff_id: int = Field(gt=0)


class RequestStatusUpdate(BaseModel):
    status: RequestStatus
    note: str | None = Field(default=None, max_length=1000)


class RequestStatusHistoryResponse(BaseModel):
    id: int
    request_id: int
    changed_by_id: int
    old_status: str | None
    new_status: RequestStatus
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
