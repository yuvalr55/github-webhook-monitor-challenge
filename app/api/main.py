import logging
import time
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import get_redis_client
from app.services.ingestion import IngestionService
from app.api.v1.api import api_router

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = get_redis_client()
    app.state.ingestion_service = IngestionService(app.state.redis)
    logger.info("Webhook server resources initialized.")
    yield
    app.state.redis.close()
    logger.info("Webhook server resources cleaned up.")


app = FastAPI(
    title="GitHub Webhook Monitoring System",
    description="A production-grade system for monitoring suspicious GitHub organization activity.",
    version="1.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")

    logger.debug(f"Incoming {request.method} {request.url.path} | Event: {event_type} | Delivery: {delivery_id}")

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    logger.debug(f"Finished {request.method} {request.url.path} | Status: {response.status_code} | Time: {process_time:.2f}ms")

    return response

app.include_router(api_router, prefix=settings.API_PREFIX)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
