from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from middleware.logger import LoggingMiddleware
from utils.logger import setup_logging, get_logger
from utils.scheduler import scheduler_service
from container.dependencies import get_customer_visit_processor_cron, get_customer_calls_cron
from controllers import admin_router, customer_calls_router, customer_visit_router, admin_jobs_router, jobs_router
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

setup_logging()
logger = get_logger("app")


async def run_customer_visit_processor():
    """Wrapper to run customer visit processor with injected dependencies."""
    with get_customer_visit_processor_cron() as cron:
        await cron.process()


async def run_customer_calls():
    """Wrapper to run customer calls processor with injected dependencies."""
    with get_customer_calls_cron() as cron:
        await cron.process()


def register_cron_jobs():
    """Register all cron jobs for the application."""
    
    # Production: Run every day at 7pm Nairobi time (EAT, UTC+3)
    scheduler_service.add_cron_job(
        func=run_customer_visit_processor,
        job_id="customer_visit_processor",
        hour="19",
        minute="30",
        second="0",
        timezone="Africa/Nairobi"
    )
    
    # Testing: Run every 5 minutes
    # scheduler_service.add_cron_job(
    #     func=run_customer_visit_processor,
    #     job_id="customer_visit_processor",
    #     minute="*/5",
    #     second="0"
    # )
    
    # Customer Calls - TODO: Configure schedule
    scheduler_service.add_cron_job(
        func=run_customer_calls,
        job_id="run_customer_calls",
        hour="19",
        minute="0",
        second="0",
        timezone="Africa/Nairobi"
    )

    # scheduler_service.add_cron_job(
    #     func=run_customer_calls,
    #     job_id="customer_calls",
    #     minute="*/5",
    #     second="0"
    # )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("FastAPI application starting up...")
    
    # Register and start cron jobs
    register_cron_jobs()
    scheduler_service.start()
    logger.info("Cron jobs registered and scheduler started")
    
    logger.info("Application startup complete!")
    yield
    # Shutdown
    logger.info("FastAPI application shutting down...")
    scheduler_service.shutdown()
    logger.info("Scheduler shut down")


def create_app() -> FastAPI:
    app_meta = {
        "title": "Brisk Automations",
        "description": "Brisk Automations Backend API",
        "version": "1.0.0",
        "lifespan": lifespan
    }
    
    # Create FastAPI app
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    if ENVIRONMENT == "development":
        app = FastAPI(**app_meta)
    else:
        app = FastAPI(
            **app_meta,
            docs_url=None,
            redoc_url=None,
            openapi_url=None 
        )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000"), "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    
    # Add Logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Trust proxy headers from nginx for proper HTTPS redirects
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    # Mount static files for serving uploaded reports
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=str(uploads_dir)), name="files")

    # Register routers
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(customer_calls_router, prefix="/api/v1")
    app.include_router(customer_visit_router, prefix="/api/v1")
    app.include_router(admin_jobs_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "healthy"}

    return app


app = create_app()


if __name__ == "__main__":
    logger.info("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
