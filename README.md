# Event-based Stock Prediction - Live System

This is the **live system implementation** of the BSCCS Final Year Project 2024-2025 "Event-based Stock Prediction" supervised by [Prof ZHANG, Qingfu](https://scholars.cityu.edu.hk/en/persons/qingfu-zhang(a25373cf-62a1-4697-ad08-43678bcbf3f2).html)

## 📚 **Research Context**

This repository contains the **production-ready live system** that implements the findings from our research on feature sets for stock price prediction. 

**For the research work, experiments, and feature analysis, please visit: [https://github.com/jasonlam510/FYP](https://github.com/jasonlam510/FYP)**

In our research, we investigated which feature sets are most critical for accurate stock price prediction. We compared five categories of predictors:
- **FinBERT sentiment scores**
- **LLM-Graded Event Vector (LGEV)**
- **Traditional technical indicators**
- **Directional-change signals**
- **Macroeconomic indicators**

Using modern deep-learning architectures, we identified the most effective feature combinations for stock price forecasting.

## 🚀 **About This Live System**

This repository implements the **production-ready live system** that operationalizes our research findings. It's a real-time financial data pipeline that continuously fetches, processes, and analyzes market data to generate live stock price predictions.

### 🎯 **Live System Goals**

- **Real-time Data Processing**: Continuously monitor and analyze financial news from Yahoo Finance
- **Live Sentiment Analysis**: Use Google Gemini LLM to extract sentiment, relevance, and event importance from news headlines in real-time
- **Technical Analysis**: Calculate comprehensive technical indicators (RSI, MACD, Bollinger Bands, etc.) for live market data
- **Live Predictions**: Generate real-time stock price forecasts using our research-validated feature combinations
- **Market Monitoring**: Provide live insights into market-moving events and their potential impact

### 🏗️ **Live System Architecture**

The live system consists of several interconnected components:

- **Real-time Data Pipeline**: Asynchronous workers for fetching RSS feeds, price data, and calculating technical indicators
- **Live LLM Analysis**: Google Gemini-powered sentiment analysis for real-time financial news
- **Time-series Database**: PostgreSQL with TimescaleDB for efficient real-time data storage
- **Live Monitoring**: Grafana dashboards for real-time visualization and monitoring
- **Live Prediction Engine**: Production ML models combining sentiment and technical analysis

### 📊 **Live System Features**

- **Real-time Data Collection**: Live RSS feeds from Yahoo Finance
- **Live Sentiment Analysis**: 15+ event types classification with real-time sentiment scoring
- **Live Technical Indicators**: 15+ technical indicators calculated in real-time
- **Continuous Processing**: Asynchronous pipeline for 24/7 data processing
- **Production Architecture**: Docker-based deployment with microservices design
- **Historical Backfill**: Capabilities for processing historical data
- **Production Ready**: Comprehensive error handling, logging, and monitoring

### 🔬 **From Research to Production**

This live system operationalizes our research findings by:
- **Implementing the optimal feature combinations** identified in our research
- **Providing real-time data processing** for live market analysis
- **Deploying production-ready ML models** based on our experimental results
- **Creating a scalable architecture** for continuous market monitoring
- **Enabling live visualization** of predictions and market insights

The system serves as a proof-of-concept for deploying research-based stock prediction models in a production environment, demonstrating the practical application of our academic research findings.

# Architecture Diagram

![Architecture Diagram](doc/Architecture_Diagram.png)

# Installation and Setup

This project uses Docker for easy deployment and setup. Follow the instructions below to get started.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/jasonlam510/myFYP
   cd myFYP
   ```

2. **Set up environment variables**
   
   Create a `.env` file in the root directory with the following variables:
   ```bash
   # Environment (test or prod)
   ENVIRONMENT=test
   
   # Database Configuration
   DATABASE_URL=postgresql://postgres:I_Love_CityU@localhost:5432/myfypdb
   
   # API Keys
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
   
   **Note**: Replace `your_gemini_api_key_here` with your actual Google Gemini API key.

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Access the services**
   - **Grafana Dashboard**: http://localhost:3000
     - Username: `admin`
     - Password: `I_Love_CityU`
   - **PostgreSQL Database**: Running in Docker container
     - Database: `myfypdb`
     - Username: `postgres`
     - Password: `I_Love_CityU`
     
     **Connecting to PostgreSQL via Docker:**
     ```bash
     # Connect to the PostgreSQL container
     docker exec -it myfyp_postgres psql -U postgres -d myfypdb
     ```
     
     **Alternative: Connect from your local machine:**
     ```bash
     # Using psql if installed locally
     psql -h localhost -p 5432 -U postgres -d myfypdb
     ```
     
     **For more Docker PostgreSQL connection options, see:**
     - [PostgreSQL Docker Official Documentation](https://hub.docker.com/_/postgres)
     - [Docker PostgreSQL Connection Guide](https://docs.docker.com/samples/library/postgres/)
     
     **Available Tables:**
     - `yf_rss_items` - Yahoo Finance RSS feed data
     - `analysis_results` - LLM analysis results
     - `stock_data` - Stock price data (OHLCV)
     - `technical_indicators` - Calculated technical indicators

## Port Configuration

The following ports are used by the services:

- **3000**: Grafana (Web dashboard)
- **5432**: PostgreSQL (Database)

Make sure these ports are available on your system before starting the services.
