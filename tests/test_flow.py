import requests
import uuid
import time
import hmac
import hashlib
import json
import os
from dotenv import load_dotenv
import pytest

# Load environment variables for the secret
load_dotenv()
SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "your_github_secret_here")

def sign_payload(payload_dict: dict, secret: str) -> str:
    """Calculates the HMAC-SHA256 signature for a payload."""
    # Use the exact same JSON format that requests sends
    payload_json = json.dumps(payload_dict, separators=(',', ':'))
    hash_object = hmac.new(secret.encode("utf-8"), msg=payload_json.encode("utf-8"), digestmod=hashlib.sha256)
    return "sha256=" + hash_object.hexdigest()

def test_flow_interaction():
    server_url = "http://localhost:8000/api/v1/webhook"
    
    # Check if server is up
    try:
        requests.get("http://localhost:8000/", timeout=5)
    except requests.exceptions.ConnectionError:
        pytest.skip("Webhook server is not running. Skipping integration test.")

    print(f"\n🚀 Starting Full Flow Test (using secret: {SECRET[:4]}...)")
    
    # Helper to send signed requests
    def send_signed_request(payload, event_type):
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        signature = "sha256=" + hmac.new(SECRET.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": event_type,
            "X-GitHub-Delivery": str(uuid.uuid4()),
            "X-Hub-Signature-256": signature
        }
        return requests.post(server_url, data=payload_bytes, headers=headers)

    # 1. Send a suspicious team creation event
    print("\nStep 1: Sending suspicious 'hacker' team event...")
    payload1 = {
        "action": "created",
        "organization": {"login": "demo-org"},
        "team": {"name": "hacker-unlimited-access"}
    }
    response1 = send_signed_request(payload1, "team")
    print(f"Server Response: {response1.status_code} - {response1.json()}")
    assert response1.status_code == 200, f"Expected 200 but got {response1.status_code}"

    # 2. Send a fast repo deletion sequence
    print("\nStep 2: Simulating fast repo deletion flow...")
    repo_name = f"malicious-repo-{uuid.uuid4().hex[:4]}"
    
    payload2_create = {
        "action": "created",
        "organization": {"login": "demo-org"},
        "repository": {"full_name": repo_name}
    }
    resp_create = send_signed_request(payload2_create, "repository")
    assert resp_create.status_code == 200
    print(f"Sent 'repository created' for {repo_name}")
    
    time.sleep(1)
    
    payload2_delete = {
        "action": "deleted",
        "organization": {"login": "demo-org"},
        "repository": {"full_name": repo_name}
    }
    resp_delete = send_signed_request(payload2_delete, "repository")
    assert resp_delete.status_code == 200
    print(f"Sent 'repository deleted' for {repo_name}")

    # 3. Send a suspicious push time event (14:00-16:00 UTC)
    print("\nStep 3: Sending suspicious push event (at 15:00 UTC)...")
    payload3 = {
        "repository": {
            "full_name": "demo-org/secure-repo",
            "owner": {"login": "demo-org"},
            "pushed_at": "2026-04-22T15:00:00Z"
        }
    }
    response3 = send_signed_request(payload3, "push")
    print(f"Server Response: {response3.status_code} - {response3.json()}")
    assert response3.status_code == 200, f"Expected 200 but got {response3.status_code}"

    print("\n✅ All test events sent successfully!")
    print("Check the Worker console output to see the alerts for:")
    print(" - hacker-unlimited-access (Team creation)")
    print(f" - {repo_name} (Fast deletion)")
    print(" - secure-repo (Suspicious push time)")

if __name__ == "__main__":
    test_flow_interaction()

