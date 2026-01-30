from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized Configuration Management.
    Loads variables from environment or .env file.
    """

    # Project Info
    PROJECT_NAME: str = "Stellar Gateway"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # External APIs (Default values for Dev)
    SWAPI_BASE_URL: str = "https://swapi.dev/api"

    # Infrastructure (Redis & Auth)
    # Using 'localhost' default for easy local dev/testing
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Firebase (Path to credentials JSON)
    # In Prod, this might be injected via distinct env vars or a secret manager
    GOOGLE_APPLICATION_CREDENTIALS: str = "serviceAccountKey.json"

    # Firebase Web API Key (for REST API token exchange)
    FIREBASE_WEB_API_KEY: str = ""

    # Environment: "dev", "test", or "prod"
    ENVIRONMENT: str = "dev"

    # Config to read from .env file automatically
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",  # Ignora variáveis extras no .env que não estão aqui
    )


# Singleton instance to be imported elsewhere
settings = Settings()
