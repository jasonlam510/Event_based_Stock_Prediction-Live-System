import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from src.pipeline.worker import PipelineWorker
from src.pipeline.queues import RSSItem, ExtractedContent, PipelineError
from archive.extractors.yf_news_extractors import YahooFinanceExtractor
from src.database import Database
from src.utils.logger import get_logger

class ContentExtractor(PipelineWorker):
    """Worker that extracts content from news articles"""
    
    def __init__(
        self,
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        error_queue: asyncio.Queue,
        db: Database,
        max_retries: int = 3
    ):
        super().__init__("content_extractor")
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.error_queue = error_queue
        self.db = db
        self.max_retries = max_retries
        self.extractor = YahooFinanceExtractor()
        
    async def get_next_item(self) -> Optional[RSSItem]:
        """Get next RSS item from input queue"""
        try:
            return await self.input_queue.get()
        except asyncio.CancelledError:
            return None
            
    async def put_result(self, result: ExtractedContent):
        """Put extracted content in output queue and store in database"""
        # Store in database
        success = await self.db.store_extracted_content(result)
        if not success:
            self.logger.error(f"Failed to store extracted content {result.guid} in database")
            return
            
        # Put in output queue
        await self.output_queue.put(result)
        
    async def process(self, item: RSSItem) -> Optional[ExtractedContent]:
        """Extract content from news article"""
        try:
            # Extract content
            content = await self.extractor.extract_content(str(item.link))
            if not content:
                self.logger.warning(f"Could not extract content for {item.guid}")
                return None
                
            # Create metadata
            metadata: Dict[str, Any] = {
                "title": item.title,
                "source_name": item.source_name,
                "source_url": str(item.source_url) if item.source_url else None,
                "media_url": str(item.media_url) if item.media_url else None,
                "media_height": item.media_height,
                "media_width": item.media_width
            }
            
            # Create result
            result = ExtractedContent(
                guid=item.guid,
                url=item.link,
                content=content,
                extraction_timestamp=datetime.now(timezone.utc),
                metadata=metadata
            )
            
            self.logger.info(f"Extracted content for {item.guid}")
            return result
            
        except Exception as e:
            error = PipelineError(
                guid=item.guid,
                stage="content_extractor",
                error=str(e),
                timestamp=datetime.now(timezone.utc),
                context={"url": str(item.link)}
            )
            await self.error_queue.put(error)
            raise 