import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime
from src.utils.logger import get_logger

class PipelineWorker(ABC):
    """Base class for all pipeline workers"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"pipeline.{name}")
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the worker"""
        if self.running:
            self.logger.warning(f"{self.name} is already running")
            return
            
        self.running = True
        self._task = asyncio.create_task(self._run())
        self.logger.info(f"{self.name} started")
        
    async def stop(self):
        """Stop the worker"""
        if not self.running:
            self.logger.warning(f"{self.name} is not running")
            return
            
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info(f"{self.name} stopped")
        
    @abstractmethod
    async def process(self, item: Any) -> Any:
        """Process a single item. Must be implemented by subclasses."""
        pass
        
    async def _run(self):
        """Main worker loop"""
        while self.running:
            try:
                # Get item from input queue
                item = await self.get_next_item()
                if item is None:
                    continue
                    
                # Process item
                try:
                    result = await self.process(item)
                    if result is not None:
                        await self.put_result(result)
                except Exception as e:
                    self.logger.error(f"Error processing item: {e}")
                    await self.handle_error(item, e)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in worker loop: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on errors
                
    @abstractmethod
    async def get_next_item(self) -> Any:
        """Get next item from input queue. Must be implemented by subclasses."""
        pass
        
    @abstractmethod
    async def put_result(self, result: Any):
        """Put result in output queue. Must be implemented by subclasses."""
        pass
        
    async def handle_error(self, item: Any, error: Exception):
        """Handle processing errors. Can be overridden by subclasses."""
        self.logger.error(f"Error processing item {item}: {error}") 