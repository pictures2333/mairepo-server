from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid"
    )

    # Database
    DATABASE_URL:str = Field(min_length=1)

    # Maisquared
    MAISQUARED_FOLDER_ID:str = Field(min_length=1)
    GOOGLE_DRIVE_API_KEY:str = Field(min_length=1)
    SYNC_INTERVAL:int = Field(min=1)
    SYNC_CONCURRENCY: int = Field(min=1)

    # Storage
    DIRECTORY:str = Field(min_length=1)

    # Security
    TOKEN:str = Field(min_length=0)


settings = Settings()
