from typing_extensions import Self

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

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
    GOOGLE_SERVICE_ACCOUNT_CRED_FILE:str = Field(min_length=1)
    SYNC_CONCURRENCY:int = Field(ge=1, default=8)
    RUN_SYNC_INTERVAL:int = Field(ge=1, default=3600) # in seconds

    # Storage
    DIRECTORY:str = Field(min_length=1)
    GC_KEEP:int = Field(ge=1, default=3)
    GC_MAX_KEEP:int = Field(ge=1, default=7)
    RUN_GC_INTERVAL:int = Field(ge=1, default=43200) # in seconds

    # Security
    TOKEN:str = Field(min_length=0, default="")

    # General
    MAX_ATTEMPTS:int = Field(ge=1, default=3)

    @model_validator(mode="after")
    def validate_keep_and_max_keep(self) -> Self:
        if self.GC_MAX_KEEP < self.GC_KEEP:
            raise ValueError("MAX_KEEP should be greater than or equal to KEEP")

        return self


settings = Settings()
