import time
import logging
from typing import Optional
from redis.asyncio import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.scheduler_key = settings.SCHEDULER_KEY

    async def schedule_org(self, org_id: str, when_ts: Optional[float] = None) -> None:
        if when_ts is None:
            when_ts = time.time()
        await self.redis.zadd(self.scheduler_key, {org_id: when_ts}, nx=True)

    async def lease_next_org(self) -> Optional[str]:
        now = time.time()
        lease_until = now + settings.ORG_LEASE_DURATION_SECONDS

        lua_script = """
        local org = redis.call('zrangebyscore', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, 1)
        if #org > 0 then
            local org_id = org[1]
            redis.call('zadd', KEYS[1], ARGV[2], org_id)
            return org_id
        end
        return nil
        """
        org_id = await self.redis.eval(lua_script, 1, self.scheduler_key, now, lease_until)
        if org_id:
            return org_id.decode("utf-8") if isinstance(org_id, bytes) else org_id
        return None

    async def complete_org_processing(self, org_id: str, delay_seconds: float = 0.1) -> None:
        next_ts = time.time() + delay_seconds
        await self.redis.zadd(self.scheduler_key, {org_id: next_ts})

    async def acquire_org_lock(self, org_id: str, worker_id: str) -> bool:
        lock_key = f"lock:org:{org_id}"
        return bool(await self.redis.set(lock_key, worker_id, nx=True, ex=settings.ORG_LOCK_TTL_SECONDS))

    async def release_org_lock(self, org_id: str, worker_id: str) -> None:
        lock_key = f"lock:org:{org_id}"
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(lua_script, 1, lock_key, worker_id)

    async def remove_org(self, org_id: str) -> None:
        await self.redis.zrem(self.scheduler_key, org_id)
