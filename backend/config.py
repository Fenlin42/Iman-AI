import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MODEL = os.getenv("ANTHROPIC_MODEL") or "claude-opus-5-5"
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
DATA_DIR = Path(os.getenv("DATA_DIR") or ROOT / "data")
MOCK_AI = os.getenv("MOCK_AI", "0") == "1"
ON_RENDER = bool(os.getenv("RENDER"))
FRONTEND_DIST = ROOT / "frontend" / "dist"


def has_api_key() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    return bool(key) and not key.endswith("...")  # ignore an unfilled placeholder
