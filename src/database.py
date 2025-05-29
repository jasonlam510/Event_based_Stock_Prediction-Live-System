from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.ext.declarative import declarative_base
from src.config import Config
from src.utils.logger import get_logger
from src.pipeline.queues import YFRSSItem, GoogleNewsRSSItem, AnalysisResult as QueueAnalysisResult
from src.data.models import Base, YFRSSItem as DBYFRSSItem, GoogleNewsRSSItem as DBGoogleNewsRSSItem, AnalysisResult

logger = get_logger(__name__) 
config = Config()

# Get database URL from environment variable
DATABASE_URL = config.get_key("DATABASE_URL")
# Convert to async URL format
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,  # Set to False in production
    future=True
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize the database by creating all tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        logger.error(f"Database URL: {DATABASE_URL}")
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def close_db():
    """Close the database connection"""
    await engine.dispose()
    logger.info("Database connection closed")

class Database:
    """SQLAlchemy database handler for the news analysis pipeline"""
    
    def __init__(self, dsn: str):
        """Initialize database connection
        
        Args:
            dsn (str): PostgreSQL connection string
        """
        # Convert postgresql:// to postgresql+asyncpg://
        self.dsn = dsn.replace("postgresql://", "postgresql+asyncpg://")
        self.engine = None
        self.async_session = None
        
    async def connect(self):
        """Create engine and session factory"""
        try:
            self.engine = create_async_engine(
                self.dsn,
                echo=False,
                future=True,
                pool_size=20,
                max_overflow=10
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                
            # Create session factory
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
            
    async def disconnect(self):
        """Close engine"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
            
    async def store_yf_rss_item(self, item: YFRSSItem) -> bool:
        """Store Yahoo Finance RSS item in database"""
        try:
            async with self.async_session() as session:
                # Convert YFRSSItem to SQLAlchemy YFRSSItem
                db_item = DBYFRSSItem(
                    guid=item.guid,
                    pub_date=item.pub_date,
                    title=item.title,
                    link=str(item.link),
                    source_name=item.source_name,
                    source_url=str(item.source_url) if item.source_url else None,
                    media_url=str(item.media_url) if item.media_url else None,
                    media_height=item.media_height,
                    media_width=item.media_width
                )
                
                # Merge will insert or update
                await session.merge(db_item)
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing Yahoo Finance RSS item {item.guid}: {e}")
            return False
            
    async def store_google_news_rss_item(self, item: GoogleNewsRSSItem) -> bool:
        """Store Google News RSS item in database"""
        try:
            async with self.async_session() as session:
                # Convert GoogleNewsRSSItem to SQLAlchemy GoogleNewsRSSItem
                db_item = DBGoogleNewsRSSItem(
                    guid=item.guid,
                    pub_date=item.pub_date,
                    title=item.title,
                    link=str(item.link),
                    source_name=item.source_name,
                    source_url=str(item.source_url) if item.source_url else None,
                    description=item.description,
                    is_perma_link=item.is_perma_link
                )
                
                # Merge will insert or update
                await session.merge(db_item)
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing Google News RSS item {item.guid}: {e}")
            return False
            
    async def store_analysis_result(self, result: QueueAnalysisResult) -> bool:
        """Store analysis result in database"""
        try:
            async with self.async_session() as session:
                # Get the RSS item to get its pub_date
                # Try Yahoo Finance first
                query = select(DBYFRSSItem).where(
                    DBYFRSSItem.guid == result.guid
                ).order_by(
                    DBYFRSSItem.pub_date.desc()
                ).limit(1)
                
                rss_result = await session.execute(query)
                rss_item = rss_result.scalar_one_or_none()
                
                # If not found in Yahoo Finance, try Google News
                if not rss_item:
                    query = select(DBGoogleNewsRSSItem).where(
                        DBGoogleNewsRSSItem.guid == result.guid
                    ).order_by(
                        DBGoogleNewsRSSItem.pub_date.desc()
                    ).limit(1)
                    
                    rss_result = await session.execute(query)
                    rss_item = rss_result.scalar_one_or_none()
                
                if not rss_item:
                    logger.error(f"RSS item {result.guid} not found in any source")
                    return False
                
                # Convert QueueAnalysisResult to SQLAlchemy AnalysisResult
                db_result = AnalysisResult(
                    guid=result.guid,
                    pub_date=rss_item.pub_date,  # Use pub_date from RSS item
                    sentiment_score=result.sentiment_score,
                    relevance_score=result.relevance_score,
                    event_importance=result.event_importance,
                    event_type=result.event_type,
                    analysis_timestamp=result.analysis_timestamp,
                    raw_content=result.raw_content,
                    content_metadata=result.metadata
                )
                
                await session.merge(db_result)
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing analysis result {result.guid}: {e}")
            return False
            
    async def get_latest_analysis(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest analysis results"""
        try:
            async with self.async_session() as session:
                # Query with joins
                query = select(
                    DBYFRSSItem, AnalysisResult
                ).join(
                    AnalysisResult
                ).order_by(
                    AnalysisResult.analysis_timestamp.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                rows = result.all()
                
                # Convert to dict
                return [{
                    "guid": row.DBYFRSSItem.guid,
                    "title": row.DBYFRSSItem.title,
                    "link": row.DBYFRSSItem.link,
                    "pub_date": row.DBYFRSSItem.pub_date,
                    "sentiment_score": row.AnalysisResult.sentiment_score,
                    "relevance_score": row.AnalysisResult.relevance_score,
                    "event_importance": row.AnalysisResult.event_importance,
                    "event_type": row.AnalysisResult.event_type,
                    "analysis_timestamp": row.AnalysisResult.analysis_timestamp,
                    "metadata": row.AnalysisResult.content_metadata
                } for row in rows]
                
        except Exception as e:
            logger.error(f"Error fetching latest analysis: {e}")
            return []

    async def get_latest_yf_pub_date(self) -> Optional[datetime]:
        """Get the latest publication date from Yahoo Finance RSS items table"""
        try:
            async with self.async_session() as session:
                # Query to get the latest pub_date
                query = select(DBYFRSSItem.pub_date).order_by(DBYFRSSItem.pub_date.desc()).limit(1)
                result = await session.execute(query)
                latest_date = result.scalar_one_or_none()
                
                if latest_date:
                    logger.info(f"Latest Yahoo Finance publication date found: {latest_date}")
                    return latest_date
                else:
                    logger.info("No Yahoo Finance RSS items found in database")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting latest Yahoo Finance publication date: {e}")
            return None

    async def get_latest_google_news_pub_date(self) -> Optional[datetime]:
        """Get the latest publication date from Google News RSS items table"""
        try:
            async with self.async_session() as session:
                # Query to get the latest pub_date
                query = select(DBGoogleNewsRSSItem.pub_date).order_by(DBGoogleNewsRSSItem.pub_date.desc()).limit(1)
                result = await session.execute(query)
                latest_date = result.scalar_one_or_none()
                
                if latest_date:
                    logger.info(f"Latest Google News publication date found: {latest_date}")
                    return latest_date
                else:
                    logger.info("No Google News RSS items found in database")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting latest Google News publication date: {e}")
            return None

    async def get_unanalyzed_yf_rss_items(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get Yahoo Finance RSS items that don't have corresponding analysis results"""
        try:
            async with self.async_session() as session:
                # Query to find RSS items without analysis results
                query = select(DBYFRSSItem).outerjoin(
                    AnalysisResult,
                    DBYFRSSItem.guid == AnalysisResult.guid
                ).where(
                    AnalysisResult.guid.is_(None)
                ).order_by(
                    DBYFRSSItem.pub_date.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                items = result.scalars().all()
                
                # Convert to dict format
                return [{
                    "guid": item.guid,
                    "title": item.title,
                    "link": item.link,
                    "pub_date": item.pub_date,
                    "source_name": item.source_name,
                    "source_url": item.source_url,
                    "media_url": item.media_url,
                    "media_height": item.media_height,
                    "media_width": item.media_width
                } for item in items]
                
        except Exception as e:
            logger.error(f"Error getting unanalyzed Yahoo Finance RSS items: {e}")
            return []

    async def get_unanalyzed_google_news_rss_items(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get Google News RSS items that don't have corresponding analysis results"""
        try:
            async with self.async_session() as session:
                # Query to find RSS items without analysis results
                query = select(DBGoogleNewsRSSItem).outerjoin(
                    AnalysisResult,
                    DBGoogleNewsRSSItem.guid == AnalysisResult.guid
                ).where(
                    AnalysisResult.guid.is_(None)
                ).order_by(
                    DBGoogleNewsRSSItem.pub_date.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                items = result.scalars().all()
                
                # Convert to dict format
                return [{
                    "guid": item.guid,
                    "title": item.title,
                    "link": item.link,
                    "pub_date": item.pub_date,
                    "source_name": item.source_name,
                    "source_url": item.source_url,
                    "description": item.description,
                    "is_perma_link": item.is_perma_link
                } for item in items]
                
        except Exception as e:
            logger.error(f"Error getting unanalyzed Google News RSS items: {e}")
            return [] 