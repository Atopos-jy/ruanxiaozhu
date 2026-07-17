import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Copy .env.example to .env and configure PostgreSQL.")

SECRET_KEY = os.getenv(
    "AUTH_SECRET_KEY",
    "development-only-change-me-use-an-environment-variable-32-bytes-minimum",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_SLIDING_DAYS = 7
REFRESH_TOKEN_MAX_SESSION_DAYS = 30
