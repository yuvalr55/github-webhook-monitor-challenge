from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

class Alert(BaseModel):
    org_id: str
    detector_name: str
    message: str
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload_summary: Optional[str] = None
