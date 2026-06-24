"""Application configuration loaded from environment variables."""

import os
from functools import lru_cache

import httpx
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_XAI_MODEL = "grok-4"
PLACEHOLDER_API_KEY = "your_xai_api_key_here"


class ConfigurationError(Exception):
    """Raised when required environment configuration is missing or invalid."""


class Settings(BaseModel):
    xai_api_key: str = Field(default="", alias="XAI_API_KEY")
    xai_model: str = Field(default=DEFAULT_XAI_MODEL, alias="XAI_MODEL")


@lru_cache
def get_settings() -> Settings:
    return Settings(
        XAI_API_KEY=os.getenv("XAI_API_KEY", "").strip(),
        XAI_MODEL=os.getenv("XAI_MODEL", DEFAULT_XAI_MODEL).strip() or DEFAULT_XAI_MODEL,
    )


def get_grok_client() -> OpenAI:
    """Return an OpenAI SDK-compatible client configured for the xAI Grok API."""
    settings = get_settings()

    if not settings.xai_api_key or settings.xai_api_key == PLACEHOLDER_API_KEY:
        raise ConfigurationError(
            "XAI_API_KEY is not configured. "
            "Copy .env.example to .env and set your xAI API key from "
            "https://console.x.ai/team/default/api-keys"
        )

    return OpenAI(
        api_key=settings.xai_api_key,
        base_url=XAI_BASE_URL,
        timeout=httpx.Timeout(120.0),
    )