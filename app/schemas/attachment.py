
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_request_id: int
    uploaded_by_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class AttachmentDownload(BaseModel):
    attachment: AttachmentRead
    download_url: str
