from pydantic import BaseModel, HttpUrl
from typing import Optional
import datetime

class BookDetails(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    price_excl_tax: Optional[float] = None
    price_incl_tax: Optional[float] = None
    availability: str
    num_reviews: int
    image_url: Optional[HttpUrl] = None
    rating: Optional[str] = None

class BookMetadata(BaseModel):
    crawl_timestamp: datetime.datetime
    status: str
    source_url: HttpUrl

class Book(BaseModel):
    metadata: BookMetadata
    book_details: BookDetails
