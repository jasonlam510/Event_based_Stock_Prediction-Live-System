from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import HttpUrl

@dataclass
class RSSItem:
    """Raw RSS feed item from Yahoo Finance"""
    title: str
    link: HttpUrl
    pub_date: datetime
    guid: str
    source_name: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    media_url: Optional[HttpUrl] = None
    media_height: Optional[int] = None
    media_width: Optional[int] = None

@dataclass
class AnalysisResult:
    """LLM analysis result for RSS item"""
    guid: str
    sentiment_score: float
    relevance_score: float
    event_importance: float
    event_type: str
    analysis_timestamp: datetime
    raw_content: str  # The RSS item title that was analyzed
    metadata: Dict[str, Any]  # Contains source_name, source_url, media_url, and pub_date

@dataclass
class PipelineError:
    """Error message for pipeline stages"""
    guid: str
    stage: str
    error: str
    timestamp: datetime
    context: Dict[str, Any] 