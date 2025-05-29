import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from src.pipeline.worker import PipelineWorker
from src.pipeline.queues import RSSItem, AnalysisResult, PipelineError
from src.llm.gemini_news_analyzer import analyze_news
from src.database import Database
from src.utils.logger import get_logger

class LLMAnalyzer(PipelineWorker):
    """Worker that analyzes content using Gemini LLM"""
    
    def __init__(
        self,
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        error_queue: asyncio.Queue,
        db: Database,
        stock_name: str = "S&P500",
        model: str = "gemini-2.0-flash"
    ):
        super().__init__("llm_analyzer")
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.error_queue = error_queue
        self.db = db
        self.stock_name = stock_name
        self.model = model
        
    async def get_next_item(self) -> Optional[RSSItem]:
        """Get next RSS item from input queue"""
        try:
            return await self.input_queue.get()
        except asyncio.CancelledError:
            return None
            
    async def put_result(self, result: AnalysisResult):
        """Put analysis result in output queue and store in database"""
        # Store in database
        success = await self.db.store_analysis_result(result)
        if not success:
            self.logger.error(f"Failed to store analysis result {result.guid} in database")
            return
            
        # Put in output queue
        await self.output_queue.put(result)
        
    async def process(self, item: RSSItem) -> Optional[AnalysisResult]:
        """Analyze RSS item title using Gemini"""
        try:
            # Analyze title
            analysis = await analyze_news(
                content=item.title,  # Use title instead of content
                content_name="title",
                stock_name=self.stock_name,
                model=self.model
            )
            
            # Create metadata
            metadata: Dict[str, Any] = {
                "source_name": item.source_name,
                "source_url": str(item.source_url) if item.source_url else None,
                "media_url": str(item.media_url) if item.media_url else None,
                "pub_date": item.pub_date.isoformat()
            }
            
            # Create result
            result = AnalysisResult(
                guid=item.guid,
                sentiment_score=analysis.sentiment_score,
                relevance_score=analysis.relevance_score,
                event_importance=analysis.event_importance,
                event_type=analysis.event_type,
                analysis_timestamp=datetime.now(timezone.utc),
                raw_content=item.title,  # Store title as raw content
                metadata=metadata
            )
            
            self.logger.info(f"Analyzed title for {item.guid}")
            return result
            
        except Exception as e:
            error = PipelineError(
                guid=item.guid,
                stage="llm_analyzer",
                error=str(e),
                timestamp=datetime.now(timezone.utc),
                context={
                    "url": str(item.link),
                    "title_length": len(item.title)
                }
            )
            await self.error_queue.put(error)
            raise 