import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import asyncio
from src.pipeline.worker import PipelineWorker
from src.database import Database
from src.utils.logger import get_logger
from src.pipeline.calculators.ti_calculator import TICalculator
from src.pipeline.fetchers.yf_price_fetcher import YFPriceFetcher
from src.pipeline.queues import StockData

class TIBackfillWorker(YFPriceFetcher):
    """Worker that backfills technical indicators for historical data"""
    
    def __init__(
        self,
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        error_queue: asyncio.Queue,
        db: Database,
        symbols: list[str],
        batch_size: int = 100,
        fetch_interval: int = 3600  # 1 hour
    ):
        # Initialize with the queues since we need them for the TI calculator
        super().__init__(
            input_queue=input_queue,
            output_queue=output_queue,
            error_queue=error_queue,
            db=db,
            symbols=symbols,
            interval="1d",
            lookback_days=365,  # Always fetch 1 year of data
            fetch_interval=fetch_interval
        )
        self.name = "ti_backfill"  # Override the name
        self.batch_size = batch_size
        
    async def get_next_item(self) -> Optional[str]:
        """Get next symbol to process"""
        if not hasattr(self, '_first_run'):
            self._first_run = False
            # Return first symbol immediately for first run
            return self.symbols[0] if self.symbols else None
            
        # For subsequent runs, wait for fetch interval
        await asyncio.sleep(self.fetch_interval)
        return self.symbols[0] if self.symbols else None
        
    async def process(self, symbol: Optional[str] = None) -> Optional[StockData]:
        """Process a symbol to calculate indicators for historical data
        
        Args:
            symbol (Optional[str]): Symbol to process
            
        Returns:
            Optional[StockData]: StockData object with price data for TI calculator
        """
        try:
            if symbol is None:
                return None
                
            # Get historical data without indicators
            df = await self.db.get_stock_data_without_indicators(
                symbol=symbol,
                limit=self.batch_size
            )
            
            if df is not None and not df.empty:
                # Create StockData object for TI calculator
                result = StockData(
                    symbol=symbol,
                    data=df
                )
                self.logger.info(f"Found {len(df)} records to process for {symbol}")
                return result
            else:
                self.logger.info(f"No data to process for {symbol}")
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error in TI backfill worker: {e}")
            await self.error_queue.put({
                'error': str(e),
                'worker': self.name
            })
            return None 