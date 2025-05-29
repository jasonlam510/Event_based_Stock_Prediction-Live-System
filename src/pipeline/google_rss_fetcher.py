import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Set
import aiohttp
import random
from src.pipeline.worker import PipelineWorker
from src.pipeline.queues import GoogleNewsRSSItem, PipelineError
from parsers.google_rss_parsers import GoogleNewsParser
from src.database import Database

class GoogleNewsFetcher(PipelineWorker):
    """Worker that periodically fetches RSS feeds from Google News"""
    
    def __init__(
        self,
        output_queue: asyncio.Queue,
        error_queue: asyncio.Queue,
        db: Database,
        urls: List[str] = [
            "https://news.google.com/rss",
            "https://news.google.com/rss/search?q=stock+market&hl=en-US&gl=US&ceid=US:en"
        ],
        fetch_interval: int = 300,  # 5 minutes
        max_retries: int = 3,
        initial_delay: float = 1.0
    ):
        super().__init__("google_news_fetcher")
        self.output_queue = output_queue
        self.error_queue = error_queue
        self.db = db
        self.urls = urls
        self.fetch_interval = fetch_interval
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.parser = GoogleNewsParser()
        self.session: Optional[aiohttp.ClientSession] = None
        self.processed_guids: Set[str] = set()  # Track processed GUIDs to avoid duplicates
        
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
            
    async def get_next_item(self) -> Optional[List[GoogleNewsRSSItem]]:
        """Wait for next fetch interval"""
        if not hasattr(self, '_first_run'):
            self._first_run = False
            return []  # Return empty list immediately for first run
        
        await asyncio.sleep(self.fetch_interval)
        return []  # Empty list triggers a new fetch
        
    async def put_result(self, items: List[GoogleNewsRSSItem]):
        """Put fetched items in output queue and store in database"""
        for item in items:
            # Skip if we've already processed this GUID
            if item.guid in self.processed_guids:
                continue
                
            # Store in database
            success = await self.db.store_google_news_rss_item(item)
            if not success:
                self.logger.error(f"Failed to store Google News RSS item {item.guid} in database")
                continue
                
            # Add to processed GUIDs
            self.processed_guids.add(item.guid)
            
            # Put in output queue
            await self.output_queue.put(item)
            
    async def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch data with exponential backoff retry logic"""
        retry_count = 0
        delay = self.initial_delay

        while retry_count < self.max_retries:
            try:
                if not self.session:
                    raise RuntimeError("Session not initialized. Use RSSFetcher as an async context manager.")
                
                # Add DNS resolution timeout
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 429:
                        retry_count += 1
                        if retry_count < self.max_retries:
                            # Add jitter to avoid thundering herd problem
                            jitter = random.uniform(0, 0.1 * delay)
                            await asyncio.sleep(delay + jitter)
                            delay *= 2  # Exponential backoff
                            continue
                        else:
                            self.logger.error(f"Max retries reached for rate limiting on URL: {url}")
                            return None
                    
                    response.raise_for_status()
                    return await response.text()

            except aiohttp.ClientError as e:
                self.logger.error(f"Error fetching RSS feed from {url}: {e}")
                if "429" in str(e):
                    retry_count += 1
                    if retry_count < self.max_retries:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                return None
            except asyncio.TimeoutError as e:
                self.logger.error(f"Timeout while fetching RSS feed from {url}: {e}")
                retry_count += 1
                if retry_count < self.max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                return None
            except Exception as e:
                self.logger.error(f"Unexpected error fetching {url}: {e}")
                return None
                
        return None
            
    async def process(self, _: List[GoogleNewsRSSItem]) -> List[GoogleNewsRSSItem]:
        """Fetch and parse RSS feeds from all URLs"""
        try:
            # Get latest processed publication date
            latest_pub_date = await self.db.get_latest_google_news_pub_date()
            
            # Clear processed GUIDs set at the start of each process cycle
            self.processed_guids.clear()
            
            all_rss_items = []
            
            # Process each URL
            for url in self.urls:
                # Fetch RSS feed with retry logic
                content = await self._fetch_with_retry(url)
                if not content:
                    continue
                    
                # Parse feed
                _, items = await self.parser.parse_feed(content=content)
                if not items:
                    self.logger.warning(f"No items found in RSS feed from {url}")
                    continue
                    
                # Convert to GoogleNewsRSSItems and filter out already processed items
                for item in items:
                    # Ensure datetime is timezone aware
                    pub_date = self._ensure_timezone_aware(item.pub_date)
                    
                    # Skip if item is older than latest processed date
                    if latest_pub_date and pub_date <= latest_pub_date:
                        self.logger.debug(f"Skipping already processed item: {item.guid} (pub_date: {pub_date})")
                        continue
                    
                    rss_item = GoogleNewsRSSItem(
                        title=item.title,
                        link=item.link,
                        pub_date=pub_date,
                        guid=item.guid,
                        source_name=item.source_name,
                        source_url=item.source_url,
                        description=None,  # We don't parse description from NewsItem
                        is_perma_link=False  # We don't parse is_perma_link from NewsItem
                    )
                    all_rss_items.append(rss_item)
                    
            self.logger.info(f"Fetched {len(all_rss_items)} new items from {len(self.urls)} feeds")
            return all_rss_items
            
        except Exception as e:
            error = PipelineError(
                guid="rss_fetch",
                stage="google_news_fetcher",
                error=str(e),
                timestamp=datetime.now(timezone.utc),
                context={
                    "urls": self.urls,
                    "fetch_interval": self.fetch_interval
                }
            )
            await self.error_queue.put(error)
            raise 