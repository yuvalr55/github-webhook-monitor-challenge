from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.detectors.base import BaseDetector
from app.schemas.alert import Alert
from app.core.config import settings

class PushTimeDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "push_time"

    def supports(self, event_type: str, payload: Dict[str, Any]) -> bool:
        return event_type == "push"

    async def detect(self, org_id: str, event_type: str, payload: Dict[str, Any], redis_client: Any) -> Optional[Alert]:
        # Try to get the push time from the payload, fallback to now
        # GitHub push events have many timestamp fields, we'll try to find one
        pushed_at_str = payload.get("repository", {}).get("pushed_at")
        if not pushed_at_str:
            return None
            
        try:
            # GitHub timestamps can be numeric (seconds) or ISO strings
            if isinstance(pushed_at_str, (int, float)):
                dt = datetime.fromtimestamp(pushed_at_str, tz=timezone.utc)
            else:
                # Generic ISO parser (simplified for demo)
                dt = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            # If the data is corrupted, we can't reliably detect push time
            return None

        hour = dt.hour
        
        if settings.SUSPICIOUS_PUSH_START_HOUR <= hour < settings.SUSPICIOUS_PUSH_END_HOUR:
            repo_name = payload.get("repository", {}).get("full_name", "unknown")
            return Alert(
                org_id=org_id,
                detector_name=self.name,
                message=f"Suspicious push time detected: {dt.strftime('%H:%M:%S')} UTC",
                event_type=event_type,
                payload_summary=f"Repo: {repo_name}"
            )

        return None
