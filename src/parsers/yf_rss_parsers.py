import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Tuple, Optional
from src.parsers.base import RSSParser
from pipeline.models import Channel, NewsItem
from src.utils.logger import get_logger

logger = get_logger(__name__)

class YahooFinanceParser(RSSParser):
    """Parser for Yahoo Finance RSS feeds."""
    
    def __init__(self):
        # Set a proper user agent that's allowed by Yahoo Finance
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

    def _validate_yahoo_finance_feed(self, root: ET.Element) -> bool:
        """Validate if the RSS feed is from Yahoo Finance"""
        try:
            channel = root.find('channel')
            if channel is None:
                return False
            
            title = channel.find('title')
            if title is None or 'Yahoo Finance' not in title.text:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating Yahoo Finance feed: {e}")
            return False

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in either RFC 822 or ISO 8601 format"""
        try:
            # Try ISO 8601 format first
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try RFC 822 format
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

            # Parse media content
            media_content_elem = item.find('.//{http://search.yahoo.com/mrss/}content')
            media_url = media_content_elem.get('url') if media_content_elem is not None else None
            media_height = media_content_elem.get('height') if media_content_elem is not None else None
            media_width = media_content_elem.get('width') if media_content_elem is not None else None

            # Parse pubDate
            pub_date = self._parse_date(item.find('pubDate').text)

            # Create NewsItem
            return NewsItem(
                title=item.find('title').text,
                link=item.find('link').text,
                pub_date=pub_date,
                guid=item.find('guid').text,
                source_name=source_name,
                source_url=source_url,
                media_url=media_url,
                media_height=media_height,
                media_width=media_width
            )
        except Exception as e:
            logger.error(f"Error parsing RSS item: {e}")
            return None

    def _parse_channel(self, channel: ET.Element) -> Channel:
        """Parse channel information into a Channel model"""
        image_elem = channel.find('image')
        
        # Parse pubDate
        pub_date = self._parse_date(channel.find('pubDate').text)

        return Channel(
            title=channel.find('title').text,
            link=channel.find('link').text,
            description=channel.find('description').text,
            language=channel.find('language').text,
            copyright=channel.find('copyright').text,
            pub_date=pub_date,
            ttl=int(channel.find('ttl').text),
            image_title=image_elem.find('title').text,
            image_link=image_elem.find('link').text,
            image_url=image_elem.find('url').text
        )

    async def parse_feed(self, content: str) -> Tuple[Channel, List[NewsItem]]:
        """Parse Yahoo Finance RSS feed.
        
        Args:
            content (str): The XML content to parse
            url (str, optional): The URL of the RSS feed. Only needed if content is not provided.
            
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
            
            # Validate if it's a Yahoo Finance feed
            if not self._validate_yahoo_finance_feed(root):
                logger.error("Invalid Yahoo Finance RSS feed")
                return None, []
            
            # Parse channel information
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
            logger.error(f"Error parsing Yahoo Finance RSS feed: {str(e)}")
            return None, [] 