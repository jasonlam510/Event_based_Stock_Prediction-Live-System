import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timezone
from src.pipeline.worker import PipelineWorker
from pipeline.yf_rss_fetcher import YF_RSSFetcher
from src.pipeline.llm_analyzer import LLMAnalyzer
from src.pipeline.content_backfill_worker import ContentBackfillWorker
from src.pipeline.queues import AnalysisResult, PipelineError, RSSItem
from src.database import Database
from src.utils.logger import get_logger

class PipelineOrchestrator:
    """Orchestrates the news analysis pipeline"""
    
    def __init__(
        self,
        db_dsn: str,
        fetch_interval: int = 300,  # 5 minutes
        stock_name: str = "S&P500",
        model: str = "gemini-2.0-flash",
        enabled_workers: Optional[Dict[str, bool]] = None
    ):
        self.logger = get_logger("pipeline.orchestrator")
        self.fetch_interval = fetch_interval
        self.stock_name = stock_name
        self.model = model
        
        # Default enabled workers if none specified
        self.enabled_workers = enabled_workers or {
            "rss_fetcher": True,
            "llm_analyzer": True,
            "content_backfill": True
        }
        
        # Initialize database
        self.db = Database(db_dsn)
        
        # Create queues
        self.rss_queue = asyncio.Queue()
        self.analysis_queue = asyncio.Queue()
        self.error_queue = asyncio.Queue()
        
        # Create workers list
        self.workers: List[PipelineWorker] = []
        
        # Add RSS Fetcher if enabled
        if self.enabled_workers.get("rss_fetcher", True):
            self.workers.append(
                YF_RSSFetcher(
                    output_queue=self.rss_queue,
                    error_queue=self.error_queue,
                    fetch_interval=fetch_interval,
                    db=self.db
                )
            )
            
        # Add LLM Analyzer if enabled
        if self.enabled_workers.get("llm_analyzer", True):
            self.workers.append(
                LLMAnalyzer(
                    input_queue=self.rss_queue,  # Now takes RSS items directly
                    output_queue=self.analysis_queue,
                    error_queue=self.error_queue,
                    stock_name=stock_name,
                    model=model,
                    db=self.db
                )
            )
            
        # Add Content Backfill Worker if enabled
        if self.enabled_workers.get("content_backfill", True):
            self.workers.append(
                ContentBackfillWorker(
                    output_queue=self.rss_queue,
                    error_queue=self.error_queue,
                    db=self.db,
                    check_interval=3600  # Check every hour
                )
            )
            
        # Error handler task
        self._error_handler_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start all workers and error handler"""
        self.logger.info("Starting pipeline")
        self.logger.info(f"Enabled workers: {self.enabled_workers}")
        
        # Connect to database
        await self.db.connect()
        
        # Start error handler
        self._error_handler_task = asyncio.create_task(self._handle_errors())
        
        # Start all workers
        for worker in self.workers:
            await worker.start()
            
        self.logger.info("Pipeline started")
        
    async def stop(self):
        """Stop all workers and error handler"""
        self.logger.info("Stopping pipeline")
        
        # Stop all workers
        for worker in self.workers:
            await worker.stop()
            
        # Stop error handler
        if self._error_handler_task:
            self._error_handler_task.cancel()
            try:
                await self._error_handler_task
            except asyncio.CancelledError:
                pass
                
        # Disconnect from database
        await self.db.disconnect()
                
        self.logger.info("Pipeline stopped")
        
    async def _handle_errors(self):
        """Handle errors from all workers"""
        while True:
            try:
                error = await self.error_queue.get()
                self.logger.error(
                    f"Error in {error.stage} for {error.guid}: {error.error}",
                    extra={
                        "stage": error.stage,
                        "guid": error.guid,
                        "context": error.context
                    }
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in error handler: {e}")
                
    async def get_analysis_results(self) -> List[AnalysisResult]:
        """Get all analysis results currently in the queue"""
        results = []
        while not self.analysis_queue.empty():
            try:
                result = await self.analysis_queue.get()
                results.append(result)
            except asyncio.QueueEmpty:
                break
        return results
        
    async def get_latest_analysis(self, limit: int = 100) -> List[dict]:
        """Get latest analysis results from database"""
        return await self.db.get_latest_analysis(limit) 