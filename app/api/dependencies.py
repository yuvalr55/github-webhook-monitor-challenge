from fastapi import Request
from app.services.ingestion import IngestionService

def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service
