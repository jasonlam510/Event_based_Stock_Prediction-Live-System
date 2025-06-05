import aiohttp

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Tuple, Optional
from src.parsers.base import RSSParser
from pipeline.models import Channel, NewsItem
from src.utils.logger import get_logger

logger = get_logger(__name__)

class GoogleNewsParser(RSSParser):
    """Parser for Google News RSS feeds."""
    
    def __init__(self):
        # Set a proper user agent for Google News
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

    def _validate_google_news_feed(self, root: ET.Element) -> bool:
        """Validate if the RSS feed is from Google News"""
        try:
            channel = root.find('channel')
            if channel is None:
                return False
            
            title = channel.find('title')
            if title is None or 'Google News' not in title.text:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating Google News feed: {e}")
            return False

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in RFC 822 format"""
        try:
            # Google News uses RFC 822 format
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.error(f"Failed to parse date '{date_str}': {e}")
            raise

    def _parse_item(self, item: ET.Element) -> Optional[NewsItem]:
        """Parse a single RSS item into a NewsItem model"""
        try:
            # Parse source
            source_elem = item.find('source')
            source_name = source_elem.text if source_elem is not None else None
            source_url = source_elem.get('url') if source_elem is not None else None

            # Parse guid
            guid_elem = item.find('guid')
            guid = guid_elem.text if guid_elem is not None else None
            is_perma_link = guid_elem.get('isPermaLink') == 'true' if guid_elem is not None else False

            # Parse pubDate
            pub_date = self._parse_date(item.find('pubDate').text)

            # Create NewsItem
            return NewsItem(
                title=item.find('title').text,
                link=item.find('link').text,
                pub_date=pub_date,
                guid=guid,
                source_name=source_name,
                source_url=source_url,
                # Google News doesn't have media content
                media_url=None,
                media_height=None,
                media_width=None
            )
        except Exception as e:
            logger.error(f"Error parsing RSS item: {e}")
            return None

    def _parse_channel(self, channel: ET.Element) -> Channel:
        """Parse channel information into a Channel model"""
        # Since we don't use channel data, return a dummy channel
        return Channel(
            title="Google News",
            link="https://news.google.com",
            description="Google News RSS Feed",
            language="en",
            copyright="Google News",
            pub_date=datetime.now(timezone.utc),
            ttl=60,
            image_title="Google News",
            image_link="https://news.google.com",
            image_url="https://news.google.com"
        )

    async def parse_feed(self, content: str) -> Tuple[Channel, List[NewsItem]]:
        """Parse Google News RSS feed.
        
        Args:
            content (str): The XML content to parse
            
        Returns:
            Tuple[Channel, List[NewsItem]]: A tuple containing the channel information
            and a list of news items
        """
        try:
            if content is None:
                logger.error("Content must be provided")
                return None, []
                    
            # Parse the XML content
            root = ET.fromstring(content)
            
            # Validate if it's a Google News feed
            if not self._validate_google_news_feed(root):
                logger.error("Invalid Google News RSS feed")
                return None, []
            
            # Parse channel information (dummy since we don't use it)
            channel = root.find('channel')
            channel_info = self._parse_channel(channel)
            
            # Parse all items
            items = []
            for item in root.findall('.//item'):
                news_item = self._parse_item(item)
                if news_item:
                    items.append(news_item)
            
            return channel_info, items
                
        except ET.ParseError as e:
            logger.error(f"Error parsing XML: {e}")
            return None, []
        except Exception as e:
            logger.error(f"Error parsing Google News RSS feed: {str(e)}")
            return None, [] 