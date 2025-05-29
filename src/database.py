from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.ext.declarative import declarative_base
from src.config import Config
from src.utils.logger import get_logger
from src.pipeline.queues import RSSItem as QueueRSSItem
from src.pipeline.queues import ExtractedContent as QueueExtractedContent
from src.pipeline.queues import AnalysisResult as QueueAnalysisResult
from src.data.models import Base, RSSItem, ExtractedContent, AnalysisResult

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
            
    async def store_rss_item(self, item: QueueRSSItem) -> bool:
        """Store RSS item in database"""
        try:
            async with self.async_session() as session:
                # Convert QueueRSSItem to SQLAlchemy RSSItem
                db_item = RSSItem(
                    guid=item.guid,
                    title=item.title,
                    link=str(item.link),
                    pub_date=item.pub_date,
                    source_name=item.source_name,
                    source_url=str(item.source_url) if item.source_url else None,
                    media_url=str(item.media_url) if item.media_url else None,
                    media_height=item.media_height,
                    media_width=item.media_width
                )
                
                # Merge will insert or update
                session.add(db_item)
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing RSS item {item.guid}: {e}")
            return False
            
    async def store_extracted_content(self, content: QueueExtractedContent) -> bool:
        """Store extracted content in database"""
        try:
            async with self.async_session() as session:
                # First get the RSS item to get its pub_date
                # Get the most recent RSS item if there are duplicates
                query = select(RSSItem).where(
                    RSSItem.guid == content.guid
                ).order_by(
                    RSSItem.pub_date.desc()
                ).limit(1)
                
                result = await session.execute(query)
                rss_item = result.scalar_one_or_none()
                
                if not rss_item:
                    logger.error(f"RSS item {content.guid} not found")
                    return False
                
                # Convert QueueExtractedContent to SQLAlchemy ExtractedContent
                db_content = ExtractedContent(
                    guid=content.guid,
                    pub_date=rss_item.pub_date,  # Add pub_date from RSS item
                    url=str(content.url),
                    content=content.content,
                    extraction_timestamp=content.extraction_timestamp,
                    content_metadata=content.metadata
                )
                
                # Use merge instead of add to handle potential duplicates
                session.merge(db_content)
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing extracted content {content.guid}: {e}")
            return False
            
    async def store_analysis_result(self, result: QueueAnalysisResult) -> bool:
        """Store analysis result in database"""
        try:
            async with self.async_session() as session:
                # Convert QueueAnalysisResult to SQLAlchemy AnalysisResult
                db_result = AnalysisResult(
                    guid=result.guid,
                    sentiment_score=result.sentiment_score,
                    relevance_score=result.relevance_score,
                    event_importance=result.event_importance,
                    event_type=result.event_type,
                    analysis_timestamp=result.analysis_timestamp,
                    raw_content=result.raw_content,
                    content_metadata=result.metadata
                )
                
                session.add(db_result)
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
                    RSSItem, ExtractedContent, AnalysisResult
                ).join(
                    ExtractedContent
                ).join(
                    AnalysisResult
                ).order_by(
                    AnalysisResult.analysis_timestamp.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                rows = result.all()
                
                # Convert to dict
                return [{
                    "guid": row.RSSItem.guid,
                    "title": row.RSSItem.title,
                    "link": row.RSSItem.link,
                    "pub_date": row.RSSItem.pub_date,
                    "content": row.ExtractedContent.content,
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

    async def get_latest_pub_date(self) -> Optional[datetime]:
        """Get the latest publication date from RSS items table
        
        Returns:
            Optional[datetime]: The latest publication date if table has data, None if table is empty
        """
        try:
            async with self.async_session() as session:
                # Query to get the latest pub_date
                query = select(RSSItem.pub_date).order_by(RSSItem.pub_date.desc()).limit(1)
                result = await session.execute(query)
                latest_date = result.scalar_one_or_none()
                
                if latest_date:
                    logger.info(f"Latest publication date found: {latest_date}")
                    return latest_date
                else:
                    logger.info("No RSS items found in database")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting latest publication date: {e}")
            return None

    async def get_unprocessed_rss_items(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get RSS items that don't have corresponding extracted content
        
        Args:
            limit (int): Maximum number of items to return
            
        Returns:
            List[Dict[str, Any]]: List of RSS items that need processing
        """
        try:
            async with self.async_session() as session:
                # Query to find RSS items without extracted content
                query = select(RSSItem).outerjoin(
                    ExtractedContent,
                    (RSSItem.guid == ExtractedContent.guid) & 
                    (RSSItem.pub_date == ExtractedContent.pub_date)
                ).where(
                    ExtractedContent.guid.is_(None)
                ).order_by(
                    RSSItem.pub_date.desc()
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
            logger.error(f"Error getting unprocessed RSS items: {e}")
            return []

    async def get_unanalyzed_rss_items(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get RSS items that don't have corresponding analysis results
        
        Args:
            limit (int): Maximum number of items to return
            
        Returns:
            List[Dict[str, Any]]: List of RSS items that need analysis
        """
        try:
            async with self.async_session() as session:
                # Query to find RSS items without analysis results
                query = select(RSSItem).outerjoin(
                    AnalysisResult,
                    RSSItem.guid == AnalysisResult.guid
                ).where(
                    AnalysisResult.guid.is_(None)
                ).order_by(
                    RSSItem.pub_date.desc()
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
            logger.error(f"Error getting unanalyzed RSS items: {e}")
            return [] 