import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import asyncio
from typing import Optional, List, Dict
from src.utils.logger import get_logger
from src.database import Database
from src.pipeline.queues import StockData
from src.pipeline.worker import PipelineWorker

class YFPriceFetcher(PipelineWorker):
    """Fetches stock price data from Yahoo Finance"""
    
    def __init__(
        self,
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        error_queue: asyncio.Queue,
        db: Database,
        symbols: List[str],
        interval: str = "1d",
        lookback_days: int = 365,  # 1 year for all fetches
        fetch_interval: int = 3600  # 1 hour
    ):
        super().__init__("price_fetcher")
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.error_queue = error_queue
        self.db = db
        self.symbols = symbols
        self.interval = interval
        self.lookback_days = lookback_days
        self.fetch_interval = fetch_interval
        self.logger = get_logger(__name__)
        
    async def get_next_item(self) -> Optional[str]:
        """Get next symbol to fetch
        
        Returns:
            Optional[str]: Symbol to fetch or None if no more symbols
        """
        if not hasattr(self, '_first_run'):
            self._first_run = False
            # Return first symbol immediately for first run
            return self.symbols[0] if self.symbols else None
            
        # For subsequent runs, wait for fetch interval
        await asyncio.sleep(self.fetch_interval)
        return self.symbols[0] if self.symbols else None
        
    async def put_result(self, result: StockData):
        """Put fetched data in output queue
        
        Args:
            result (StockData): Stock data to put in queue
        """
        if result is not None:
            await self.output_queue.put(result)
            self.logger.info(f"Queued data for {result.symbol}")
        
    async def fetch_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch stock data for a symbol
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            Optional[pd.DataFrame]: DataFrame containing stock data or None if error
        """
        try:
            # Calculate date range - always fetch 1 year of data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            self.logger.debug(f"Fetching data for {symbol} from {start_date} to {end_date}")
            
            # Fetch data
            stock = yf.Ticker(symbol)
            df = stock.history(
                start=start_date,
                end=end_date,
                interval=self.interval
            )
            
            if df.empty:
                self.logger.warning(f"No data found for {symbol}")
                return None
                
            # Log the original columns and first few rows
            self.logger.debug(f"Original columns from yfinance for {symbol}: {df.columns.tolist()}")
            self.logger.debug(f"First few rows of data:\n{df.head()}")
            
            # Add symbol column
            df['symbol'] = symbol
            
            # Reset index to make Date a column
            df = df.reset_index()
            
            # Log columns after reset_index
            self.logger.debug(f"Columns after reset_index for {symbol}: {df.columns.tolist()}")
            self.logger.debug(f"First few rows after reset_index:\n{df.head()}")
            
            # Check if Date column exists
            if 'Date' not in df.columns:
                self.logger.error(f"Date column not found in DataFrame for {symbol}. Available columns: {df.columns.tolist()}")
                return None
            
            # Convert timezone-aware timestamps to UTC
            df['Date'] = df['Date'].dt.tz_convert('UTC')
            
            # Convert column names to match database
            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Log final columns and data
            self.logger.debug(f"Final columns for {symbol}: {df.columns.tolist()}")
            self.logger.debug(f"Final data shape: {df.shape}")
            self.logger.debug(f"First few rows of final data:\n{df.head()}")
            
            self.logger.info(f"Successfully fetched {len(df)} records for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
            self.logger.debug(f"Error type: {type(e)}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
            
    async def process(self, symbol: Optional[str] = None) -> Optional[StockData]:
        """Process a symbol to fetch data
        
        Args:
            symbol (Optional[str]): Symbol to fetch data for
            
        Returns:
            Optional[StockData]: Stock data if successful, None otherwise
        """
        try:
            if symbol is None:
                return None
                
            # Fetch data
            df = await self.fetch_stock_data(symbol)
            
            if df is not None:
                # Store in database and get new/updated data
                new_data = await self.db.store_stock_data(df)
                
                if new_data is not None:
                    # Create StockData object
                    result = StockData(
                        symbol=symbol,
                        data=new_data
                    )
                    self.logger.info(f"Stored {len(new_data)} new/updated data points for {symbol}")
                    return result
                else:
                    self.logger.info(f"No new data to store for {symbol}")
            else:
                await self.error_queue.put(f"No data found for {symbol}")
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error in price fetcher process: {e}")
            await self.error_queue.put(str(e))
            return None 