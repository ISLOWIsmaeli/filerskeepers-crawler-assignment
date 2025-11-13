import datetime
import hashlib
import time
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any

class ChangeLogEntry(BaseModel):
    change_id: str = Field(
        default_factory=lambda: f"change_{datetime.datetime.now(datetime.timezone.utc).isoformat()}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
    )
    crawl_timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    source_url: HttpUrl
    status: str  
    changes: List[
        Dict[str, Any]
    ] = []  
