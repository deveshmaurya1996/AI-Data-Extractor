from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/chatbot"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    POLLINATIONS_API_KEY: str = Field(default="")
    POLLINATIONS_MODEL: str = "openai"
    POLLINATIONS_BASE_URL: str = "https://gen.pollinations.ai/v1"
    POLLINATIONS_TIMEOUT: int = 30
    
    DEBUG: bool = False
    APP_NAME: str = "AI Data Extraction Chatbot"
    API_VERSION: str = "1.0.0"
    
    MAX_ROWS_PER_QUERY: int = 1000
    QUERY_TIMEOUT_MS: int = 5000
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]


settings = Settings()