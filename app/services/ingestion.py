import json
import logging
from redis import Redis
from app.schemas.event import WebhookEvent
from app.core.scheduler import Scheduler
from app.core.config import settings

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.scheduler = Scheduler(redis_client)

    async def ingest_event(self, event: WebhookEvent) -> bool:
        """
        Ingests the event into the durable Redis Stream and schedules the organization.
        Returns True if newly ingested, False if duplicate.
        """
        idp_key = f"event:seen:{event.delivery_id}"
        
        # 1. Idempotency check
        if self.redis.set(idp_key, "1", nx=True, ex=settings.DUPLICATE_CHECK_TTL) is None:
            logger.debug(f"Rejecting duplicate event {event.delivery_id} (Idempotency key: {idp_key})")
            return False

        # 2. Persist to Stream
        stream_key = f"stream:org:{event.org_id}"
        event_json = event.model_dump_json()
        
        logger.debug(f"Persisting {event.event_type} to stream: {stream_key}")
        # Add to stream (XADD)
        # We use * to let Redis generate the ID
        self.redis.xadd(stream_key, {"event": event_json})
        logger.info(f"Event {event.delivery_id} successfully persisted to {stream_key}")

        # 3. Schedule organization for processing
        logger.debug(f"Scheduling organization {event.org_id} for background processing.")
        self.scheduler.schedule_org(event.org_id)
        
        return True
