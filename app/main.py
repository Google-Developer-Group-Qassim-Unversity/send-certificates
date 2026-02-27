import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.startup import validate_startup, get_startup_status
from app.routers import certificates, status, email_blasts


logging.basicConfig(
    level=logging.INFO,
    format="\t%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Certificate API starting up...")

    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Certificates folder: {settings.certificates_folder}")
    logger.info(f"Official template: {settings.official_template}")
    logger.info(f"Unofficial template: {settings.unofficial_template}")

    checks = validate_startup()
    failures = [c for c in checks if not c.passed]

    if failures:
        logger.warning(f"Startup completed with {len(failures)} check(s) failing")
        logger.warning("Some features may not work correctly")
    else:
        logger.info("All startup checks passed")

    yield

    logger.info("Certificate API shutting down...")


app = FastAPI(
    title="Certificate Generator API",
    description="Generate and send certificates via email",
    version="2.1.0",
    lifespan=lifespan,
)

register_error_handlers(app)

app.include_router(certificates.router)
app.include_router(email_blasts.router)
app.include_router(status.router)


@app.get(
    "/startup-status",
    summary="Get startup validation status",
    description="Returns the results of all startup validation checks",
)
async def startup_status():
    return get_startup_status()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
