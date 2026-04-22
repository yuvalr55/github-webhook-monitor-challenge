import time
import logging
from typing import Optional
from redis import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.scheduler_key = settings.SCHEDULER_KEY

    def schedule_org(self, org_id: str, when_ts: Optional[float] = None) -> None:
        """
        Adds or updates an organization in the fair scheduler.
        score is the timestamp when it becomes eligible for processing.
        Using NX=True to only add if it doesn't exist (e.g. during ingestion).
        """
        if when_ts is None:
            when_ts = time.time()
        
        self.redis.zadd(self.scheduler_key, {org_id: when_ts}, nx=True)

    def lease_next_org(self) -> Optional[str]:
        """
        Atomically finds the next eligible org and 'leases' it by pushing its 
        score into the future. This is the Visibility Timeout pattern.
        
        Returns org_id or None.
        """
        now = time.time()
        lease_until = now + settings.ORG_LEASE_DURATION_SECONDS

        # Lua script for atomic 'Get and Update Score'
        lua_script = """
        local org = redis.call('zrangebyscore', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, 1)
        if #org > 0 then
            local org_id = org[1]
            redis.call('zadd', KEYS[1], ARGV[2], org_id)
            return org_id
        end
        return nil
        """
        org_id = self.redis.eval(lua_script, 1, self.scheduler_key, now, lease_until)
        
        if org_id:
            return org_id.decode('utf-8') if isinstance(org_id, bytes) else org_id
        return None

    def complete_org_processing(self, org_id: str, delay_seconds: float = 0.1) -> None:
        """
        Called when a worker finishes a batch. Resets the org score to 'now' 
        (plus a tiny delay for fairness) so it's eligible again.
        """
        next_ts = time.time() + delay_seconds
        self.redis.zadd(self.scheduler_key, {org_id: next_ts})

    def acquire_org_lock(self, org_id: str, worker_id: str) -> bool:
        """
        Distributed lock for extra safety (concurrency protection).
        """
        lock_key = f"lock:org:{org_id}"
        return bool(self.redis.set(
            lock_key, 
            worker_id, 
            nx=True, 
            ex=settings.ORG_LOCK_TTL_SECONDS
        ))

    def release_org_lock(self, org_id: str, worker_id: str) -> None:
        """
        Releases the distributed lock safely.
        """
        lock_key = f"lock:org:{org_id}"
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.redis.eval(lua_script, 1, lock_key, worker_id)

    def remove_org(self, org_id: str) -> None:
        """
        Removes an organization from the scheduler.
        """
        self.redis.zrem(self.scheduler_key, org_id)
