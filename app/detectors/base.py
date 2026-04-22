from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.schemas.alert import Alert

class BaseDetector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def supports(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """
        Returns True if this detector can handle the given event type.
        """
        pass

    @abstractmethod
    def detect(self, org_id: str, event_type: str, payload: Dict[str, Any], redis_client: Any) -> Optional[Alert]:
        """
        Analyzes the payload and returns an Alert if suspicious behavior is found.
        """
        pass
