import time
from typing import Optional, Dict, Any
from app.detectors.base import BaseDetector
from app.schemas.alert import Alert
from app.core.config import settings

class RepoDeletedFastDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "repo_deleted_fast"

    def supports(self, event_type: str, payload: Dict[str, Any]) -> bool:
        if event_type != "repository":
            return False
        
        action = payload.get("action")
        return action in ["created", "deleted"]

    def detect(self, org_id: str, event_type: str, payload: Dict[str, Any], redis_client: Any) -> Optional[Alert]:
        action = payload.get("action")
        repo_name = payload.get("repository", {}).get("full_name")
        
        if not repo_name:
            return None
            
        redis_key = f"repo:created_at:{repo_name}"
        
        if action == "created":
            # Store creation timestamp
            redis_client.set(redis_key, str(time.time()), ex=3600) # Expire in 1 hour
            return None
            
        if action == "deleted":
            created_at_str = redis_client.get(redis_key)
            if not created_at_str:
                return None
            
            created_at = float(created_at_str)
            deleted_at = time.time()
            diff_minutes = (deleted_at - created_at) / 60
            
            if diff_minutes < settings.REPO_DELETION_THRESHOLD_MINUTES:
                # Cleanup
                redis_client.delete(redis_key)
                
                return Alert(
                    org_id=org_id,
                    detector_name=self.name,
                    message=f"Repository '{repo_name}' deleted too quickly ({diff_minutes:.2f} minutes)",
                    event_type=event_type,
                    payload_summary=f"Repo: {repo_name}, Lifetime: {diff_minutes:.2f}m"
                )
        
        return None
