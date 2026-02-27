import os
import logging
from dotenv import load_dotenv
from sqlmodel import create_engine, Session

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

engine = create_engine(DATABASE_URL, echo=False)

assert engine is not None, "Failed to create database engine"


def get_session():
    with Session(engine) as session:
        assert session is not None, "Session creation returned None"
        yield session
