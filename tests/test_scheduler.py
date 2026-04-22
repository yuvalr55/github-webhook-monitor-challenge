import pytest
import time
from unittest.mock import MagicMock
from app.core.scheduler import Scheduler
from app.core.config import settings

@pytest.fixture
def scheduler():
    redis_mock = MagicMock()
    # Mock settings if needed
    return Scheduler(redis_mock)

def test_schedule_org(scheduler):
    scheduler.schedule_org("org1")
    scheduler.redis.zadd.assert_called_once()
    args, kwargs = scheduler.redis.zadd.call_args
    assert kwargs["nx"] is True
    assert "org1" in args[1]

def test_lease_next_org_eligible(scheduler):
    # Mock eval to return an org_id (it's eligible)
    scheduler.redis.eval.return_value = "org1"
    
    org_id = scheduler.lease_next_org()
    assert org_id == "org1"
    scheduler.redis.eval.assert_called_once()

def test_lease_next_org_not_eligible(scheduler):
    # Mock eval to return None (no eligible org)
    scheduler.redis.eval.return_value = None
    
    org_id = scheduler.lease_next_org()
    assert org_id is None
    scheduler.redis.eval.assert_called_once()

def test_acquire_release_lock(scheduler):
    scheduler.redis.set.return_value = True
    
    assert scheduler.acquire_org_lock("org1", "worker1") is True
    scheduler.redis.set.assert_called_once()
    
    scheduler.release_org_lock("org1", "worker1")
    scheduler.redis.eval.assert_called_once()

def test_remove_org(scheduler):
    scheduler.remove_org("org1")
    scheduler.redis.zrem.assert_called_once_with(settings.SCHEDULER_KEY, "org1")
