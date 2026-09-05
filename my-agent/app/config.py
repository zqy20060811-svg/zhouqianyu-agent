"""环境变量与项目路径。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PUBLIC_DIR = PROJECT_ROOT / "public"


def load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def model_base_url() -> str:
    return _env("MODEL_BASE_URL", "").strip().rstrip("/")


def model_api_key() -> str:
    return _env("MODEL_API_KEY", "").strip()


def model_name() -> str:
    return _env("MODEL_NAME", "").strip()


def model_timeout_ms() -> int:
    try:
        return max(5000, int(_env("MODEL_TIMEOUT_MS", "45000")))
    except ValueError:
        return 45000


def is_production() -> bool:
    return _env("NODE_ENV", "") == "production" or _env("ENV", "") == "production"


def port() -> int:
    try:
        return max(1, int(_env("PORT", "8787")))
    except ValueError:
        return 8787


def trust_proxy() -> bool:
    return _env("TRUST_PROXY", "0") == "1"


def chat_limit() -> int:
    try:
        return max(1, int(_env("CHAT_LIMIT", "20")))
    except ValueError:
        return 20


def chat_window_ms() -> int:
    try:
        return max(1000, int(_env("CHAT_WINDOW_MS", "600000")))
    except ValueError:
        return 600000


def fastapi_base_url() -> str:
    return _env("FASTAPI_BASE_URL", "http://127.0.0.1:8787").rstrip("/")


def langsmith_enabled() -> bool:
    return _env("LANGSMITH_TRACING", "").lower() in {"true", "1", "yes"}
