import hmac
import hashlib
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends
from app.schemas.event import WebhookEvent
from app.api.dependencies import get_ingestion_service
from app.services.ingestion import IngestionService
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def handle_webhook(
    request: Request,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """
    Receives GitHub webhook events, persists them durably, and returns quickly.
    """
    try:
        # 1. Parse payload and headers
        webhook_data = await parse_github_webhook(request)
        event_type = webhook_data["event_type"]
        org_id = webhook_data["org_id"]

        # 2. Granular Event Filtering
        allowed_events = settings.ORG_SPECIFIC_EVENTS.get(org_id, settings.SUPPORTED_EVENTS)
        if event_type not in allowed_events:
            logger.info(f"Ignoring event type '{event_type}' for organization: {org_id}")
            return {"status": "ignored", "reason": "unsupported_event_type_for_org", "org_id": org_id}

        # 3. Create internal model (Schema)
        logger.debug(f"Processing event: {event_type} for org: {org_id}")
        event = WebhookEvent(
            event_type=webhook_data["event_type"],
            delivery_id=webhook_data["delivery_id"],
            org_id=webhook_data["org_id"],
            payload=webhook_data["payload"]
        )
        
        # 3. Ingest durably using the injected service
        is_new = await ingestion_service.ingest_event(event)
        
        if is_new:
            return {"status": "accepted", "delivery_id": event.delivery_id}
        else:
            return {"status": "ignored", "reason": "duplicate", "delivery_id": event.delivery_id}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

async def parse_github_webhook(request: Request) -> Dict[str, Any]:
    """
    Parses GitHub webhook headers and body with signature verification.
    """
    event_type = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    signature = request.headers.get("X-Hub-Signature-256")
    
    if not event_type or not delivery_id:
        raise HTTPException(status_code=400, detail="Missing GitHub headers")

    # 2. Get raw body for verification
    body = await request.body()
    
    # 3. Verify Signature
    if not verify_signature(body, settings.GITHUB_WEBHOOK_SECRET, signature):
        logger.warning(f"Invalid signature for delivery: {delivery_id}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 4. Parse JSON
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    logger.debug(f"Webhook received. Event: {event_type}, Delivery: {delivery_id}, Payload keys: {list(payload.keys())}")
    
    # Extract Organization/Owner ID
    # Following GitHub's schema: org events have 'organization', repo events have 'repository.owner'
    org_id = None
    if "organization" in payload:
        org_id = payload["organization"].get("login")
    elif "repository" in payload:
        org_id = payload["repository"].get("owner", {}).get("login")

    if not org_id:
        logger.error(f"Event {delivery_id} ({event_type}) missing organization/owner context. Dropping.")
        raise HTTPException(status_code=400, detail="Could not identify organization or repository owner")
    
    org_id = str(org_id)
    
    return {
        "event_type": event_type,
        "delivery_id": delivery_id,
        "signature": signature,
        "org_id": org_id,
        "payload": payload
    }

def verify_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    """
    Verifies that the webhook signature matches our secret.
    """
    if not signature_header:
        return False
        
    hash_object = hmac.new(
        secret.encode("utf-8"), 
        msg=payload_body, 
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)
