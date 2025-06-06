import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from src.pipeline.worker import PipelineWorker
from src.pipeline.queues import YFRSSItem, GoogleNewsRSSItem, RSSItem, PipelineError
from src.database import Database
from src.utils.logger import get_logger

class ContentBackfillWorker(PipelineWorker):
    """Worker that processes RSS items that haven't been analyzed yet"""
    
    def __init__(
        self,
        output_queue: asyncio.Queue,
        error_queue: asyncio.Queue,
        db: Database,
        check_interval: int = 3600,  # 1 hour
        batch_size: int = 100
    ):
        super().__init__("content_backfill")
        self.output_queue = output_queue
        self.error_queue = error_queue
        self.db = db
        self.check_interval = check_interval
        self.batch_size = batch_size
        
    async def get_next_item(self) -> Optional[List[Any]]:
        """Wait for next check interval"""
        if not hasattr(self, '_first_run'):
            self._first_run = False
            return []  # Return empty list immediately for first run
            
        await asyncio.sleep(self.check_interval)
        return []  # Empty list triggers a new check
        
    async def put_result(self, items: List[Any]):
        """Put items in output queue"""
        for item in items:
            await self.output_queue.put(item)
            
    async def process(self, _: List[Any]) -> List[Any]:
        """Check for and process unanalyzed RSS items from both sources"""
        try:
            # Get unanalyzed items from both sources
            yf_items = await self.db.get_unanalyzed_yf_rss_items(limit=self.batch_size)
            google_news_items = await self.db.get_unanalyzed_google_news_rss_items(limit=self.batch_size)
            
            if not yf_items and not google_news_items:
                self.logger.info("No unanalyzed RSS items found")
                return []
                
            # Convert to RSSItem objects for queue
            rss_items = []
            
            # Process Yahoo Finance items
            for item in yf_items:
                # Create simplified RSSItem for queue
                rss_item = RSSItem(
                    guid=item["guid"],
                    pub_date=item["pub_date"],
                    title=item["title"]
                )
                rss_items.append(rss_item)
                
            # Process Google News items
            for item in google_news_items:
                # Create simplified RSSItem for queue
                rss_item = RSSItem(
                    guid=item["guid"],
                    pub_date=item["pub_date"],
                    title=item["title"]
                )
                rss_items.append(rss_item)
                
            self.logger.info(f"Found {len(rss_items)} unanalyzed RSS items ({len(yf_items)} from Yahoo Finance, {len(google_news_items)} from Google News)")
            return rss_items
            
        except Exception as e:
            error = PipelineError(
                guid="content_backfill",
                stage="content_backfill",
                error=str(e),
                timestamp=datetime.now(timezone.utc),
                context={
                    "batch_size": self.batch_size,
                    "check_interval": self.check_interval
                }
            )
            await self.error_queue.put(error)
            raise 