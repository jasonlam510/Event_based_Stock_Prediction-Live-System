import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import asyncio
from src.pipeline.worker import PipelineWorker
from src.database import Database
from src.utils.logger import get_logger
from ta.trend import SMAIndicator, EMAIndicator, MACD, CCIIndicator, ADXIndicator, VortexIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, MFIIndicator, VolumeWeightedAveragePrice

class TICalculator(PipelineWorker):
    """Worker that calculates technical indicators from price data"""
    
    # Define the list of indicators to calculate
    BALANCED_INDICATORS = [
        {'name': 'bb', 'window': 20},          # Bollinger Bands
        {'name': 'ma', 'window': 50},          # Simple Moving Average
        {'name': 'ema', 'window': 12},         # Exponential Moving Average
        {'name': 'rsi', 'window': 14},         # Relative Strength Index
        {'name': 'macd', 'window': 26},        # MACD slow window (fast=12, signal=9)
        {'name': 'atr', 'window': 14},         # Average True Range
        {'name': 'cci', 'window': 20},         # Commodity Channel Index
        {'name': 'stochastic', 'window': 14},  # Stochastic oscillator (%K)
        {'name': 'adx', 'window': 14},         # Average Directional Index
        {'name': 'vortex', 'window': 14},      # Vortex Indicator
        {'name': 'obv'},                       # On-Balance Volume
        {'name': 'mfi', 'window': 14},         # Money Flow Index
        {'name': 'vwap'}                       # Volume-Weighted Average Price
    ]
    
    def __init__(
        self,
        input_queue: asyncio.Queue,
        error_queue: asyncio.Queue,
        db: Database,
        lookback_days: int = 30  # Days of historical data needed for calculations
    ):
        super().__init__("ti_calculator")
        self.input_queue = input_queue
        self.error_queue = error_queue
        self.db = db
        self.lookback_days = lookback_days
        self.logger = get_logger(__name__)
        
    async def get_next_item(self):
        """Get next item from input queue"""
        return await self.input_queue.get()
        
    async def put_result(self, result):
        """Put result in output queue"""
        # No output queue needed as we store directly to database
        pass
        
    def calculate_technical_indicators(self, price_df: pd.DataFrame, indicators: List[Dict]) -> pd.DataFrame:
        """
        Calculate technical indicators for the given price data using ta library.
        
        Args:
            price_df (pd.DataFrame): Price data with OHLCV columns
            indicators (List[Dict]): List of indicator configurations
            
        Returns:
            pd.DataFrame: DataFrame with calculated indicators
        """
        if price_df is None:
            raise ValueError("DataFrame is not initialized")
        
        df = price_df.copy()
        
        for indicator in indicators:
            name = indicator['name']
            window = indicator.get('window', None)
            
            try:
                if name == 'bb':
                    bb = BollingerBands(close=df['close'], window=window)
                    df[f'bb_upper_{window}'] = bb.bollinger_hband()
                    df[f'bb_middle_{window}'] = bb.bollinger_mavg()
                    df[f'bb_lower_{window}'] = bb.bollinger_lband()
                    
                elif name == 'ma':
                    ma = SMAIndicator(close=df['close'], window=window)
                    df[f'ma_{window}'] = ma.sma_indicator()
                    
                elif name == 'ema':
                    ema = EMAIndicator(close=df['close'], window=window)
                    df[f'ema_{window}'] = ema.ema_indicator()
                    
                elif name == 'rsi':
                    rsi = RSIIndicator(close=df['close'], window=window)
                    df[f'rsi_{window}'] = rsi.rsi()
                    
                elif name == 'macd':
                    macd = MACD(close=df['close'], window_slow=window, window_fast=12, window_sign=9)
                    df[f'macd_{window}'] = macd.macd()
                    df[f'macd_signal_{window}'] = macd.macd_signal()
                    df[f'macd_hist_{window}'] = macd.macd_diff()
                    
                elif name == 'atr':
                    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=window)
                    df[f'atr_{window}'] = atr.average_true_range()
                    
                elif name == 'cci':
                    cci = CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=window)
                    df[f'cci_{window}'] = cci.cci()
                    
                elif name == 'stochastic':
                    stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=window)
                    df[f'stoch_k_{window}'] = stoch.stoch()
                    df[f'stoch_d_{window}'] = stoch.stoch_signal()
                    
                elif name == 'adx':
                    adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=window)
                    df[f'adx_{window}'] = adx.adx()
                    df[f'di_pos_{window}'] = adx.adx_pos()
                    df[f'di_neg_{window}'] = adx.adx_neg()
                    
                elif name == 'vortex':
                    vortex = VortexIndicator(high=df['high'], low=df['low'], close=df['close'], window=window)
                    df[f'vortex_pos_{window}'] = vortex.vortex_indicator_pos()
                    df[f'vortex_neg_{window}'] = vortex.vortex_indicator_neg()
                    
                elif name == 'obv':
                    obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume'])
                    df['obv'] = obv.on_balance_volume()
                    
                elif name == 'mfi':
                    mfi = MFIIndicator(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=window)
                    df[f'mfi_{window}'] = mfi.money_flow_index()
                    
                elif name == 'vwap':
                    vwap = VolumeWeightedAveragePrice(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'])
                    df['vwap'] = vwap.volume_weighted_average_price()

                else:
                    raise ValueError(f"Unknown indicator: {name}")
                    
            except Exception as e:
                self.logger.error(f"Error calculating {name} indicator: {str(e)}")
                # Dont continue with next indicator if one fails
        
        return df
            
    async def process(self, data):
        """Process price data and calculate indicators
        
        Args:
            data: StockData object containing price data
        """
        try:
            if data is None:
                return
                
            symbol = data.symbol
            price_data = data.data
            
            # Calculate indicators
            df_with_indicators = self.calculate_technical_indicators(price_data, self.BALANCED_INDICATORS)
            
            # Store indicators in database
            success = await self.db.store_technical_indicators(df_with_indicators)
            
            if success:
                self.logger.info(f"Calculated and stored indicators for {symbol}")
            else:
                self.logger.error(f"Failed to store indicators for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error in TI calculator: {e}")
            await self.error_queue.put({
                'error': str(e),
                'worker': self.name
            })
            await asyncio.sleep(60)  # Wait a minute before retrying 