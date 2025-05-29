import aiohttp
from bs4 import BeautifulSoup
from typing import Optional
from archive.extractors.base import ContentExtractor
from src.utils.logger import get_logger
from playwright.async_api import async_playwright, TimeoutError
import json
import os
from pathlib import Path
from datetime import datetime

logger = get_logger(__name__)

class YahooFinanceExtractor(ContentExtractor):
    """Extractor for Yahoo Finance article content."""
    
    def __init__(self):
        self.healess=True
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
        # Create cookies directory if it doesn't exist
        self.cookies_dir = Path("cookies")
        self.cookies_dir.mkdir(exist_ok=True)
        self.cookies_file = self.cookies_dir / "yahoo_finance_cookies.json"
    
    def _load_cookies(self) -> Optional[list]:
        """Load cookies from file if they exist and are not expired."""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    
                # Check if any essential cookies are expired
                current_time = datetime.now().timestamp()
                for cookie in cookies:
                    if 'expires' in cookie:
                        try:
                            # Convert expires to timestamp if it's a string
                            if isinstance(cookie['expires'], str):
                                expires = datetime.fromisoformat(cookie['expires'].replace('Z', '+00:00')).timestamp()
                            else:
                                expires = cookie['expires']
                            
                            if expires < current_time:
                                logger.info("Cookies are expired, will need to refresh")
                                return None
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error checking cookie expiration: {e}")
                            continue
                
                return cookies
            except Exception as e:
                logger.error(f"Error loading cookies: {e}")
        return None
    
    def _save_cookies(self, cookies: list):
        """Save cookies to file."""
        try:
            # Filter out session cookies and expired cookies
            current_time = datetime.now().timestamp()
            valid_cookies = []
            for cookie in cookies:
                # Skip session cookies
                if cookie.get('session', False):
                    continue
                    
                # Skip expired cookies
                if 'expires' in cookie:
                    try:
                        if isinstance(cookie['expires'], str):
                            expires = datetime.fromisoformat(cookie['expires'].replace('Z', '+00:00')).timestamp()
                        else:
                            expires = cookie['expires']
                            
                        if expires < current_time:
                            continue
                    except (ValueError, TypeError):
                        continue
                        
                valid_cookies.append(cookie)
            
            with open(self.cookies_file, 'w') as f:
                json.dump(valid_cookies, f)
            logger.info(f"Saved {len(valid_cookies)} valid cookies")
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")
    
    async def extract_content(self, url: str) -> Optional[str]:
        """Extract description from a Yahoo Finance article URL.
        
        Args:
            url (str): The URL of the Yahoo Finance article
            
        Returns:
            Optional[str]: The extracted article description from meta tag, or None if extraction failed
        """
        browser = None
        context = None
        try:
            p = await async_playwright().start()
            # Launch browser with specific options
            browser = await p.chromium.launch(
                headless=self.healess
            )
            
            # Load existing cookies
            stored_cookies = self._load_cookies()
            cookies_valid = bool(stored_cookies)
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.headers['user-agent']
            )
            
            # Add stored cookies if they exist
            if stored_cookies:
                await context.add_cookies(stored_cookies)
                logger.info("Loaded stored cookies")
            
            page = await context.new_page()
            
            # Set headers
            await page.set_extra_http_headers(self.headers)
            
            # Navigate to URL with more specific waiting conditions
            logger.info(f"Navigating to {url}")
            response = await page.goto(
                url,
                wait_until='domcontentloaded',  # Wait for initial HTML to be loaded
                timeout=30000  # 30 seconds timeout
            )
            
            if not response:
                logger.error("Failed to get response from page")
                return None
            
            logger.info(f"Page loaded with status: {response.status}")
            
            # Check if we need to handle cookie consent
            if not cookies_valid or response.status == 403:  # 403 might indicate expired/invalid cookies
                try:
                    logger.info("Checking for cookie consent banner...")
                    # Wait for and click the accept button
                    await page.wait_for_selector('button[type="submit"]', timeout=5000)
                    await page.click('button[type="submit"]')
                    logger.info("Accepted cookie consent")
                    # Wait a bit for the banner to disappear
                    await page.wait_for_timeout(1000)
                    
                    # Save new cookies
                    cookies = await context.cookies()
                    self._save_cookies(cookies)
                except TimeoutError:
                    logger.info("No cookie consent banner found")
            else:
                logger.info("Using valid stored cookies, skipping cookie consent check")
            
            # Wait for meta description to be available and get its content
            description = await page.evaluate('''() => {
                const meta = document.querySelector('meta[name="description"]');
                return meta ? meta.getAttribute('content') : null;
            }''')
            
            if not description:
                # If not found, try to force a page reload with specific wait conditions
                logger.info("Meta description not found, trying page reload...")
                await page.reload(wait_until='domcontentloaded')
                await page.wait_for_selector('article, meta[name="description"]', timeout=10000)
                
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
            if context:
                try:
                    await context.close()
                except Exception as e:
                    logger.error(f"Error closing context: {str(e)}")
            if browser:
                try:
                    await browser.close()
                except Exception as e:
                    logger.error(f"Error closing browser: {str(e)}")
            if 'p' in locals():
                try:
                    await p.stop()
                except Exception as e:
                    logger.error(f"Error stopping playwright: {str(e)}") 