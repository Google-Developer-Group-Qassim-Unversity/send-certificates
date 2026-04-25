import logging

from fastapi import FastAPI

from app.routers import blasts, emails, generations, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Certificate Sender API", version="2.0.0")

app.include_router(emails.router, prefix="/emails")
app.include_router(blasts.router, prefix="/blasts")
app.include_router(generations.router, prefix="/generations")
app.include_router(health.router)
