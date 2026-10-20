from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    #API Keys
    GOOGLE_API_KEY: str = ""

    #Database
    DATABASE_URL : str = "sqlite:///./codereview.db"

    #Scan and Rate Limiting Rules
    MAX_AI_EXPLANATIONS_PER_SCAN: int = 10
    RATE_LIMIT_PER_MINUTE: int = 5

    #Security and Auth
    SECRET_KEY: str = "default_secret_key_change_in_production"
    ALLOWED_ORIGINS: List[str] = ["https://localhost:8000"]

    #Config dict tells Pydantic to read from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

#Export a single settings instance to be imported across the app
settings = Settings()