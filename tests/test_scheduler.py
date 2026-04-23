import pytest
import time
from unittest.mock import AsyncMock
from app.core.scheduler import Scheduler
from app.core.config import settings

@pytest.fixture
def scheduler():
    """Fixture that creates a Scheduler with an AsyncMock Redis client."""
    redis_mock = AsyncMock()
    return Scheduler(redis_mock)

@pytest.mark.asyncio
async def test_schedule_org(scheduler):
    """Test adding an organization to the scheduler with NX=True (don't overwrite)."""
    await scheduler.schedule_org("org1")
    scheduler.redis.zadd.assert_called_once()
    args, kwargs = scheduler.redis.zadd.call_args
    assert kwargs["nx"] is True
    assert "org1" in args[1]

@pytest.mark.asyncio
async def test_lease_next_org_eligible(scheduler):
    """Test that an eligible organization is successfully leased and returned."""
    scheduler.redis.eval.return_value = b"org1"
    
    org_id = await scheduler.lease_next_org()
    assert org_id == "org1"
    scheduler.redis.eval.assert_called_once()

@pytest.mark.asyncio
async def test_lease_next_org_not_eligible(scheduler):
    """Test that lease_next_org returns None when no organizations are ready."""
    scheduler.redis.eval.return_value = None
    
    org_id = await scheduler.lease_next_org()
    assert org_id is None
    scheduler.redis.eval.assert_called_once()

@pytest.mark.asyncio
async def test_acquire_release_lock(scheduler):
    """Test the distributed lock mechanism for acquiring and releasing an organization."""
    scheduler.redis.set.return_value = True
    
    # Test lock acquisition
    assert await scheduler.acquire_org_lock("org1", "worker1") is True
    scheduler.redis.set.assert_called_once()
    
    # Test lock release
    await scheduler.release_org_lock("org1", "worker1")
    scheduler.redis.eval.assert_called_once()

@pytest.mark.asyncio
async def test_remove_org(scheduler):
    """Test that an organization is correctly removed from the scheduler."""
    await scheduler.remove_org("org1")
    scheduler.redis.zrem.assert_called_once_with(settings.SCHEDULER_KEY, "org1")
