from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, text, PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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

Base = declarative_base()

class RSSItem(Base):
    """RSS feed item model"""
    __tablename__ = "rss_items"

    guid = Column(String, nullable=False)
    pub_date = Column(DateTime(timezone=True), nullable=False)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False)
    source_name = Column(String)
    source_url = Column(String)
    media_url = Column(String)
    media_height = Column(Integer)
    media_width = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Define composite primary key
    __table_args__ = (
        PrimaryKeyConstraint('guid', 'pub_date', name='rss_items_pkey'),
    )

class ExtractedContent(Base):
    """Extracted content model"""
    __tablename__ = "extracted_content"

    guid = Column(String, nullable=False)
    pub_date = Column(DateTime(timezone=True), nullable=False)
    url = Column(String, nullable=False)
    content = Column(String, nullable=False)
    extraction_timestamp = Column(DateTime(timezone=True), nullable=False)
    content_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Define composite primary key and foreign key
    __table_args__ = (
        PrimaryKeyConstraint('guid', 'pub_date', name='extracted_content_pkey'),
        ForeignKeyConstraint(
            ['guid', 'pub_date'],
            ['rss_items.guid', 'rss_items.pub_date'],
            name='extracted_content_rss_items_fkey'
        ),
    )

class AnalysisResult(Base):
    """Analysis result model"""
    __tablename__ = "analysis_results"

    guid = Column(String, nullable=False)
    pub_date = Column(DateTime(timezone=True), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    relevance_score = Column(Float, nullable=False)
    event_importance = Column(Float, nullable=False)
    event_type = Column(String, nullable=False)
    analysis_timestamp = Column(DateTime(timezone=True), nullable=False)
    raw_content = Column(String, nullable=False)
    content_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Define composite primary key and foreign key
    __table_args__ = (
        PrimaryKeyConstraint('guid', 'pub_date', name='analysis_results_pkey'),
        ForeignKeyConstraint(
            ['guid', 'pub_date'],
            ['rss_items.guid', 'rss_items.pub_date'],
            name='analysis_results_rss_items_fkey'
        ),
    ) 