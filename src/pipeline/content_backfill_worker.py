import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from src.pipeline.worker import PipelineWorker
from src.pipeline.queues import RSSItem, PipelineError
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
        
    async def get_next_item(self) -> Optional[List[RSSItem]]:
        """Wait for next check interval"""
        if not hasattr(self, '_first_run'):
            self._first_run = False
            return []  # Return empty list immediately for first run
            
        await asyncio.sleep(self.check_interval)
        return []  # Empty list triggers a new check
        
    async def put_result(self, items: List[RSSItem]):
        """Put items in output queue"""
        for item in items:
            await self.output_queue.put(item)
            
    async def process(self, _: List[RSSItem]) -> List[RSSItem]:
        """Check for and process unanalyzed RSS items"""
        try:
            # Get unanalyzed RSS items
            unanalyzed_items = await self.db.get_unanalyzed_rss_items(limit=self.batch_size)
            
            if not unanalyzed_items:
                self.logger.info("No unanalyzed RSS items found")
                return []
                
            # Convert to RSSItem objects
            rss_items = []
            for item in unanalyzed_items:
                rss_item = RSSItem(
                    title=item["title"],
                    link=item["link"],
                    pub_date=item["pub_date"],
                    guid=item["guid"],
                    source_name=item["source_name"],
                    source_url=item["source_url"],
                    media_url=item["media_url"],
                    media_height=item["media_height"],
                    media_width=item["media_width"]
                )
                rss_items.append(rss_item)
                
            self.logger.info(f"Found {len(rss_items)} unanalyzed RSS items")
            return rss_items
            
        except Exception as e:
            error = PipelineError(
                guid="content_backfill",
                stage="content_backfill",
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
            await self.error_queue.put(error)
            raise 