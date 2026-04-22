from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Redis
    REDIS_URL: str

    # Worker
    BATCH_SIZE: int
    ORG_LOCK_TTL_SECONDS: int
    ORG_LEASE_DURATION_SECONDS: int
    WORKER_IDLE_SLEEP_SECONDS: float
    REPO_DELETION_THRESHOLD_MINUTES: int
    SUSPICIOUS_PUSH_START_HOUR: int
    SUSPICIOUS_PUSH_END_HOUR: int
    SUSPICIOUS_TEAM_PREFIX: str

    # Scheduling & Idempotency
    SCHEDULER_KEY: str
    DUPLICATE_CHECK_TTL: int

    # API & Security
    API_PREFIX: str
    GITHUB_WEBHOOK_SECRET: str

    # Generic Filtering
    SUPPORTED_EVENTS: set[str]
    # Mapping of org_id -> set of allowed events. If org not here, it uses SUPPORTED_EVENTS.
    ORG_SPECIFIC_EVENTS: dict[str, set[str]] = {}

    # Logging
    LOG_LEVEL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
