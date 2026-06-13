import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import routes
from configs.config import AppInfo
from scheduler import start_scheduler, stop_scheduler


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return "/health-check" not in record.getMessage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


def create_application() -> FastAPI:
    info = AppInfo()

    application = FastAPI(
        title=info.PROJECT_NAME,
        version=info.VERSION,
        description=info.DESCRIPTION,
        openapi_url=f"{info.API_STR}/vectoriser/openapi.json",
        lifespan=lifespan
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=info.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(routes, prefix=info.API_STR)

    return application


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
