from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class MediaFile(SQLModel, table=True):
    file_id: str = Field(primary_key=True, unique=True)
    path: str
    type: str  # "IMG" или "VID"
    size: int
    created_at: datetime = Field(default_factory=datetime.now)
