import aiohttp
from bs4 import BeautifulSoup
from typing import Optional
from src.extractors.base import ContentExtractor
from src.utils.logger import get_logger
from playwright.async_api import async_playwright, TimeoutError

logger = get_logger(__name__)

class YahooFinanceExtractor(ContentExtractor):
    """Extractor for Yahoo Finance article content."""
    
    def __init__(self):
        # Set headers exactly as they appear in the browser request
        self.headers = {
            'authority': 'finance.yahoo.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
        }
    
    async def extract_content(self, url: str) -> Optional[str]:
        """Extract description from a Yahoo Finance article URL.
        
        Args:
            url (str): The URL of the Yahoo Finance article
            
        Returns:
            Optional[str]: The extracted article description from meta tag, or None if extraction failed
        """
        try:
            async with async_playwright() as p:
                # Launch browser with specific options
                browser = await p.chromium.launch(
                    headless=True
                )
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=self.headers['user-agent']
                )
                page = await context.new_page()
                
                # Set headers
                await page.set_extra_http_headers(self.headers)
                
                # Navigate to URL with more specific waiting conditions
                logger.info(f"Navigating to {url}")
                response = await page.goto(
                    url,
                    wait_until='networkidle',  # Wait for network to be idle
                    timeout=30000  # Increase timeout to 30 seconds
                )
                
                if not response:
                    logger.error("Failed to get response from page")
                    return None
                
                logger.info(f"Page loaded with status: {response.status}")
                
                # Handle cookie consent banner if present
                try:
                    logger.info("Checking for cookie consent banner...")
                    # Wait for and click the accept button
                    await page.wait_for_selector('button[type="submit"]', timeout=5000)
                    await page.click('button[type="submit"]')
                    logger.info("Accepted cookie consent")
                    # Wait a bit for the banner to disappear
                    await page.wait_for_timeout(1000)
                except TimeoutError:
                    logger.info("No cookie consent banner found or already accepted")
                
                # Debug: Get and log the page content
                content = await page.content()
                logger.debug("Page content: %s", content)
                
                # Debug: Get all meta tags
                meta_tags = await page.evaluate('''() => {
                    const metas = document.getElementsByTagName('meta');
                    return Array.from(metas).map(meta => ({
                        name: meta.getAttribute('name'),
                        content: meta.getAttribute('content')
                    }));
                }''')
                logger.debug("Meta tags found: %s", meta_tags)
                
                # Wait for meta description to be available and get its content
                description = await page.evaluate('''() => {
                    const meta = document.querySelector('meta[name="description"]');
                    return meta ? meta.getAttribute('content') : null;
                }''')
                
                if not description:
                    # If not found, try to force a page reload
                    logger.info("Meta description not found, trying page reload...")
                    await page.reload(wait_until='networkidle')
                    await page.wait_for_timeout(5000)
                    
                    description = await page.evaluate('''() => {
                        const meta = document.querySelector('meta[name="description"]');
                        return meta ? meta.getAttribute('content') : null;
                    }''')
                
                if description:
                    logger.info("Successfully extracted meta description")
                    return description
                
                logger.warning(f"No meta description found at {url}")
                return None
                    
        except TimeoutError as e:
            logger.error(f"Timeout waiting for content at {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error extracting description from {url}: {str(e)}")
            return None
        finally:
            # Ensure browser is closed even if an error occurs
            try:
                await context.close()
                await browser.close()
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}") 