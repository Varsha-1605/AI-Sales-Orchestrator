"""All configuration, read from environment variables or .env."""

import os
from typing import List

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    ANTHROPIC_API_KEY: SecretStr = SecretStr("")
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    OPENAI_API_KEY: SecretStr = SecretStr("")
    OPENAI_MODEL: str = "gpt-4o-mini"

    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000
    DEBUG_MODE: bool = True
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    LLM_TIMEOUT_SECONDS: float = 20
    LLM_MAX_RETRIES: int = 2
    # Send one tiny request to each model at startup so the first customer does not wait for the connection
    WARMUP_LLM: bool = True

    # Sessions get a secret token; every request must send it in the X-Session-Token header
    AUTH_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60
    LOG_JSON: bool = False
    # Pause between pieces of a streamed reply, so the text appears as it is typed (0 = send at once)
    STREAM_PIECE_DELAY_SECONDS: float = 0.03

    REDIS_URL: SecretStr = SecretStr("redis://localhost:6379/0")
    SESSION_TIMEOUT_SECONDS: int = 3600

    POSTGRES_URL: SecretStr = SecretStr("")
    POSTGRES_POOL_MAX_SIZE: int = 10

    PAYMENT_GATEWAY_ORDER: List[str] = ["Razorpay", "PayU", "UPI Direct"]
    PAYMENT_GATEWAY_TIMEOUT_SECONDS: float = 5

    GUARDRAILS_ENABLED: bool = True

    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: SecretStr = SecretStr("")
    LANGSMITH_PROJECT: str = "ai-sales-orchestrator"

    DATA_DIR: str = "data"


settings = Settings()

if settings.LANGSMITH_TRACING:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY.get_secret_value()
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
