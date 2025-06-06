from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, text, PrimaryKeyConstraint, ForeignKeyConstraint, Boolean, BigInteger, Index
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
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Define composite primary key
    __table_args__ = (
        PrimaryKeyConstraint('guid', 'pub_date', name='analysis_results_pkey'),
    )

class StockData(Base):
    """Stock price data from Yahoo Finance"""
    __tablename__ = "stock_data"
    
    symbol = Column(String, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    
    # Define composite primary key
    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'date', name='stock_data_pkey'),
    )

class TechnicalIndicators(Base):
    """Technical indicators for stock data"""
    __tablename__ = "technical_indicators"
    
    symbol = Column(String, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    
    # Bollinger Bands (20)
    bb_upper_20 = Column(Float)  # Bollinger Bands Upper
    bb_middle_20 = Column(Float) # Bollinger Bands Middle
    bb_lower_20 = Column(Float)  # Bollinger Bands Lower
    
    # Moving Averages
    ma_50 = Column(Float)     # Simple Moving Average 50
    ema_12 = Column(Float)    # Exponential Moving Average 12
    
    # Momentum Indicators
    rsi_14 = Column(Float)    # Relative Strength Index 14
    macd_26 = Column(Float)      # MACD
    macd_signal_26 = Column(Float)  # MACD Signal Line
    macd_hist_26 = Column(Float)    # MACD Histogram
    
    # Volatility Indicators
    atr_14 = Column(Float)    # Average True Range 14
    cci_20 = Column(Float)    # Commodity Channel Index 20
    
    # Stochastic Oscillator (14)
    stoch_k_14 = Column(Float)   # Stochastic %K
    stoch_d_14 = Column(Float)   # Stochastic %D
    
    # ADX (14)
    adx_14 = Column(Float)       # Average Directional Index
    di_pos_14 = Column(Float)    # Positive Directional Indicator
    di_neg_14 = Column(Float)    # Negative Directional Indicator
    
    # Vortex (14)
    vortex_pos_14 = Column(Float)  # Positive Vortex
    vortex_neg_14 = Column(Float)  # Negative Vortex
    
    # Volume Indicators
    obv = Column(Float)       # On-Balance Volume
    mfi_14 = Column(Float)    # Money Flow Index 14
    vwap = Column(Float)      # Volume-Weighted Average Price
    
    # Define composite primary key and foreign key
    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'date', name='technical_indicators_pkey'),
        ForeignKeyConstraint(
            ['symbol', 'date'],
            ['stock_data.symbol', 'stock_data.date'],
            name='fk_technical_indicators_stock_data'
        ),
    ) 