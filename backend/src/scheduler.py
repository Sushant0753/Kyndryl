from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from configs.config import SBIIngestionSettings
from lib.logger import logger


_scheduler = None


async def _run_ingestion_job():
    """Wrapper that imports BankIngestionService at call time to avoid circular imports."""
    from services.bank_ingestion.bank_ingestion_service import BankIngestionService
    service = BankIngestionService()
    try:
        result = await service.run_full_ingestion()
        logger.info(f"Scheduled ingestion completed: {result.get('status')}, new_chunks={result.get('new_chunks_stored', 0)}")
    except Exception as e:
        logger.error(f"Scheduled ingestion failed: {e}", exc_info=True)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    settings = SBIIngestionSettings()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_ingestion_job,
        trigger=CronTrigger(hour=settings.SBI_INGESTION_SCHEDULE_HOUR, minute=0),
        id="sbi_bank_ingestion",
        name="SBI Bank Data Daily Ingestion",
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace if job is missed
    )
    return scheduler


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    return _scheduler


def start_scheduler():
    """Start the global scheduler."""
    global _scheduler
    _scheduler = create_scheduler()
    _scheduler.start()
    logger.info("APScheduler started — SBI ingestion scheduled daily")
    return _scheduler


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("APScheduler stopped")
