from abc import ABC, abstractmethod
import logging
from app.schemas.alert import Alert

logger = logging.getLogger(__name__)

class BaseNotifier(ABC):
    @abstractmethod
    def notify(self, alert: Alert) -> None:
        pass

class ConsoleNotifier(BaseNotifier):
    def notify(self, alert: Alert) -> None:
        print("\n" + "="*50, flush=True)
        print(f"🚨 SUSPICIOUS BEHAVIOR DETECTED 🚨", flush=True)
        print(f"Organization: {alert.org_id}", flush=True)
        print(f"Detector:     {alert.detector_name}", flush=True)
        print(f"Message:      {alert.message}", flush=True)
        print(f"Event Type:   {alert.event_type}", flush=True)
        print(f"Timestamp:    {alert.timestamp.isoformat()}", flush=True)
        if alert.payload_summary:
            print(f"Details:      {alert.payload_summary}", flush=True)
        print("="*50 + "\n", flush=True)
