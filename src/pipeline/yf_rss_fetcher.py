import asyncio
from datetime import datetime, timezone
from typing import Optional, List
import aiohttp
import random
from src.pipeline.worker import PipelineWorker
from src.pipeline.queues import YFRSSItem, PipelineError
from src.parsers.yf_rss_parsers import YahooFinanceParser
from src.database import Database

class YF_RSSFetcher(PipelineWorker):
    """Worker that periodically fetches RSS feeds from Yahoo Finance"""
    
    def __init__(
        self,
        output_queue: asyncio.Queue,
        error_queue: asyncio.Queue,
        db: Database,
        url: str = "https://finance.yahoo.com/rss/",
        fetch_interval: int = 300,  # 5 minutes
        max_retries: int = 3,
        initial_delay: float = 1.0
    ):
        super().__init__("yf_rss_fetcher")  # Updated name to be more specific
        self.output_queue = output_queue
        self.error_queue = error_queue
        self.db = db
        self.url = url
        self.fetch_interval = fetch_interval
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.parser = YahooFinanceParser()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start the worker and initialize session"""
        try:
            self.session = await aiohttp.ClientSession(
                headers=self.parser.headers,
                timeout=aiohttp.ClientTimeout(total=30)  # Add timeout
            ).__aenter__()
            await super().start()
        except Exception as e:
            self.logger.error(f"Failed to initialize session: {e}")
            raise
            
    async def stop(self):
        """Stop the worker and cleanup session"""
        await super().stop()
        if self.session:
            await self.session.__aexit__(None, None, None)
            
    def _ensure_timezone_aware(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone aware"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
            
    async def get_next_item(self) -> Optional[List[YFRSSItem]]:
        """Wait for next fetch interval"""
        if not hasattr(self, '_first_run'):
            self._first_run = False
            return []  # Return empty list immediately for first run
        
        await asyncio.sleep(self.fetch_interval)
        return []  # Empty list triggers a new fetch
        
    async def put_result(self, items: List[YFRSSItem]):
        """Put fetched items in output queue and store in database"""
        for item in items:
            # Store in database
            success = await self.db.store_yf_rss_item(item)  # Updated method name
            if not success:
                self.logger.error(f"Failed to store Yahoo Finance RSS item {item.guid} in database")
                continue
                
            # Put in output queue
            await self.output_queue.put(item)
            
    async def _fetch_with_retry(self) -> Optional[str]:
        """Fetch data with exponential backoff retry logic"""
        retry_count = 0
        delay = self.initial_delay

        while retry_count < self.max_retries:
            try:
                if not self.session:
                    raise RuntimeError("Session not initialized. Use RSSFetcher as an async context manager.")
                
                # Add DNS resolution timeout
                async with self.session.get(self.url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 429:
                        retry_count += 1
                        if retry_count < self.max_retries:
                            # Add jitter to avoid thundering herd problem
                            jitter = random.uniform(0, 0.1 * delay)
                            await asyncio.sleep(delay + jitter)
                            delay *= 2  # Exponential backoff
                            continue
                        else:
                            self.logger.error("Max retries reached for rate limiting")
                            return None
                    
                    response.raise_for_status()
                    return await response.text()

            except aiohttp.ClientError as e:
                self.logger.error(f"Error fetching RSS feed: {e}")
                if "429" in str(e):
                    retry_count += 1
                    if retry_count < self.max_retries:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                return None
            except asyncio.TimeoutError as e:
                self.logger.error(f"Timeout while fetching RSS feed: {e}")
                retry_count += 1
                if retry_count < self.max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                return None
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return None
                
        return None
            
    async def process(self, _: List[YFRSSItem]) -> List[YFRSSItem]:
        """Fetch and parse RSS feed"""
        try:
            # Get latest processed publication date
            latest_pub_date = await self.db.get_latest_yf_pub_date()  # Updated method name
            
            # Fetch RSS feed with retry logic
            content = await self._fetch_with_retry()
            if not content:
                return []
                
            # Parse feed
            _, items = await self.parser.parse_feed(content=content)
            if not items:
                self.logger.warning("No items found in RSS feed")
                return []
                
            # Convert to YFRSSItems and filter out already processed items
            rss_items = []
            for item in items:
                # Ensure datetime is timezone aware
                pub_date = self._ensure_timezone_aware(item.pub_date)
                
                # Skip if item is older than latest processed date
                if latest_pub_date and pub_date <= latest_pub_date:
                    self.logger.debug(f"Skipping already processed item: {item.guid} (pub_date: {pub_date})")
                    continue
                
                rss_item = YFRSSItem(
                    title=item.title,
                    link=item.link,
                    pub_date=pub_date,
                    guid=item.guid,
                    source_name=item.source_name,
                    source_url=item.source_url,
                    media_url=item.media_url,
                    media_height=item.media_height,
                    media_width=item.media_width
                )
                rss_items.append(rss_item)
                
            self.logger.info(f"Fetched {len(rss_items)} new items")
            return rss_items
            
        except Exception as e:
            error = PipelineError(
                guid="rss_fetch",
                stage="yf_rss_fetcher",  # Updated stage name
                error=str(e),
                timestamp=datetime.now(timezone.utc),
                context={"url": self.url}
            )
            await self.error_queue.put(error)
            raise 