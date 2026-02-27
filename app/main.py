import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.routers import certificates, status

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)

app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)
app_logger.addHandler(handler)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Certificate API starting up...")
    logger.info(f"Jobs folder: {settings.jobs_folder}")
    logger.info(f"Official template: {settings.official_template}")
    logger.info(f"Unofficial template: {settings.unofficial_template}")
    yield
    logger.info("Certificate API shutting down...")


app = FastAPI(
    title="Certificate Generator API",
    description="Generate and send certificates via email",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(certificates.router)
app.include_router(status.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
