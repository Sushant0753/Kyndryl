from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from lib.logger import logger

router = APIRouter(prefix="/bank", tags=["bank-admin"])


class IngestionStatusResponse(BaseModel):
    collection_name: str
    vector_count: int
    last_run: Optional[Dict[str, Any]]
    scheduler_running: bool


@router.post("/ingest", summary="Trigger SBI bank data ingestion manually")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Manually trigger the SBI bank data ingestion pipeline.
    Runs in the background — returns immediately.
    """
    from services.bank_ingestion.bank_ingestion_service import BankIngestionService

    async def run_ingestion():
        service = BankIngestionService()
        try:
            result = await service.run_full_ingestion()
            logger.info(f"Manual ingestion completed: {result.get('status')}")
        except Exception as e:
            logger.error(f"Manual ingestion failed: {e}", exc_info=True)

    background_tasks.add_task(run_ingestion)
    return {"message": "Ingestion started in background", "status": "accepted"}


@router.get("/status", response_model=IngestionStatusResponse, summary="Get SBI ingestion status")
async def get_ingestion_status():
    """
    Get the current state of the SBI bank knowledge base:
    - Vector count in Qdrant SBI_BANK_DATA collection
    - Last ingestion run metadata
    - Scheduler running status
    """
    from services.bank_ingestion.bank_ingestion_service import BankIngestionService
    from services.qdrant_service import QdrantService
    from scheduler import get_scheduler
    from configs.config import SBIIngestionSettings

    settings = SBIIngestionSettings()

    try:
        qdrant_service = QdrantService()
        collection_info = qdrant_service.get_collection_info_for(settings.SBI_COLLECTION_NAME)
        vector_count = collection_info.get("points_count", 0)
    except Exception as e:
        logger.warning(f"Could not get Qdrant collection info: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector database unavailable"
        )

    try:
        bank_service = BankIngestionService()
        last_run = await bank_service.get_last_run_status()
    except Exception as e:
        logger.warning(f"Could not get ingestion status from MongoDB: {e}")
        last_run = None

    scheduler = get_scheduler()
    scheduler_running = scheduler is not None and scheduler.running

    return IngestionStatusResponse(
        collection_name=settings.SBI_COLLECTION_NAME,
        vector_count=vector_count,
        last_run=last_run,
        scheduler_running=scheduler_running
    )
