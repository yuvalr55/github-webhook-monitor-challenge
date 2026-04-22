from pydantic import BaseModel
from typing import Dict, Any

class WebhookEvent(BaseModel):
    event_type: str
    delivery_id: str
    org_id: str
    payload: Dict[str, Any]
