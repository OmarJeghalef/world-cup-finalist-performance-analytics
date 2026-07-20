"""Central configuration for the World Cup analytics project."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
FOOTBALL_DATA_BASE_URL = os.getenv(
    "FOOTBALL_DATA_BASE_URL",
    "https://api.football-data.org/v4",
)
WORLD_CUP_COMPETITION_CODE = os.getenv(
    "WORLD_CUP_COMPETITION_CODE",
    "WC",
)

RAW_API_DIR = PROJECT_ROOT / "data" / "raw" / "api"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"


def validate_api_configuration() -> None:
    """Raise an error when required football API configuration is missing."""

    if not FOOTBALL_DATA_API_KEY:
        raise ValueError(
            "FOOTBALL_DATA_API_KEY is missing. "
            "Add it to the local .env file before running API scripts."
        )

    if FOOTBALL_DATA_API_KEY == "replace_with_your_api_key":
        raise ValueError(
            "FOOTBALL_DATA_API_KEY still contains the placeholder value."
        )