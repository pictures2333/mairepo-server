from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DriveFileInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id:str = Field(min_length=1)
    name:str = Field(min_length=1)
    mime_type:str = Field(alias="mimeType", min_length=1)
    head_revision_id:Optional[str] = Field(default=None, alias="headRevisionId")
    size:Optional[int] = Field(default=None, ge=0)
    md5_checksum:Optional[str] = Field(default=None, alias="md5Checksum")
    resource_key:Optional[str] = Field(default=None, alias="resourceKey", min_length=1)
