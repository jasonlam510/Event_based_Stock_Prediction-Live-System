from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime

class NewsItem(BaseModel):
    title: str
    link: HttpUrl
    pub_date: datetime
    guid: str
    source_name: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    media_url: Optional[HttpUrl] = None
    media_height: Optional[int] = None
    media_width: Optional[int] = None

class Channel(BaseModel):
    title: str
    link: HttpUrl
    description: str
    language: str
    copyright: str
    pub_date: datetime
    ttl: int
    image_title: str
    image_link: HttpUrl
    image_url: HttpUrl 