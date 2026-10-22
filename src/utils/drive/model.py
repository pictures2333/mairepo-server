from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import FOLDER_MIME_TYPE


class DriveFileInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id:str = Field(min_length=1)
    name:str = Field(min_length=1)
    mime_type:str = Field(alias="mimeType", min_length=1)
    modified_time:datetime = Field(alias="modifiedTime")
    size:Optional[int] = Field(default=None, ge=0)
    md5_checksum:Optional[str] = Field(default=None, alias="md5Checksum")
    resource_key:Optional[str] = Field(default=None, alias="resourceKey", min_length=1)

    @field_validator("modified_time")
    @classmethod
    def normalize_modified_time(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("Google Drive returned a modified time without a timezone.")

        return value.astimezone(timezone.utc)

    @property
    def is_folder(self) -> bool:
        return self.mime_type == FOLDER_MIME_TYPE
