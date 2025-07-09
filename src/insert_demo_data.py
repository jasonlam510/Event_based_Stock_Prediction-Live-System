import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import os
import sys
project_root = Path.cwd() # Get the current directory
sys.path.append(str(project_root))
from utils.config import Config
from src.pipeline.orchestrator import PipelineOrchestrator
from src.utils.logger import get_logger
from src.database import init_db, close_db, Database
from src.database import Database
from sqlalchemy import Column, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = 'postgresql://postgres:I_Love_CityU@localhost:5432/myfypdb'

Base = declarative_base()

class Prediction(Base):
    __tablename__ = "prediction"
    date = Column(Date, primary_key=True)
    symbol = Column(String, primary_key=True)
    predicted_close = Column(Float)

async def create_prediction_table(db: Database):
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_full_price_data(db: Database, symbol: str):
    start_date = datetime(2000, 1, 1)
    end_date = datetime.now()
    df = await db.get_stock_data(symbol, start_date, end_date)
    if df is not None:
        df = df.sort_values('date')
    return df

def generate_demo_predictions(df):
    np.random.seed(42)
    actual = df['close'].values
    noise = np.random.normal(loc=0, scale=46.38, size=len(actual))
    predicted = actual + noise
    predicted = pd.Series(predicted).rolling(window=5, min_periods=1).mean().values
    lag_days = int(round(0.87))
    predicted = np.roll(predicted, lag_days)
    predicted[:lag_days] = predicted[lag_days]
    return predicted

async def insert_predictions(db: Database, df, symbol, predicted):
    async with db.async_session() as session:
        for date, pred in zip(df['date'], predicted):
            prediction = Prediction(
                date=date.date(),
                symbol=symbol,
                predicted_close=float(pred)
            )
            session.add(prediction)
        await session.commit()

async def main():
    symbol = "^GSPC"
    db = Database(DATABASE_URL)
    await db.connect()
    await create_prediction_table(db)
    df = await get_full_price_data(db, symbol)
    if df is None or df.empty:
        print(f"No price data found for symbol {symbol}")
        await db.disconnect()
        return
    predicted = generate_demo_predictions(df)
    await insert_predictions(db, df, symbol, predicted)
    print("Demo predictions inserted.")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())