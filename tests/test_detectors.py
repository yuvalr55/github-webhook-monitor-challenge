import pytest
from unittest.mock import MagicMock
from datetime import datetime
from app.detectors.push_time import PushTimeDetector
from app.detectors.hacker_team import HackerTeamDetector
from app.detectors.repo_deleted_fast import RepoDeletedFastDetector

def test_push_time_detector_triggered():
    detector = PushTimeDetector()
    # Provide a pushed_at in the suspicious window (14:30)
    payload = {
        "repository": {
            "full_name": "repo/test",
            "pushed_at": "2024-01-01T14:30:00Z"
        }
    }
    alert = detector.detect("test-org", "push", payload, None)
    assert alert is not None
    assert "Suspicious push time" in alert.message

def test_push_time_detector_not_triggered():
    detector = PushTimeDetector()
    # Provide a pushed_at outside the window (10:00)
    payload = {
        "repository": {
            "full_name": "repo/test",
            "pushed_at": "2024-01-01T10:00:00Z"
        }
    }
    alert = detector.detect("test-org", "push", payload, None)
    assert alert is None

def test_hacker_team_detector():
    detector = HackerTeamDetector()
    
    # Suspicious name
    alert = detector.detect("test-org", "team", {"action": "created", "team": {"name": "Hacker-Force"}}, None)
    assert alert is not None
    assert "Suspicious team name" in alert.message
    
    # Normal name
    alert = detector.detect("test-org", "team", {"action": "created", "team": {"name": "Dev-Team"}}, None)
    assert alert is None

def test_repo_deleted_fast_detector():
    detector = RepoDeletedFastDetector()
    redis_mock = MagicMock()
    
    # Simulate creation
    detector.detect("test-org", "repository", {"action": "created", "repository": {"full_name": "repo/test"}}, redis_mock)
    redis_mock.set.assert_called_once()
    
    # Simulate fast deletion
    import time
    start_time = time.time() - 60 # 1 min ago
    redis_mock.get.return_value = str(start_time)
    
    alert = detector.detect("test-org", "repository", {"action": "deleted", "repository": {"full_name": "repo/test"}}, redis_mock)
    assert alert is not None
    assert "deleted too quickly" in alert.message

    # Simulate slow deletion (>10 mins)
    start_time = time.time() - 700 # ~11 mins
    redis_mock.get.return_value = str(start_time)
    alert = detector.detect("test-org", "repository", {"action": "deleted", "repository": {"full_name": "repo/test"}}, redis_mock)
    assert alert is None
