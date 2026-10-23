from typing import List
from datetime import datetime

from pydantic import BaseModel


class Chart(BaseModel):
    id:int
    name:str
    files:List["File"]


class File(BaseModel):
    id:int
    filename:str
    drive_head_revision_id:str
    blobs:List["Blob"]


class Blob(BaseModel):
    id:int
    drive_revision_id:str
    created_at:datetime
