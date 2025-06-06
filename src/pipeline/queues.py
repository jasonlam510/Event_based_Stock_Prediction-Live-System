from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, Union
from pydantic import HttpUrl
import pandas as pd

@dataclass
class RSSItem:
    """Simplified RSS feed item for LLM analysis"""
    guid: str
    pub_date: datetime
    title: str

@dataclass
class BaseRSSItem:
    """Base class for RSS feed items"""
    title: str
    link: HttpUrl
    pub_date: datetime
    guid: str
    source_name: Optional[str] = None
    source_url: Optional[HttpUrl] = None

@dataclass
class YFRSSItem(BaseRSSItem):
    """Yahoo Finance RSS feed item"""
    media_url: Optional[HttpUrl] = None
    media_height: Optional[int] = None
    media_width: Optional[int] = None

@dataclass
class GoogleNewsRSSItem(BaseRSSItem):
    """Google News RSS feed item"""
    description: Optional[str] = None
    is_perma_link: bool = False

# Type alias for source-specific RSS items
SourceRSSItem = Union[YFRSSItem, GoogleNewsRSSItem]

@dataclass
class AnalysisResult:
    """LLM analysis result for RSS item"""
    guid: str
    sentiment_score: float
    relevance_score: float
    event_importance: float
    event_type: str

@dataclass
class PipelineError:
    """Error message for pipeline stages"""
    guid: str
    stage: str
    error: str
    timestamp: datetime
    context: Dict[str, Any]

@dataclass
class StockData:
    """Stock price data for processing"""
    symbol: str
    data: pd.DataFrame 