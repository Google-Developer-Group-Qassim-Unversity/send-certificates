import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import blasts, emails, generations, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

BLASTS_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


def _write_blast_422_log(request: Request, exc: RequestValidationError) -> Path:
    BLASTS_LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    log_path = BLASTS_LOGS_DIR / f"blast_{ts}.log"

    query_params: dict = {}
    for key in request.query_params:
        values = request.query_params.getlist(key)
        query_params[key] = values if len(values) > 1 else values[0]

    request_data = {
        "path": request.url.path,
        "query_params": query_params,
    }

    lines = [
        "=== BLAST REQUEST (422 - Validation Error) ===",
        json.dumps(request_data, indent=4, ensure_ascii=False),
        "",
        "=== VALIDATION ERRORS ===",
        json.dumps(exc.errors(), indent=4, ensure_ascii=False),
    ]

    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path


app = FastAPI(title="Certificate Sender API", version="2.0.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/blasts"):
        log_path = _write_blast_422_log(request, exc)
        logger.warning(f"Blast validation failed (422) | log={log_path.name}")

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


app.include_router(emails.router, prefix="/emails")
app.include_router(blasts.router, prefix="/blasts")
app.include_router(generations.router, prefix="/generations")
app.include_router(health.router)
