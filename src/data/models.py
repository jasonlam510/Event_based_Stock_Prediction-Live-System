from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, text, PrimaryKeyConstraint, ForeignKeyConstraint, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Base Pydantic models for parsing
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

# Base SQLAlchemy model for common fields
class BaseRSSItem(Base):
    """Base class for RSS items with common fields"""
    __abstract__ = True
    
    guid = Column(String, nullable=False)
    pub_date = Column(DateTime(timezone=True), nullable=False)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False)
    source_name = Column(String)
    source_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

# Yahoo Finance specific model
class YFRSSItem(BaseRSSItem):
    """RSS feed item from Yahoo Finance"""
    __tablename__ = "yf_rss_items"
    
    media_url = Column(String)
    media_height = Column(Integer)
    media_width = Column(Integer)

    # Define composite primary key
    __table_args__ = (
        PrimaryKeyConstraint('guid', 'pub_date', name='yf_rss_items_pkey'),
    )

# Google News specific model
class GoogleNewsRSSItem(BaseRSSItem):
    """RSS feed item from Google News"""
    __tablename__ = "google_news_rss_items"
    
    description = Column(String)
    is_perma_link = Column(Boolean, default=False)

    # Define composite primary key
    __table_args__ = (
        PrimaryKeyConstraint('guid', 'pub_date', name='google_news_rss_items_pkey'),
    )

class AnalysisResult(Base):
    """LLM analysis result for RSS item"""
    __tablename__ = "analysis_results"
    
    guid = Column(String, nullable=False)
    pub_date = Column(DateTime(timezone=True), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    relevance_score = Column(Float, nullable=False)
    event_importance = Column(Float, nullable=False)
    event_type = Column(String, nullable=False)
    analysis_timestamp = Column(DateTime(timezone=True), nullable=False)
    raw_content = Column(String, nullable=False)  # The RSS item title that was analyzed
    content_metadata = Column(JSON)  # Contains source_name, source_url, media_url, and pub_date
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Define composite primary key and foreign key
    __table_args__ = (
        PrimaryKeyConstraint('guid', 'pub_date', name='analysis_results_pkey'),
        ForeignKeyConstraint(
            ['guid', 'pub_date'],
            ['yf_rss_items.guid', 'yf_rss_items.pub_date'],
            name='analysis_results_yf_rss_items_fkey'
        ),
        ForeignKeyConstraint(
            ['guid', 'pub_date'],
            ['google_news_rss_items.guid', 'google_news_rss_items.pub_date'],
            name='analysis_results_google_news_rss_items_fkey'
        ),
    ) 