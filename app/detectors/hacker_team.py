from typing import Optional, Dict, Any
from app.detectors.base import BaseDetector
from app.schemas.alert import Alert
from app.core.config import settings

class HackerTeamDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "hacker_team"

    def supports(self, event_type: str, payload: Dict[str, Any]) -> bool:
        if event_type != "team":
            return False
            
        action = payload.get("action")
        return action == "created"

    def detect(self, org_id: str, event_type: str, payload: Dict[str, Any], redis_client: Any) -> Optional[Alert]:
        team_name = payload.get("team", {}).get("name", "").lower()
        
        if team_name.startswith(settings.SUSPICIOUS_TEAM_PREFIX.lower()):
            return Alert(
                org_id=org_id,
                detector_name=self.name,
                message=f"Suspicious team name created: {team_name}",
                event_type=event_type,
                payload_summary=f"Team: {team_name}"
            )
            
        return None
