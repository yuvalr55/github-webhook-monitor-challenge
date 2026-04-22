import asyncio
import logging
import uuid
import json
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import get_redis_client
from app.core.scheduler import Scheduler
from app.core.notifier import ConsoleNotifier
from app.worker.processor import EventProcessor

setup_logging()
logger = logging.getLogger(__name__)

class Worker:
    def __init__(self):
        self.worker_id = f"worker:{uuid.uuid4().hex[:8]}"
        self.redis = get_redis_client()
        self.scheduler = Scheduler(self.redis)
        self.notifier = ConsoleNotifier()
        self.processor = EventProcessor(self.redis, self.notifier)
        self.running = True

    async def run(self):
        logger.info(f"Starting {self.worker_id}...")
        
        while self.running:
            try:
                # 1. Fetch next eligible organization (Lease it)
                logger.debug(f"[{self.worker_id}] Checking for next eligible organization...")
                org_id = await self.scheduler.lease_next_org()

                if not org_id:
                    await asyncio.sleep(settings.WORKER_IDLE_SLEEP_SECONDS)
                    continue

                # 2. Attempt to acquire org-level lock
                logger.debug(f"[{self.worker_id}] Attempting to acquire lock for org: {org_id}")
                if not await self.scheduler.acquire_org_lock(org_id, self.worker_id):
                    continue

                try:
                    # 3. Process a batch of events for this org
                    logger.debug(f"[{self.worker_id}] Processing batch for org: {org_id}")
                    processed_any = await self.process_org_batch(org_id)
                finally:
                    # 4. Release lock and mark as ready for next batch if work remains
                    logger.debug(f"[{self.worker_id}] Releasing lock for org: {org_id}")
                    await self.scheduler.release_org_lock(org_id, self.worker_id)

                    if processed_any:
                        await self.scheduler.complete_org_processing(org_id)
                    else:
                        logger.info(f"[{self.worker_id}] No more work for org: {org_id}. Removing from scheduler.")
                        await self.scheduler.remove_org(org_id)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def process_org_batch(self, org_id: str) -> bool:
        stream_key = f"stream:org:{org_id}"
        
        # Read batch from stream
        entries = await self.redis.xread({stream_key: "0-0"}, count=settings.BATCH_SIZE)
        
        if not entries:
            return False

        stream_name, stream_entries = entries[0]
        logger.info(f"[{self.worker_id}] Processing batch of {len(stream_entries)} events for organization: {org_id}")
        
        for entry_id, data in stream_entries:
            try:
                event_json = data.get("event")
                if event_json:
                    event_dict = json.loads(event_json)
                    await self.processor.process_event(
                        org_id=org_id,
                        event_type=event_dict["event_type"],
                        payload=event_dict["payload"]
                    )
                
                # Acknowledge
                await self.redis.xdel(stream_key, entry_id)
            except Exception as e:
                logger.error(f"Failed to process entry {entry_id}: {e}")

        # Check for fairness - if we processed a full batch, we assume more work might remain.
        return True


async def main():
    worker = Worker()
    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
